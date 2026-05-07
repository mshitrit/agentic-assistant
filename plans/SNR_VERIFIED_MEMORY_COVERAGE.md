# SNR verified memory — coverage checklist

Use this when writing or reviewing **`memory/verified/snr/`**. Every row should be covered somewhere: **architecture** (behaviour), **failure_modes** (symptoms), **runbook** (commands / what to inspect). **overview** only needs a short mention if it helps readers; **code_map** is optional file pointers.

Legend: ✓ = intentionally covered in that file’s prose.

## `SelfNodeRemediation` spec & runtime contract (`api/v1alpha1/selfnoderemediation_types.go`, controller)

| Topic | Spec / behaviour | architecture | failure_modes | runbook |
|-------|------------------|:------------:|:-------------:|:-------:|
| Remediation strategies | `remediationStrategy`: **Automatic**, **ResourceDeletion**, **OutOfServiceTaint**; **Automatic** vs **IsOutOfServiceTaintGA** | ✓ | ✓ | ✓ |
| Phase machine | **Fencing-Started → Pre-Reboot-Completed → Reboot-Completed → Fencing-Completed**; manager vs agent roles | ✓ | ✓ | ✓ |
| Conditions | **Processing**, **Succeeded**, **Disabled**; **`status.lastError`** | ✓ | ✓ | ✓ |
| Safe timing | **`status.timeAssumedRebooted`**; **`RebootDurationCalculator`** / config minimum | ✓ | ✓ | ✓ |
| NHC timeout | Annotation **`remediation.medik8s.io/nhc-timed-out`** | ✓ | ✓ | ✓ |
| Target node resolution | NHC owner vs **Machine** vs name / **`remediation.medik8s.io/node-name`** | ✓ | ✓ | ✓ |
| Exclude label | Node label **`remediation.medik8s.io/exclude-from-remediation=true`** | ✓ | ✓ | ✓ |
| Taints / cleanup | **NoSchedule** remediation taint; **out-of-service** taint when strategy uses it; finalizer | ✓ | ✓ | ✓ |

## `SelfNodeRemediationConfig` (`selfnoderemediationconfig_types.go`, config reconciler)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| Required singleton | Name **`self-node-remediation-config`**; missing → **Disabled** | ✓ | ✓ | ✓ |
| API check tuning | **`apiCheckInterval`**, **`apiServerTimeout`**, **`maxApiErrorThreshold`** | ✓ | ✓ | ✓ |
| Peer tuning | **`peerUpdateInterval`**, dial/request timeouts, **`minPeersForRemediation`**, **`hostPort`** | ✓ | ✓ | ✓ |
| Reboot safety | **`safeTimeToAssumeNodeRebootedSeconds`** vs calculated minimum; **`isSoftwareRebootEnabled`** | ✓ | ✓ | ✓ |
| Watchdog | **`watchdogFilePath`**; node **watchdog-timeout** annotation | ✓ | ✓ | ✓ |
| Agent scheduling | **`customDsTolerations`** (and env mirroring) | | | ✓ |
| Control-plane diagnostics | **`endpointHealthCheckUrl`** / **`controlplane.Manager`** | ✓ | ✓ | ✓ |

## Operator binary: manager vs agent (`main.go`, `install/`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| **Manager** (`--is-manager`) | Webhooks, **Config** reconciler, DaemonSet from **`install/`**, **SNR** reconciler **without** reboot | ✓ | ✓ | ✓ |
| **Agent** (default) | Watchdog, API check, peers, **gRPC peer health**, **Rebooter** | ✓ | ✓ | ✓ |
| Admission webhooks | **Config** / **Template** / **SNR** validation & defaults | ✓ | | |
| Default **Template** | **`template.Creator`** / default **Automatic** template | ✓ | | |
| gRPC TLS | **Certificates** package; **node ↔ node** port | ✓ | | ✓ |

## Connectivity, peers, reboot (`pkg/apicheck`, `pkg/peers`, `pkg/peerhealth`, `pkg/reboot`)

| Topic | Behaviour | architecture | failure_modes | runbook |
|-------|-----------|:------------:|:-------------:|:-------:|
| API connectivity | **`/readyz?exclude=shutdown`**; threshold before peer path | ✓ | ✓ | ✓ |
| Peer quorum / isolation | **`MinPeersForRemediation`**; **HealthyBecauseNoPeersWereFound** / **UnHealthyBecauseNodeIsIsolated** | ✓ | ✓ | ✓ |
| Reboot execution | **Watchdog** stop vs **software reboot** (`sysrq`); **`TimeToAssumeRebootHasStarted`** | ✓ | ✓ | ✓ |
| Duplicate reboot guard | **Uptime** vs CR creation (**`didIRebootMyself`**) | | ✓ | ✓ |
| Strategy timeouts | **OutOfService** housekeeping window (**`OutOfServiceTimeoutDuration`**) | ✓ | ✓ | ✓ |

## Integrations & scope

| Topic | Where | architecture | failure_modes | runbook |
|-------|-------|:------------:|:-------------:|:-------:|
| **NHC** | Creates **SNR** CRs; orchestration contract | ✓ | ✓ | ✓ |
| **SBR** coexistence | Watchdog / fencing conflict; detect-only patterns | ✓ | | ✓ |
| **Machine API** | **Machine** owner; **`nodeRef`** | ✓ | ✓ | ✓ |

**Optional:** **`code_map.md`** points at `main.go`, `selfnoderemediation_controller.go`, `owner_and_name.go`, `selfnoderemediationconfig_controller.go`, `pkg/*` — not ticked per row above.

Update this table if **`memory/verified/snr/`** changes; leave a cell empty only if intentionally out of scope for that file.
