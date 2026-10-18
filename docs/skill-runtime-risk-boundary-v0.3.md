# Maintenance risk modelling boundary

CEPIO v0.3 does not claim that one generic formula can determine whether industrial maintenance is safe to defer.

The runtime function `evaluateMaintenanceDeferralRisk` requires governed Risk evidence produced by an appropriate engineering or analytical source and validates that the evidence is linked to the Equipment and WorkOrder under assessment. It interprets the proposed deferral against the supplied supported window and hard-constraint flag. It does not estimate failure probability, consequence, integrity limit, regulatory acceptability or barrier health from first principles.

Those methods belong in domain profiles, operator engineering models, RBI/APM systems or specialized services. CEPIO supplies the governed semantic, policy, decision and action envelope around them.
