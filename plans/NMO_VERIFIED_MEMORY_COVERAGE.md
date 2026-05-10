# NMO verified memory — coverage checklist

**NMO** = **Node Maintenance Operator** (repository **`node-maintenance-operator`**). Upstream: **`github.com/medik8s/node-maintenance-operator`**.

Use this when writing or reviewing **`memory/verified/nmo/`**. Each row should be covered in **architecture** (behaviour), **failure_modes** (symptoms / failure behaviour), **runbook** (ops / `kubectl`). **overview** is optional short context; **code_map** maps repo files to topics.

Legend: ✓ = intentionally covered in that file’s prose (tick after verified memory exists).

## API scope

- **Group:** `nodemaintenance.medik8s.io`, **`v1beta1`**
- **Kind:** **`NodeMaintenance`** (short **`nm`**)
- **Scope:** **Cluster**
- **`spec`:** **`nodeName`** (required), **`reason`** (optional)
- **`status`:** **`phase`** (**Running** / **Succeeded** / **Failed**), **`drainProgress`**, **`lastUpdate`**, **`lastError`**, **`pendingPods`**, **`pendingPodsRefs`**, **`totalpods`**, **`evictionPods`**, **`errorOnLeaseCount`**
- **Finalizer:** **`foregroundDeleteNodeMaintenance`**

## Validating webhook (`api/v1beta1/nodemaintenance_webhook.go`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **Create** | Node must exist; no other **NodeMaintenance** for same **`nodeName`**; on OpenShift, control-plane nodes require **`etcd.IsEtcdDisruptionAllowed`** | | | |
| **Update** | **`spec.nodeName`** immutable | | | |
| **Delete** | **`ValidateDelete`** no-op (logged) | | | |
| **OpenShift-only quorum** | If not OpenShift, CP quorum check skipped | | | |

## Reconcile — lifecycle (`controllers/nodemaintenance_controller.go`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **CR deleted** | With finalizer: **`stopNodeMaintenanceOnDeletion`** (uncordon, taints, invalidate lease / skip if **AlreadyHeld**); remove finalizer; event **RemovedMaintenance** | | | |
| **Finalizer add** | On create path: add **`NodeMaintenanceFinalizer`**, event **BeginMaintenance** | | | |
| **`initMaintenanceStatus`** | First reconcile when **`phase` empty**: set **Running**, populate **pending** / **total** / **eviction** pod counts | | | |
| **Node missing** | **NotFound** → **Failed** phase, warning event, **`onReconcileError`** (no perpetual requeue for expected not-found string) | | | |
| **Lease failure budget** | **`errorOnLeaseCount` > 3** → **`stopNodeMaintenanceImp`**, **Failed**, **LastError** | | | |
| **`RequestLease`** | **`LeaseHolderIdentity`** **`node-maintenance`**, **`LeaseDuration`** 1h; **AlreadyHeld** mid-drain increments error / fail path | | | |
| **Exclude remediation label** | **`medik8s.io/exclude-from-remediation`** = **`true`** on node (common labels pkg) | | | |
| **Cordon** | **`drain.RunCordonOrUncordon(..., true)`** after taints | | | |
| **Taints** | **`AddOrRemoveTaint`**: **`node.kubernetes.io/unschedulable`** + **`medik8s.io/drain`** **NoSchedule** (`controllers/taint.go`) | | | |
| **Drain** | **`drain.RunNodeDrain`**: **Force**, **DeleteEmptyDirData**, **IgnoreAllDaemonSets**, **Timeout** **30s**, grace **-1** | | | |
| **Drain in progress** | Error → **`onReconcileErrorWithRequeue`** **5s**, update **pending** / **drainProgress** / **lastError** | | | |
| **Succeeded** | All pods evicted → **Succeeded**, **drainProgress** 100, clear pending, event **SucceedMaintenance** | | | |
| **Owner ref** | **`setOwnerRefToNode`** — Node **ownerReference** on **NodeMaintenance** (non-blocking GC hint) | | | |

## Lease integration (`medik8s/common/pkg/lease`, controller constants)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **Identity / duration** | **`node-maintenance`**, **3600s** | | | |
| **Stop / delete** | **`InvalidateLease`**; **AlreadyHeld** (e.g. NHC) → skip invalidation, continue cleanup | | | |

## RBAC (kubebuilder markers on reconciler)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **NodeMaintenance** | CRUD + status + finalizers | | | |
| **Nodes** | get/list/update/patch/watch | | | |
| **Pods** | get/list/watch; **pods/eviction** create | | | |
| **Apps** | get/list/watch **deployments/daemonsets/replicasets/statefulsets** | | | |
| **Leases** | coordination.k8s.io full set for drain/lease | | | |
| **PDBs** | policy, get/list/watch | | | |
| **Other** | namespaces get/create; ServiceMonitor; **oauth.openshift.io** * (marker — confirm bundle) | | | |

## Operator process (`main.go`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **Leader election** | Flag **`--leader-elect`** (default **false** in code); ID **`135b1886.medik8s.io`** | | | |
| **Lease manager** | **`leaseManagerInitializer`** runnable → **`lease.NewManager`** with **`LeaseHolderIdentity`** | | | |
| **OpenShift probe** | **`utils.NewOpenshiftValidator`** → webhook gets **`isOpenShift`** for etcd PDB path | | | |
| **Webhook TLS** | OLM certs **`/apiserver.local.config/certificates`** or generated; **HTTP/2** optional via flag | | | |
| **Metrics / probes** | **`--metrics-bind-address`** (default **`:8080`**) and **`--health-probe-bind-address`** (default **`:8081`**) are defined; **`ctrl.Options` in `main.go` wires probes but not `Metrics`** — confirm metrics exposure in your branch / OLM deployment | | | |
| **Single reconciler** | **NodeMaintenance** only | | | |

## Integrations

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **kube-openapi drain** | **`k8s.io/kubectl/pkg/drain`** | | | |
| **KubeVirt / VMI** | Comments: **Force** / **DeleteEmptyDirData** for **VirtualMachineInstance** pods | | | |
| **NHC / lease sharing** | **AlreadyHeld** handling when another holder owns lease | | | |
| **etcd guard PDB** | Webhook: **`openshift-etcd`**, **`etcd-guard-pdb`** / **`etcd-quorum-guard`** names | | | |

## Code map expectation

**`code_map.md`:** **`main.go`**; **`api/v1beta1/nodemaintenance_types.go`**, **`nodemaintenance_webhook.go`**, **`groupversion_info.go`**; **`controllers/nodemaintenance_controller.go`**, **`taint.go`**; **`pkg/utils/`** (events, OpenShift check); **`version/version.go`**.

Update this table when **`memory/verified/nmo/`** or upstream NMO changes; leave a cell empty only if intentionally out of scope for that file.
