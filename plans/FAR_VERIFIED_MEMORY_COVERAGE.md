# FAR verified memory — coverage checklist

Use this when writing or reviewing **`memory/verified/far/`**. Each row should be covered in **architecture** (behaviour), **failure_modes** (symptoms / failure behaviour), **runbook** (ops / `kubectl`). **overview** is optional short context; **code_map** maps repo files to topics.

**Upstream / code reference:** `github.com/medik8s/fence-agents-remediation`.

Legend: ✓ = intentionally covered in that file’s prose (tick when verified memory exists).

## API scope

- **Group:** `fence-agents-remediation.medik8s.io`, **`v1alpha1`**
- **Kinds:** `FenceAgentsRemediation` (short **`far`**), `FenceAgentsRemediationTemplate` (short **`fartemplate`**)
- **Scope:** **Namespaced** (CRs and referenced **Secrets** use the **same namespace** as the FAR/Template CR)

## `FenceAgentsRemediation` spec & runtime (`api/v1alpha1/fenceagentsremediation_types.go`, `controllers/fenceagentsremediation_controller.go`, `api/v1alpha1/fenceagentsremediation_params.go`)

| Topic | Spec / behaviour (code truth) | architecture | failure_modes | runbook |
|-------|----------------------------------|:------------:|:-------------:|:-------:|
| Target node | **`GetNodeName`**: annotation **`remediation.medik8s.io/node-name`** or **`metadata.name`**; node must exist or **NodeNotFound** path | | | |
| Agent | **`spec.agent`**, pattern **`fence_.+`**; binary must exist under **`/usr/sbin/`** (webhook) | | | |
| Fence **action** | Only **`reboot`** or **`off`**; default **`--action=reboot`** if omitted when building CLI args | | | |
| Retries / timeout | **`retrycount`** (default 5), **`retryinterval`** (default 5s), **`timeout`** (default 60s); used by **`Executer`** exponential backoff | | | |
| **SharedParameters** / **NodeParameters** | Merge + overrides; **`{{.NodeName}}`** templates (`pkg/template`) | | | |
| **SharedSecretName** / **NodeSecretNames** | Secret data merged; shared templated per node; node secret overrides; **not-found** errors surface from **`BuildFenceAgentParams`** | | | |
| **SharedSecretName** legacy default | **Mutating** webhook may set/remove **`fence-agents-credentials-shared`**; **validating** webhook blocks clearing name if secret still exists | | | |
| **RemediationStrategy** | **`ResourceDeletion`** or **`OutOfServiceTaint`**; empty spec treated as **ResourceDeletion** in controller | | | |
| **OutOfServiceTaint** vs K8s version | Rejected on admission if cluster is **below Kubernetes 1.26** per **`OutOfServiceTaintValidator`** | | | |

## Reconcile flow & side effects (`controllers/fenceagentsremediation_controller.go`, `pkg/utils/taints.go`, medik8s `common`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **NHC timeout** | Annotation **`remediation.medik8s.io/nhc-timed-out`** (medik8s common): stop / cleanup; if deleting, **`handleFARDeletion`** | | | |
| **Finalizer** | **`fence-agents-remediation.medik8s.io/far-finalizer`**; add on create; remove after taint cleanup on delete | | | |
| **Remediation taint** | **`remediation.medik8s.io/fence-agents-remediation:NoSchedule`** | | | |
| **Phase logic (conditions)** | **RemediationStarted** → **Processing=true**; async fence → **FenceAgentActionSucceeded**; then **DeletePods** or **OOS taint** → **Succeeded** | | | |
| **Fence execution** | **`Executer.AsyncExecute`**: one goroutine per **FAR UID**; **`Exists`** skips duplicate runs | | | |
| **Fence failure / timeout** | **`FenceAgentFailed`** / **`FenceAgentTimedOut`** via **`pkg/cli` executer** status update | | | |
| **ResourceDeletion** | **`commonResources.DeletePods`** (RBAC includes **pods**, **volumeattachments**, etc.) | | | |
| **OutOfService taint** | **`node.kubernetes.io/out-of-service=nodeshutdown:NoExecute`** with **TimeAdded** | | | |
| **CR deletion cleanup** | Remove **OOS** taint if used; remove **remediation** taint; **RemoveFinalizer**; conflict → **RequeueAfter 1s** | | | |
| **Status cache** | After status **Update**, poll up to **5s** for cache freshness | | | |
| **Node not found** | **RemediationFinishedNodeNotFound**; event **NodeNotFound** | | | |

## `FenceAgentsRemediationTemplate` (`api/v1alpha1/fenceagentsremediationtemplate_types.go`, `controllers/fenceagentsremediationtemplate_controller.go`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **statusValidationSample** | **`IntOrString`**: count or **percent**; **`0` / unset** → validation **skipped**; invalid → condition **False**, event | | | |
| Sample capping | Scaled value **capped** to node count (warning event) | | | |
| **Status command** | **`agent --action=status`** + params (action params stripped); **15s** timeout | | | |
| **Success criterion** | **stdout** contains **STATUS: ON** / **STATUS:ON** / leading **ON** (agent-specific) | | | |
| **Status condition** | **`FenceAgentStatusValidationSucceeded`**: Unknown → True/False; **`validationFailed`** map | | | |

## Admission / webhooks (`api/v1alpha1/fenceagentsremediation_webhook.go`, `fenceagentsremediationtemplate_webhook.go`, `fenceagentsremediation_params.go`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **Validate** | Agent exists, strategy allowed, **template syntax**, **`BuildFenceAgentParams`** per discovered node (or dummy if none) | | | |
| **Mutate FAR** | Shared secret **default workaround** on create/update | | | |
| **Mutate Template** | **`MultipleTemplatesSupportedAnnotation`**, shared secret workaround | | | |

## Operator process (`main.go`, OLM bundle)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **Webhooks** | TLS from **`/apiserver.local.config/certificates`** when present; HTTP/2 optional | | | |
| **Leader election** | Flag in **`main.go`**; **CSV** typically enables **`--leader-elect`** with **2 replicas** | | | |
| **Metrics / probes** | **:8080** metrics, **:8081** health | | | |

## Integrations

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **NHC** | Creates/deletes **FAR** CRs; **nhc-timed-out** annotation | | | |
| **Secrets** | Credentials for fence agents in **same namespace** as CR | | | |

## Code map expectation

**`code_map.md`** should enumerate first-party packages: `main.go`; `api/v1alpha1/*` (types, params+validator, webhooks); `controllers/*`; `pkg/cli/cliexecuter.go`; `pkg/utils/*`; `pkg/template/template.go`; `pkg/validation/validation.go`; `version/version.go`. Note **`pkg/utils/pods.go`** / **`namespaces.go`** may be unused by other packages (utility / tests).

Update this table when **`memory/verified/far/`** or upstream FAR changes; leave a cell empty only if that file is intentionally out of scope.
