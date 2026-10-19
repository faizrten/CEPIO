# Reliability IQ v0.3 — Condition Monitoring IQ

## Purpose

REL-IQ-003 interprets governed condition-monitoring evidence before maintenance intervention is selected.

The executable question is:

> Which current condition observations materially deviate from accepted operating condition, how significant is the deterioration, and what evidence should enter reliability intervention review?

The capability is deliberately cross-industrial. It applies to generic `Equipment` and domain-derived equipment such as drilling equipment without creating a domain-specific condition-monitoring ontology.

## Boundary

REL-IQ-003 owns **condition interpretation**. It does not own maintenance execution and it does not replace REL-IQ-001.

```text
condition observations
        ↓
REL-IQ-003
condition deviation + trend
        ↓
review disposition + cited evidence
        ↓
REL-IQ-001
multi-evidence intervention assessment
        ↓
existing governed Decision / Action / approval / audit
```

This prevents a sensor deviation from becoming an automated maintenance instruction without failure, work, risk and authority context.

## Reused semantics

The pack reuses existing CEPIO semantics only:

- `Equipment`
- `ConditionObservation`
- `hasConditionObservation`
- `value`
- `unitSymbol`
- `observedAt`

No canonical ontology or public API change is introduced.

The accepted operating envelope is not asserted as a universal ontology fact. Normal, advisory and material bounds, the expected unit, freshness horizon and trend epsilon are governed assessment/profile configuration so they can vary by equipment class, operating mode, service and customer policy without forking CEPIO semantics.

## Condition states

For each monitored signal, the latest qualified observation is classified against three nested envelopes:

- `NORMAL` — inside the accepted normal envelope;
- `ADVISORY_DEVIATION` — outside normal but inside the advisory envelope;
- `MATERIAL_DEVIATION` — outside advisory but inside the material envelope;
- `CRITICAL_DEVIATION` — outside the material envelope.

The overall equipment condition is the most severe current signal state.

## Deterioration trend

Trend is intentionally **not** based on whether the raw measurement rises or falls.

For each observation CEPIO calculates distance from the accepted normal band, normalized by the width of that band. The two most recent qualified observations are compared:

- increasing distance beyond the governed epsilon → `DETERIORATING`;
- decreasing distance beyond epsilon → `IMPROVING`;
- movement within epsilon → `STABLE`;
- one qualified observation → `INSUFFICIENT_HISTORY`.

This avoids naïve rules such as “higher is always worse.” A temperature rise, vibration rise, pressure drop or efficiency drop can all represent deterioration depending on the governed operating envelope.

The normalized distance is an interpretable intermediate calculation; it is **not** a synthetic reliability or health score.

## Evidence qualification

Every supplied observation must:

1. be a governed `ConditionObservation`;
2. be linked to the assessed `Equipment` by `hasConditionObservation`;
3. carry a numeric `value`;
4. carry a `unitSymbol` matching the governed signal configuration;
5. carry a timezone-aware `observedAt` timestamp;
6. not be future evidence at assessment time;
7. remain inside the configured observation-freshness horizon.

Duplicate observation IDs are rejected globally. Duplicate timestamps inside one signal are rejected because they make chronological trend interpretation ambiguous.

Signal identifiers must also be unique within one assessment.

## Governed envelopes

Each signal uses nested ranges:

```text
material_low
  ≤ advisory_low
  ≤ normal_low
  < normal_high
  ≤ advisory_high
  ≤ material_high
```

Invalid or overlapping configuration fails closed. This makes the severity interpretation explicit and testable rather than embedding hidden thresholds in model behavior.

## Review dispositions

REL-IQ-003 returns an advisory review disposition, not an action:

- `MONITOR`
- `INSPECTION_REVIEW`
- `MAINTENANCE_REVIEW`
- `RISK_REVIEW`

Current severity is primary. A deteriorating trend can increase the review urgency for advisory or material conditions. Any actual `CreateInspection`, `CreateWorkOrder`, `EscalateRisk` or other side effect remains under REL-IQ-001 and the existing CEPIO governed action path.

## North-star alignment

```text
Authoritative historian / condition source
              ↓
replaceable binding
              ↓
ConditionObservation evidence
              ↓
REL-IQ-003 Condition Monitoring IQ
              ↓
condition state + normalized trend + provenance
              ↓
REL-IQ-001 intervention assessment
              ↓
human/governed execution
```

The source remains authoritative. CEPIO does not train from customer condition data, does not copy historian schemas into Core, and does not create customer-specific ontology forks for operating thresholds.
