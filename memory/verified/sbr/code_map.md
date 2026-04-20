# Storage-Based Remediation (SBR) — Code Map

**Repository:** `github.com/medik8s/storage-based-remediation`

> **Key architectural note:** The main operator binary runs `StorageBasedRemediationConfig` reconciliation and admission webhooks. **Fencing for `StorageBasedRemediation` CRs runs in the sbr-agent** via `SBRRemediationReconciler` — not in the operator process.

---

## Directory structure

```
storage-based-remediation/
├── api/v1alpha1/           # CRD Go types, defaults/validation helpers, admission webhook for Config
├── cmd/
│   ├── main.go             # sbr-operator: manager, config controller, webhooks only
│   └── sbr-agent/          # sbr-agent: heartbeats, peer monitor, watchdog, remediation fencing
├── config/                 # Kustomize / deployment manifests
├── pkg/
│   ├── agent/              # Shared CLI flag names + shared-storage path constants (DaemonSet ↔ agent)
│   ├── blockdevice/        # Raw block I/O with timeouts and retries (SBR heartbeat/fence devices)
│   ├── controller/         # StorageBasedRemediationConfig + StorageBasedRemediation reconcilers
│   ├── mocks/              # Interfaces (watchdog, block device) for tests
│   ├── retry/              # Generic exponential backoff retry
│   ├── sbdprotocol/        # SBD message format + node map + NodeManager (slots, locking)
│   ├── storage/            # Optional tooling: NFS CSI / ODF helpers (not the main operator path)
│   ├── version/            # Build/version info
│   └── watchdog/           # Linux watchdog open/pet (ioctl + softdog fallback)
├── test/
│   ├── e2e/                # Ginkgo e2e (cluster disruption, remediation, storage class checks)
│   └── utils/              # Test helpers
└── tools/                  # Ancillary scripts/tools
```

---

## Key files and what they do

### `cmd/main.go` — Operator entry point

- Registers `StorageBasedRemediationConfigReconciler` only.
- Sets up controller-runtime manager, metrics, health probes, leader election (`LeaderElectionID: sbr-operator-leader-election`).
- Registers `StorageBasedRemediationConfigValidator` webhook when `--enable-webhooks=true`.
- **Does not** run `SBRRemediationReconciler`.

### `cmd/sbr-agent/main.go` — Agent entry point and core runtime

Owns all agent loops, the embedded controller-runtime manager, and the self-fence decision logic.

| Function | Description |
|---|---|
| `SBRAgent`, `NewSBRAgentWithWatchdog` | Construct agent: devices, node manager, metrics, embedded reconciler |
| `watchdogLoop` | Periodic pet or self-fence / SBR-unhealthy policy |
| `petWatchdogWhenHealthy` | Pet with `retry.Do` when SBR is healthy |
| `handleWatchdogTickSBRUnhealthy` | Detect-only vs skip pet if CR exists / API error |
| `heartbeatLoop`, `writeHeartbeatToSBR` | Write heartbeat to own slot |
| `peerMonitorLoop` | Read peers, check liveness, set `SBRStorageUnhealthy` on Node |
| `readOwnSlotForFenceMessage` | Detect fence message in own slot → self-fence |
| `executeSelfFencing` | panic / systemctl-reboot / none |
| `shouldTriggerSelfFence` | Threshold check + abort if no remediation CR |
| `remediationExistsForThisNode` | K8s Get with 5s timeout; used as CR existence gate |
| `initializeControllerManager`, `addSBRRemediationController` | Embed `SBRRemediationReconciler` in agent |

### `api/v1alpha1/`

| File | Role |
|---|---|
| `groupversion_info.go` | Group/version registration, `AddToScheme` |
| `storagebasedremediation_types.go` | `StorageBasedRemediation` types, status conditions, `NodeConditionSBRStorageUnhealthy` constant |
| `storagebasedremediationtemplate_types.go` | Template CRD for NHC-style consumers |
| `storagebasedremediationconfig_types.go` | Full Config spec + `ValidateAll` + field validators + defaults + `deriveAgentImageFromOperator` |
| `storagebasedremediationconfig_webhook.go` | Admission: `ValidateCreate` / `ValidateUpdate` call `Spec.ValidateAll()` |

### `pkg/controller/`

| File | Role |
|---|---|
| `storagebasedremediationconfig_controller.go` | DaemonSet, PVC, init Job, SA/RBAC, StorageClass validation, `buildDaemonSet`, `buildSBRAgentArgs`, `updateStatus` |
| `storagebasedremediation_controller.go` | `SBRRemediationReconciler`: cordon, `writeFenceMessage`, `checkFencingCompletion`, `ensureOutOfServiceTaint`, deletion cleanup |

### `pkg/sbdprotocol/`

| File | Role |
|---|---|
| `message.go` | Slot size, message types (`HEARTBEAT`, `FENCE`), marshal/unmarshal, fence reason constants |
| `nodemap.go` | JSON node-name↔slot mapping on disk: `NodeMapTable`, hash-based `AssignSlot`, checksum |
| `nodemanager.go` | `NodeManager`: load/sync map file, `GetNodeIDForNode`, `LookupNodeIDForNode`, `WriteWithLock` / `ReadWithLock`, stale cleanup, periodic sync |

### `pkg/blockdevice/blockdevice.go`

`Device`: `Open` / `OpenWithTimeout`, `ReadAt` / `WriteAt` / `Sync` with I/O timeouts (goroutine + `time.After`) and `retry.Do`.

### `pkg/watchdog/watchdog.go`

`Watchdog`: `Pet()` (ioctl keepalive + write fallback), `NewWithSoftdogFallback` (loads `softdog` via nsenter), `Close`.

### `pkg/agent/flags.go`

Flag name constants (`FlagWatchdogPath`, `FlagSBRDevice`, etc.), defaults, and **shared storage layout constants** — the bridge between DaemonSet args and agent runtime (`SharedStorageSBRDeviceFile`, `SharedStorageFenceDeviceSuffix`, `SharedStorageNodeMappingSuffix`, mount path `/dev/sbr`).

### `pkg/retry/retry.go`

`retry.Config`, `retry.Do`, `IsTransientError`, `NewRetryableError` — used by agent, blockdevice, watchdog, and controllers throughout.

---

## Key functions quick reference

| Function | File | Description |
|---|---|---|
| `(*SBRRemediationReconciler).Reconcile` | `pkg/controller/storagebasedremediation_controller.go` | Fence peer: cordon → write fence → wait → OOS taint → success |
| `(*SBRRemediationReconciler).writeFenceMessage` | `pkg/controller/storagebasedremediation_controller.go` | Marshal fence to target slot on fence device |
| `(*SBRRemediationReconciler).ensureOutOfServiceTaint` | `pkg/controller/storagebasedremediation_controller.go` | Apply `node.kubernetes.io/out-of-service` NoExecute taint |
| `(*SBRRemediationReconciler).checkFencingCompletion` | `pkg/controller/storagebasedremediation_controller.go` | Poll node Ready status + heartbeat staleness; force-complete on timeout |
| `(*StorageBasedRemediationConfigReconciler).Reconcile` | `pkg/controller/storagebasedremediationconfig_controller.go` | Validate SC, PVC, init Job, DaemonSet, status |
| `(*StorageBasedRemediationConfigReconciler).validateStorageClass` | `pkg/controller/storagebasedremediationconfig_controller.go` | RWX provisioner checks + optional test PVC |
| `(*StorageBasedRemediationConfigReconciler).buildDaemonSet` | `pkg/controller/storagebasedremediationconfig_controller.go` | Build full privileged pod spec with host mounts and agent args |
| `shouldTriggerSelfFence` | `cmd/sbr-agent/main.go` | Failure threshold check; aborts if no remediation CR confirmed |
| `handleWatchdogTickSBRUnhealthy` | `cmd/sbr-agent/main.go` | Per-tick: detect-only / stop petting (CR exists or API error) / keep petting (no CR) |
| `executeSelfFencing` | `cmd/sbr-agent/main.go` | Runs reboot method; stops watchdog petting |
| `peerMonitorLoop` | `cmd/sbr-agent/main.go` | Read peers, assess liveness, set `SBRStorageUnhealthy` node condition |
| `setNodeConditionSBRStorageUnhealthyStatus` | `cmd/sbr-agent/main.go` | Patch node status with `SBRStorageUnhealthy` condition |
| `(*NodeManager).WriteWithLock` | `pkg/sbdprotocol/nodemanager.go` | Serialize writes to SBR device + map file with optional file lock |
| `(*NodeManager).GetNodeIDForNode` | `pkg/sbdprotocol/nodemanager.go` | Assign or retrieve slot ID for this node |
| `(*Watchdog).Pet` | `pkg/watchdog/watchdog.go` | ioctl keepalive (+ write fallback) |
| `retry.Do` | `pkg/retry/retry.go` | Backoff retry for transient errors |

---

## Where is X? Quick lookup

| Question | Answer |
|---|---|
| **Where is fencing logic?** | **Peer → self-fence** (own slot): `cmd/sbr-agent/main.go` — `readOwnSlotForFenceMessage`, `executeSelfFencing`. **NHC/operator → peer** (fence write): `pkg/controller/storagebasedremediation_controller.go` — `executeFencing`, `writeFenceMessage`. |
| **Where is heartbeat written?** | `cmd/sbr-agent/main.go`: `heartbeatLoop` → `writeHeartbeatToSBR` → `writeHeartbeatToSBRInternal` (uses `sbdprotocol.MarshalHeartbeat` + `NodeManager.WriteWithLock`). |
| **Where is peer health checked?** | `cmd/sbr-agent/main.go`: `peerMonitorLoop` → `readPeerHeartbeat` → `peerMonitor.updatePeer` / `checkPeerLiveness`. |
| **Where is node condition set?** | `cmd/sbr-agent/main.go`: `setNodeConditionSBRStorageUnhealthy`, `setNodeConditionSBRStorageUnhealthyStatus`. Type constant: `api/v1alpha1/storagebasedremediation_types.go` — `NodeConditionSBRStorageUnhealthy`. |
| **Where is watchdog petted?** | `pkg/watchdog/watchdog.go`: `Pet()`. Called from `cmd/sbr-agent/main.go`: `petWatchdogWhenHealthy` and (conditionally) `handleWatchdogTickSBRUnhealthy`. |
| **Where is self-fence decision made?** | `cmd/sbr-agent/main.go`: `shouldTriggerSelfFence` (failure counts + CR gate), called from `watchdogLoop`. |
| **Where is OOS taint applied?** | `pkg/controller/storagebasedremediation_controller.go`: `ensureOutOfServiceTaint`. Delayed for fresh agent remediations: `isRemediationFresh`, `SBRAgentRemediationFreshAge`. |
| **Where is the DaemonSet built?** | `pkg/controller/storagebasedremediationconfig_controller.go`: `buildDaemonSet`, `buildSBRAgentArgs`, `buildVolumeMounts`, `buildVolumes`, `buildNodeSelector`. |
| **Where is StorageClass validated?** | API name format: `api/v1alpha1/storagebasedremediationconfig_types.go` — `ValidateSharedStorageClass`. RWX/provisioner check: `pkg/controller/storagebasedremediationconfig_controller.go` — `validateStorageClass`, `isRWXCompatibleProvisioner`, `testRWXSupport`. |
| **Where are agent CLI flags defined?** | Names + path constants: `pkg/agent/flags.go`. `flag` declarations: `cmd/sbr-agent/main.go`. DaemonSet args: `buildSBRAgentArgs` in `storagebasedremediationconfig_controller.go`. |
| **Where is node slot assignment?** | `pkg/sbdprotocol/nodemanager.go`: `NodeManager.GetNodeIDForNode` (assigns hash-based slot, persists to shared nodemap). |
| **Where is the message protocol?** | `pkg/sbdprotocol/message.go`: slot layout, `NewHeartbeat`, `NewFence`, marshal/unmarshal. |

---

## E2E test structure

- **Suite setup:** `test/e2e/e2e_suite_test.go` — namespace `sbr-test-e2e`, cluster connection, optional AWS init, cleanup.
- **Specs:** `test/e2e/e2e_test.go` — `Describe("SBR Operator")` Ordered: kubelet disruption, basic config, fake remediation, incompatible StorageClass, node remediation (cordon → fencing → OOS taint), agent crash, storage disruption.
- **Key helpers:** RWX provisioner lists (mirrors controller), disruptor pods, `checkNodeHasSBRStorageUnhealthyCondition`, boot ID / reboot checks.
