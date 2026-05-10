# Node Maintenance Operator (NMO) — Code map

**Repository:** `github.com/medik8s/node-maintenance-operator`

## Purpose

Reader’s map from verified memory into the repo (not a full tour).

## Layout (first-party)

```
node-maintenance-operator/
├── main.go                          # Manager, webhook server, lease initializer, OpenShift probe
├── api/v1beta1/
│   ├── nodemaintenance_types.go     # CRD types, phases, finalizer constant
│   ├── nodemaintenance_webhook.go   # Validating webhook (create/update/delete)
│   ├── groupversion_info.go
│   └── zz_generated.deepcopy.go
├── controllers/
│   ├── nodemaintenance_controller.go # Reconcile, drainer, lease, status
│   ├── taint.go                     # Maintenance taints JSON patch
│   └── *_test.go
├── pkg/utils/                       # Events, OpenShift validator, helpers
├── version/
└── config/                          # Manifests, bundle (OLM)
```

## Where to look

| Question | Start here |
|----------|------------|
| End-to-end **Reconcile** | `controllers/nodemaintenance_controller.go` |
| **Taints** keys/effects | `controllers/taint.go` |
| **Webhook** / etcd quorum | `api/v1beta1/nodemaintenance_webhook.go` |
| **CRD** fields & short name **`nm`** | `api/v1beta1/nodemaintenance_types.go` |
| **Events** reasons/messages | `pkg/utils/events.go` |
| **OpenShift** detection | `pkg/utils/` (e.g. `NewOpenshiftValidator`) |
| **Process flags** / TLS / leader ID | `main.go` |
| **Version** logging | `version/version.go` |

## API short name

| Resource | Short name |
|----------|------------|
| `NodeMaintenance` | `nm` |

## Related pieces

- **`architecture.md`**
- **`runbook.md`**

## Scope

Does not enumerate every **bundle** RBAC rule or CSV env; use **`config/`** / shipped CSV for deployment truth.
