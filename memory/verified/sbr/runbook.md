# Storage-Based Remediation (SBR) — Operational Runbook

## 1. Overview

SBR deploys two components:

- **Operator** (`cmd/main.go`): reconciles `StorageBasedRemediationConfig`, manages DaemonSet/PVC/RBAC, optional admission webhooks, leader election. Does **not** run fencing — that runs inside agents.
- **sbr-agent** (DaemonSet per config): watchdog + shared device I/O, peer monitoring, `SBRStorageUnhealthy` node condition, Prometheus metrics, and in-agent `StorageBasedRemediation` reconciliation (fence writes).

Default install namespace: **`sbr-operator-system`** (`config/default/kustomization.yaml`).

---

## 2. Deployment

### 2.1 Prerequisites

| Requirement | Note |
|---|---|
| Kubernetes 1.28+ | Per README |
| **RWX shared storage** | A `StorageClass` supporting ReadWriteMany is required for reconciliation to succeed |
| **Watchdog device** on each node | Agent preflight opens it; softdog fallback is available |
| Linux worker nodes | DaemonSet affinity/selectors enforce this |

> **Note:** The README mentions CSI block volumes. The actual implementation creates a **RWX PVC** and initializes regular **files** on that volume. Treat the production requirement as RWX filesystem shared storage.

### 2.2 Install CRDs

```bash
make install
# equivalent: kustomize build config/crd | kubectl apply -f -
```

### 2.3 Install operator (manifests)

```bash
make deploy
# equivalent: kustomize build config/default | kubectl apply -f -
```

Build a consolidated installer:
```bash
make build-installer            # writes dist/install.yaml
make build-openshift-installer  # includes SCC overlay
```

### 2.4 Install via OLM

```bash
make bundle-run
# or: operator-sdk -n "$OPERATOR_NAMESPACE" run bundle "$BUNDLE_IMG"
```

Default OLM namespace: `openshift-workload-availability`. Upgrade: `make bundle-run-update`.

### 2.5 Create a `StorageBasedRemediationConfig`

The controller validates `sharedStorageClass` and will not complete reconciliation without it. Minimal working config:

```yaml
apiVersion: storage-based-remediation.medik8s.io/v1alpha1
kind: StorageBasedRemediationConfig
metadata:
  name: sbr
  namespace: sbr-operator-system
spec:
  sharedStorageClass: "<your-rwx-storageclass>"
  image: "quay.io/medik8s/storage-based-remediation-agent:latest"
  imagePullPolicy: IfNotPresent
```

On reconciliation the controller will:
1. Validate the StorageClass (known RWX provisioners, or temporary RWX test PVC for unknown ones).
2. Create PVC `<name>-shared-storage` (10Mi, RWX).
3. Run Job `<name>-sbr-device-init` to create heartbeat/fence files and nodemap under the mount.
4. Create DaemonSet `sbr-agent-<name>`, ServiceAccount `sbr-agent`, ClusterRoleBindings, and (on OpenShift) privileged SCC binding.

---

## 3. Configuration reference

### 3.1 `StorageBasedRemediationConfig` spec — defaults

| Field | Default | Note |
|---|---|---|
| `watchdogPath` | `/dev/watchdog` | |
| `watchdogTimeout` | `60s` | 10s–300s allowed |
| `petIntervalMultiple` | `4` | pet interval = watchdog timeout / multiple |
| `staleNodeTimeout` | `1h` | |
| `iotimeout` | `2s` | Block device I/O timeout |
| `logLevel` | `info` | |
| `imagePullPolicy` | `IfNotPresent` | |
| `rebootMethod` | `panic` | See §3.3 |
| `sbrTimeoutSeconds` | `30` | Heartbeat interval = this / 2 |
| `sbrUpdateInterval` | `5s` | |
| `peerCheckInterval` | `5s` | |
| `nodeSelector` | `node-role.kubernetes.io/worker: ""` + `kubernetes.io/os=linux` | |

### 3.2 `detectOnlyMode`

- **Values:** `Disabled` (default) or `Enabled`.
- **When enabled:** Agent disarms the watchdog, skips self-fence, and still sets/clears `SBRStorageUnhealthy` on peers. Used to leverage SBR's storage-based detection while delegating actual remediation to another medik8s remediator (e.g. FAR, MDR) via NHC.
- **Required when** running alongside any remediator that also arms the watchdog (e.g. SNR).

### 3.3 `rebootMethod` options

| Value | Behavior |
|---|---|
| `panic` | Immediate `panic()` — fastest. **Default.** |
| `systemctl-reboot` | Tries `systemctl reboot --force --force`, `reboot -f`, then `/proc/sysrq-trigger`; falls back to panic if all fail. |
| `none` | No agent-initiated reboot; relies on hardware watchdog timeout after petting stops. |

---

## 4. Operating

### 4.1 Verify the operator

```bash
kubectl get deploy -n sbr-operator-system
kubectl logs -n sbr-operator-system deploy/sbr-operator-controller-manager -c manager
```

### 4.2 Verify config and agents

```bash
kubectl get storagebasedremediationconfig -A
kubectl describe storagebasedremediationconfig <name> -n <ns>
kubectl get daemonset -n <ns> -l app=sbr-agent
kubectl get pods -n <ns> -l app=sbr-agent -o wide
```

Check status conditions on the config: `DaemonSetReady`, `SharedStorageReady`, `Ready`.

### 4.3 Manually trigger a remediation (testing)

The CR `metadata.name` **must exactly match the Kubernetes node name** (this is how the reconciler identifies the target — there is no `spec.nodeName` field):

```yaml
apiVersion: storage-based-remediation.medik8s.io/v1alpha1
kind: StorageBasedRemediation
metadata:
  name: <exact-kubernetes-node-name>
  namespace: <same namespace as StorageBasedRemediationConfig>
spec:
  reason: ManualFencing      # HeartbeatTimeout | NodeUnresponsive | ManualFencing
  timeoutSeconds: 120        # 30–300
```

> **Note:** The sample file `config/samples/...storagebasedremediation.yaml` includes `spec.nodeName` — this field does **not** exist in the CRD and will be rejected.

### 4.4 Check remediation status

```bash
kubectl get storagebasedremediation -n <ns> -o wide
kubectl describe storagebasedremediation <node-name> -n <ns>
```

Key conditions: `FencingInProgress`, `FencingSucceeded`, `Ready`.

### 4.5 Cancel / clean up a remediation

Delete the CR — the finalizer automatically uncordons the node, removes the `OutOfService` taint, then removes the finalizer:

```bash
kubectl delete storagebasedremediation <node-name> -n <ns>
```

Delete the config (removes DaemonSet/PVC via GC, cleans up ClusterRoleBindings via finalizer):
```bash
kubectl delete storagebasedremediationconfig <name> -n <ns>
```

---

## 5. Troubleshooting

### 5.1 Agent logs

```bash
kubectl logs -n <ns> -l app=sbr-agent -c sbr-agent --tail=200 -f
# For a specific node:
kubectl logs -n <ns> <sbr-agent-pod-name> -c sbr-agent
```

### 5.2 Key log messages

| Message / event reason | Meaning |
|---|---|
| `Peer node became unhealthy` | Peer missed heartbeats beyond timeout |
| `Set SBRStorageUnhealthy condition` | Agent signaling NHC to act |
| `Skipping watchdog pet - SBR device is unhealthy and remediation CR exists` | Intentional stop petting; reboot imminent |
| `SelfFenceInitiated` | Self-fence executing |
| `FenceMessageDetected` | Fence message found in own slot; self-fence triggered |
| `SBRUnhealthyDetectOnly` | Detect-only mode; no reboot |
| `SBRUnhealthySkipPetAPIError` | API unavailable during CR check; failing safe → stop petting |
| `SelfFenceAbortedNoRemediation` | Thresholds met but no CR confirmed → abort self-fence, keep petting |

### 5.3 Check `SBRStorageUnhealthy` node condition

```bash
kubectl get node <name> -o jsonpath='{range .status.conditions[*]}{.type}{"\t"}{.status}{"\t"}{.reason}{"\n"}{end}' | grep SBRStorageUnhealthy
```

Condition lifecycle: `False` → `True` (peer unhealthy) → `Unknown` (stale, ~125s) → grace period (3 min) → `True` again if still unhealthy.

### 5.4 Prometheus metrics

Default metrics port: **8082** (not 8080 — the Prometheus manifest at `config/prometheus/sbr-agent-metrics.yaml` is outdated).

| Metric | Meaning |
|---|---|
| `sbr_agent_status_healthy` | 1 = healthy, 0 = unhealthy |
| `sbr_device_io_errors_total` | Cumulative I/O errors on shared device |
| `sbr_watchdog_pets_total` | Successful watchdog pets |
| `sbr_peer_status` | Per-peer liveness (labels: `node_id`, `node_name`, `status`) |
| `sbr_self_fenced_total` | How many times this agent has self-fenced |

Scrape: agent runs with `hostNetwork: true`; scrape via node IP on port 8082. The operator does not create a Service or PodMonitor automatically.

### 5.5 Common problems

| Symptom | Likely cause / fix |
|---|---|
| Config never `Ready`; PVC/storage events | Invalid or block-only StorageClass; use a known RWX class |
| Init Job stuck or failing | Check Job pod logs: `kubectl get jobs -n <ns>` |
| Agent CrashLoop on startup | Preflight failed — watchdog or SBR device inaccessible; check agent logs |
| Fencing never starts | Fencing runs in agents, not the operator pod; confirm agent pods are Ready and CR name matches node name exactly |
| `spec.nodeName` rejection | Remove this field — it does not exist in the current CRD |
| Remediation forced complete but node still up | Timeout path; node may not have rebooted — check agent and node logs |

---

## 6. Known doc/code mismatches

- README describes CSI block volumes; implementation uses RWX PVC + files.
- `config/samples/...storagebasedremediation.yaml` has invalid `spec.nodeName`.
- `docs/sbr-agent-prometheus-metrics.md` lists port 8080; code default is **8082**.
- `config/prometheus/sbr-agent-metrics.yaml` uses namespace `sbr-system`; adjust to match your deployment.
