# Storage-Based Remediation (SBR) — Architecture

## What SBR does (high level)

SBR provides **cluster node coordination and fencing over shared storage**: each node runs an **sbr-agent** that heartbeats into fixed slots on shared device files, watches peers, and can **write fence messages** so a failed node self-reboots when it reads its fence slot. A separate **sbr-operator** deploys and configures agents from a `StorageBasedRemediationConfig` CR.

---

## Repository layout

| Area | Role |
|------|------|
| `cmd/main.go` | **SBR operator** — controller-runtime manager for `StorageBasedRemediationConfig` + validating webhook |
| `cmd/sbr-agent/main.go` | **SBR agent** — watchdog + shared-device loops + embedded `StorageBasedRemediation` reconciler |
| `api/v1alpha1/` | CRD Go types (`StorageBasedRemediation`, `StorageBasedRemediationConfig`, `StorageBasedRemediationTemplate`), webhooks, deepcopy |
| `pkg/controller/` | `StorageBasedRemediationConfigReconciler` (operator); `SBRRemediationReconciler` (used by agent) |
| `pkg/sbdprotocol/` | Slot layout, heartbeat/fence messages, `NodeManager` (node name ↔ slot ID, shared nodemap) |
| `pkg/blockdevice/` | Block I/O with timeouts |
| `pkg/watchdog/` | Linux watchdog (with softdog fallback in agent) |
| `pkg/agent/` | Shared flags/constants (device paths, mount dir `/dev/sbr`, file names) |
| `pkg/retry/` | Shared exponential backoff for API and I/O |

---

## Key components and responsibilities

### 1. SBR operator (`cmd/main.go`)

- Runs **controller-runtime** with **leader election** (ID: `sbr-operator-leader-election`) — serializes config reconciliation, not per-node fencing.
- Registers only **`StorageBasedRemediationConfigReconciler`** (explicit code comment: remediation reconciler runs in the agent, not here).
- Optional **validating admission webhook** for `StorageBasedRemediationConfig`.

### 2. `StorageBasedRemediationConfigReconciler`

- Reconciles **`StorageBasedRemediationConfig`**.
- **Finalizer** `sbr-operator.medik8s.io/cleanup` for delete path.
- Ensures shared **sbr-agent ServiceAccount** and **ClusterRoleBindings** (including OpenShift **privileged SCC** binding).
- If `spec.sharedStorageClass` is set: validates StorageClass supports **ReadWriteMany** → creates **RWX PVC** → runs a **Job** that initializes heartbeat file, fence file, and shared nodemap under the mount.
- Builds **DaemonSet** `sbr-agent-{configName}`: privileged, mounts host `/dev` + `/sys` + `/proc`, optional PVC mount at `/dev/sbr`.
- Updates **status**: `DaemonSetReady`, `SharedStorageReady`, `Ready`, `readyNodes`, `totalNodes`.

### 3. SBR agent (`cmd/sbr-agent/main.go`)

- Requires both a watchdog and SBR device to be accessible at startup.
- Runs two loops: **(a)** kernel watchdog pet loop; **(b)** SBR heartbeat writes + peer heartbeat reads on the heartbeat device; fence device is separate.
- **Node slot assignment**: hash-based via `sbdprotocol.NodeManager`; initial `--node-id` flag is overridden at runtime.
- Sets **`SBRStorageUnhealthy`** condition on peer `Node` objects → intended signal for **NHC** to create a `StorageBasedRemediation` CR.
- On local failure: may stop petting watchdog or panic/reboot unless no remediation CR exists for that node.
- Hosts an embedded **controller-runtime manager** (no leader election) running `SBRRemediationReconciler`.

### 4. `SBRRemediationReconciler` (runs inside each agent)

- **Target node = CR `.metadata.name`**. Short-circuits if name matches own node (no self-fence via this path).
- Flow: add finalizer → **cordon** target → set **FencingInProgress** → **write fence message** to target's slot on fence device → poll until fenced (Node `Ready=False`, stale heartbeat, or timeout) → apply **`node.kubernetes.io/out-of-service`** taint → set success conditions.
- Delete path: uncordon → wait for taint removal → remove OOS taint → remove finalizer.

---

## Custom Resources (`api/v1alpha1/`)

**Group:** `storage-based-remediation.medik8s.io`, **Version:** `v1alpha1`

### `StorageBasedRemediationConfig` (namespaced)

Operator-managed desired state for agent DaemonSet, image, timing, and optional RWX shared storage.

Key spec fields:
- `sharedStorageClass` — drives PVC creation (RWX, `10Mi`)
- `watchdogPath`, `staleNodeTimeout`, `watchdogTimeout`, `petIntervalMultiple`
- `sbrTimeoutSeconds`, `sbrUpdateInterval`, `peerCheckInterval`
- `rebootMethod` — `panic` | `systemctl-reboot` | `none`
- `detectOnlyMode` — `Disabled` | `Enabled` (arms/disarms local agent fencing paths; **note:** peer fencing reconciler does not read this flag)
- `nodeSelector`, `logLevel`, `iotimeout`

### `StorageBasedRemediation` (namespaced)

Request to fence a node; **CR name must match the Kubernetes node name**.

Key spec fields:
- `reason` — `HeartbeatTimeout` | `NodeUnresponsive` | `ManualFencing` (default: `NodeUnresponsive`)
- `timeoutSeconds` — 30–300 (default 60)

Status: `FencingInProgress`, `FencingSucceeded`, `Ready` conditions. Note: `LeadershipAcquired`, `status.nodeID`, `fenceMessageWritten`, and `operatorInstance` exist in the schema but are **not set** by the reconciler today — schema placeholders.

### `StorageBasedRemediationTemplate` (namespaced)

Wraps a `StorageBasedRemediation`-shaped template for external remediation integrations (e.g. NHC). No reconciler in this repo — external controllers instantiate remediations from it.

---

## Reconciliation flows

### A. `StorageBasedRemediationConfig` create/update

1. Validate spec; webhook may enforce additional rules (e.g. node selector overlap).
2. Ensure SA + RBAC (+ OpenShift SCC binding).
3. If shared storage: validate StorageClass → create PVC → run init Job for device files + nodemap.
4. Create/update DaemonSet; refresh status conditions.

### B. `StorageBasedRemediation` create/update (inside agent)

1. Only agents **not on the target node** fence it (own-node short-circuit).
2. Cordon → FencingInProgress → write fence to target slot on fence device → wait for confirmation or timeout → apply OOS taint → set success.
3. Delete: uncordon → remove OOS taint → drop finalizer.

### C. Failure / observability paths (agent)

- Local watchdog and SBR I/O failures → possible **self-fence**.
- Peer failure → **`SBRStorageUnhealthy`** on peer's `Node` → intended signal for **NHC** to create `StorageBasedRemediation`.

---

## Interaction with other systems

| System | How SBR connects |
|--------|-----------------|
| **Kubernetes** | Nodes, Pods, PVCs, StorageClasses, Jobs, DaemonSets, RBAC, optional SCC bindings |
| **NHC (Node Health Check)** | No Go import. Contract: `SBRStorageUnhealthy` condition on `Node` + `StorageBasedRemediation` CR named after the node. E2E tests simulate NHC by manually creating/deleting the CR |
| **FAR / external remediation** | `StorageBasedRemediationTemplate` + `external_remediation_clusterrole` support the external remediation RBAC pattern |
| **Storage** | RWX PVC + regular files under `/dev/sbr` (`sbr-device`, `sbr-device-fence`, nodemap). **Not** a CSI block volume despite README wording — filesystem-backed files on shared storage |
| **Prometheus** | Agent exposes metrics (`sbr_agent_status_healthy`, `sbr_device_io_errors_total`, etc.); operator uses controller-runtime metrics |

---

## Notable patterns and design decisions

- **Fencing runs in agents, not the operator**: Leader election in the operator serializes config/DaemonSet management only; actual fence writes happen in `sbr-agent` instances across the cluster.
- **Two logical devices on shared storage**: heartbeat device (liveness) and fence device (trigger reboot) are separate files.
- **Hash-based slot assignment** with persisted nodemap supersedes the old static `--node-id` flag.
- **File locking** optional (`--sbr-file-locking`) for coordination on shared FS.
- **API/implementation drift**: `LeadershipAcquired` status field and RBAC for leases are generated but unused in the reconciler.

---

> **Doc caveat:** The README emphasizes CSI block PVs. The actual implemented path uses RWX filesystem PVCs with regular files as SBR devices. Prefer `StorageBasedRemediationConfig` spec + `pkg/agent` constants as ground truth.
