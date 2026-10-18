# Skill capability matrix v0.3

| Logical capability | Runtime capability | v0.3 status |
|---|---|---|
| `Risk` | `core:Risk` | available |
| `hasRisk` | `core:hasRisk` | available |
| `evaluate-maintenance-risk` | `evaluateMaintenanceDeferralRisk` | available |
| `maintenance-deferral-decision` | `maintenance-deferral-decision` | available |
| `defer-work-order` | `DeferWorkOrder` | available |

`ApproveMaintenanceDeferral` remains a separate backward-compatible runtime action and is not used as the logical `defer-work-order` binding.
