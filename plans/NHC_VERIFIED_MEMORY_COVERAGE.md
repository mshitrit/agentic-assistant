# NHC verified memory — coverage checklist

Use this when writing or reviewing **`memory/verified/nhc/`**. Every row should be covered somewhere: **architecture** (behaviour), **failure_modes** (symptoms), **runbook** (commands / what to inspect). **overview** only needs a short mention if it helps readers; **code_map** is optional file pointers.

Legend: ✓ = intentionally covered in that file’s prose.

## `NodeHealthCheck` spec (`api/v1alpha1/nodehealthcheck_types.go`)

| Topic | Spec / behaviour | architecture | failure_modes | runbook |
|-------|------------------|:------------:|:-------------:|:-------:|
| Node selection | `selector` (webhook: mandatory non-empty) | ✓ | ✓ | ✓ |
| Unhealthy definition | `unhealthyConditions` (OR; duration from `lastTransitionTime`) | ✓ | ✓ | ✓ |
| Capacity | `minHealthy` **xor** `maxUnhealthy` | ✓ | ✓ | ✓ |
| Storm recovery | `stormCooldownDuration`; conditions **StormActive**, **StormCooldownActive** | ✓ | ✓ | ✓ |
| Remediation mode A | `remediationTemplate` | ✓ | ✓ | ✓ |
| Remediation mode B | `escalatingRemediations` (order, timeout, mutual exclusion with A) | ✓ | ✓ | ✓ |
| Pause | `pauseRequests` | ✓ | ✓ | ✓ |
| Healthy delay | `healthyDelay` (incl. negative semantics) | ✓ | ✓ | ✓ |

## Controller / cluster behaviour (`controllers/`, `main.go`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| Upgrade deferral | OpenShift upgrade checker; requeue when upgrading | ✓ | ✓ | ✓ |
| MHC coexistence | Disable NHC vs ignore **Terminating** (MHC checker) | ✓ | ✓ | ✓ |
| Template validation | Missing/invalid template → **Disabled** | ✓ | ✓ | ✓ |
| Control plane | Serial CP remediation; etcd disruption; CP label on CR | ✓ | ✓ | ✓ |
| Leases | Lease held / overdue; timeout annotation on CR | ✓ | ✓ | ✓ |
| Orphan CR cleanup | Node gone; MDR-style wait on conditions | ✓ | ✓ | ✓ |
| Webhook | Topology; immutability while remediating; MDR+maxUnhealthy | ✓ | ✓ | ✓ |
| Second reconciler | **MachineHealthCheck** when Machine API present | ✓ | | ✓ |
| Bootstrapping | Initializer: RBAC aggregation, console, ServiceMonitor | ✓ | | |

## Status / observability

| Topic | Where | architecture | failure_modes | runbook |
|-------|-------|:------------:|:-------------:|:-------:|
| Phases | `status.phase` / `reason` | ✓ | ✓ | ✓ |
| Disabled / storm | `status.conditions` | ✓ | ✓ | ✓ |
| Per-node tracking | `status.unhealthyNodes`, remediations, `timedOut` | ✓ | ✓ | ✓ |

**Optional:** **`code_map.md`** points at `main.go`, `nodehealthcheck_webhook.go`, `nodehealthcheck_controller.go`, `templates.go`, etc., for deeper dives — not ticked per row above.

Update this table if **`memory/verified/nhc/`** changes; leave a cell empty only if intentionally out of scope for that file.
