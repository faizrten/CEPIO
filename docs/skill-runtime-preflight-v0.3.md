# Maintenance deferral Skill admission v0.3

The `assess-maintenance-deferral` Skill is admissible only when the host proves all of the following for the current runtime and actor:

```text
canonical object and relationship identity
+ Equipment -> ConditionObservation visibility
+ Equipment -> WorkOrder visibility
+ Equipment -> Risk visibility
+ Equipment <- FailureEvent -> FailureMode visibility
+ calculateProductionExposure authorization
+ evaluateMaintenanceDeferralRisk authorization
+ maintenance-deferral-decision proposal authority
+ DeferWorkOrder recommendation/handoff authority
+ Decision -> Action auditability
```

For the least-privilege `ai_agent_recommender` identity, direct `DeferWorkOrder` execution must remain impossible. A manager identity that can execute the action is intentionally over-authorized for the recommendation-only Skill and therefore does not satisfy its READY preflight contract.

READY establishes runtime and actor eligibility only. The specific invocation must still retrieve sufficient current evidence. Missing condition, work-order basis, risk evidence, hard-constraint context or other required evidence must result in `INSUFFICIENT_CEPIO_EVIDENCE`; the host must not reinterpret READY as a safety conclusion.
