# MDR verified memory — coverage checklist

Use this when writing or reviewing **`memory/verified/mdr/`**. Each row should be covered in **architecture** (behaviour), **failure_modes** (symptoms / failure behaviour), **runbook** (ops / `kubectl`). **overview** is optional short context; **code_map** maps repo files to topics.

**Upstream / code reference:** `github.com/medik8s/machine-deletion-remediation` (Go module name; local clone directory may be **`machine-deletion`**).

Legend: ✓ = intentionally covered in that file’s prose (tick after verified memory exists).

## API scope

- **Group:** `machine-deletion-remediation.medik8s.io`, **`v1alpha1`**
- **Kinds:** `MachineDeletionRemediation` (short **`mdr`**), `MachineDeletionRemediationTemplate` (short **`mdrt`**)
- **Scope:** **Namespaced**
- **`MachineDeletionRemediation.spec`:** **empty** (placeholder in types)
- **`MachineDeletionRemediationTemplate`:** embeds the same **spec** for **NHC** — this operator has **no Template reconciler** (template CRD is for NHC / API only)

## `MachineDeletionRemediation` — identity & Machine resolution (`controllers/machinedeletionremediation_controller.go`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| CR **name** ↔ **Node** (typical NHC) | **`getNodeFromCR`** loads **Node** named **`mdr.Name`** | | | |
| **Machine** from saved annotation | **`machine-deletion-remediation.medik8s.io/machineNameNamespace`** → `namespace/name` | | | |
| **Machine** from **ownerReference** | Owner **`Kind: Machine`** → machine name + **MDR namespace** | | | |
| **Machine** from **Node** | Node **`machine.openshift.io/machine`** → `namespace/name` | | | |
| Bad **`machineNameNamespace`** value | **`unrecoverableError`** | | | |

## Reconcile flow & side effects

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **NHC timeout** | **`remediation.medik8s.io/nhc-timed-out`** (medik8s common), only if **`DeletionTimestamp` is nil** | | | |
| **RemediationStarted** | First condition transition → **requeue 1s** | | | |
| **Node not found** | **`RemediationCannotStartNodeNotFound`**; **`GetTargetNodeFailed`** event | | | |
| **Machine not found** (never handled) | **`RemediationCannotStartMachineNotFound`** | | | |
| **Machine** gone or **newer** than MDR | **`machine == nil`** or **`Machine.CreationTimestamp` after MDR** → wait for **`isExpectedNodesNumberRestored`** | | | |
| **Node count restoration** | Owner from **`machine-deletion-remediation.medik8s.io/machineOwner`** (`kind/name`) → load **MachineSet** or **ControlPlaneMachineSet** → compare **`spec.replicas`** to nodes whose **Machine** chains to that owner; **`replicas == 0`** → success without count check | | | |
| Owner kind not **MachineSet** / **ControlPlaneMachineSet** | **`unrecoverableError`** | | | |
| **PermanentNodeDeletionExpected** | **`Machine.spec.providerID`**: **`baremetal`** prefix → **False**; else → **True**; empty/missing → **Unknown** | | | |
| **Machine** already **deleting** | Log **phase**; **requeue 30s** | | | |
| **Machine** has **no controller owner** | **`RemediationCannotStartNoControllerOwner`** | | | |
| **Persist Machine** | Annotations **`machineNameNamespace`**, **`machineOwner`** before **Delete** | | | |
| **Delete Machine** | **`Delete`**; **RemediationStarted** event; **requeue** | | | |
| **Deferred status** | **`Status().Update`** in defer; conflict → **requeue 1s** | | | |
| **Processing** stuck **False** | Once **Processing** is **False**, it is **not** set back to **True** (`remediationStarted` no-op) | | | |

## Status conditions

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **Processing** / **Succeeded** | **Started**, **MachineDeleted**, **NHC timeout**, **cannot start** / **Failed** pairs | | | |
| **PermanentNodeDeletionExpected** | Reasons from **`api/v1alpha1`** constants (cloud vs baremetal vs undefined) | | | |

## RBAC / runtime (`main.go`, RBAC markers)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **OpenShift Machine API** | Scheme **`machine.openshift.io` v1 / v1beta1**; RBAC **machines**, **machinesets**, **controlplanemachinesets** | | | |
| **Nodes** | get/list/watch | | | |

## Operator process (`main.go`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **No webhooks** | Only **MachineDeletionRemediation** reconciler registered | | | |
| **Metrics** | **`:8080`**; metrics TLS opts disable **HTTP/2** | | | |
| **Probes** | **`:8081`** | | | |
| **Leader election** | **`--leader-elect`**; **`LeaderElectionID`** in source — confirm **OLM/CSV** for real deployments | | | |

## `MachineDeletionRemediationTemplate`

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **Template CRD** | **Empty** nested **spec**; **not** reconciled by MDR operator | | | |

## Integrations

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **NHC** | Creates **MDR** (name = node); **`nhc-timed-out`**; removes MDR when node healthy | | | |
| **MHC** | **Machine** ownerReference path | | | |
| **Machine API** | **Machine** delete → replacement by owning controllers | | | |

## Code map expectation

**`code_map.md`:** **`main.go`**, **`api/v1alpha1/*`**, **`controllers/machinedeletionremediation_controller.go`**, **`version/version.go`** — no separate **`pkg/`** app package beyond vendor.

Update this table when **`memory/verified/mdr/`** or upstream MDR changes; leave a cell empty only if intentionally out of scope for that file.
