# Refinery Standards & Persona Expansion v0.2

## Purpose

This Generalization Lab slice expands refinery competency **without changing the ontology**. It creates a new frozen challenge so CEPIO can be tested against a broader refinery operating model and a stronger external standards surface while preserving the historical v0.1 benchmark.

The design follows the same discipline used for drilling persona expansion:

1. expand personas and external reference coverage;
2. freeze business questions before remediation;
3. measure current semantic capability;
4. classify every new gap as `CORE / DOMAIN / PROFILE / MAPPING / REJECT`;
5. remediate only accepted abstractions in separate changes.

## Persona expansion

The v0.2 persona pack retains all 14 refinery v0.1 personas and adds 12 roles that were underrepresented in the original challenge:

- Refinery Economist / Planning Engineer;
- Production Scheduler / Blend Planner;
- Field Operator;
- Process Control / APC Engineer;
- Inspection / Corrosion Engineer;
- Electrical / Power Systems Engineer;
- Instrumentation / Analyzer Engineer;
- Engineering Information Manager;
- Asset Management Lead;
- Tank Farm / Product Movements Manager;
- Production Assurance Engineer;
- OT / Automation Engineer.

Total refinery persona coverage becomes **26 roles**.

## Expanded external reference surface

The v0.2 standards registry preserves the existing ISA-95, ISO 14224, IEC 61511, API RP 754 and ISO 50001 references and adds public-metadata grounding for:

- ANSI/ISA-106.00.01-2023 — procedure automation for continuous process operations;
- IEC 62682:2022 — alarm-system management for process industries;
- ISO 20815:2026 — production assurance and reliability management;
- ISO 55001:2024 — asset-management system requirements and decision/value framing;
- API RP 580, 4th edition — risk-based inspection;
- API RP 584, 2nd edition — integrity operating windows;
- ISO 15926-2:2003 — process-plant lifecycle information model;
- DEXPI 2.0.1 — plant/process engineering-data exchange;
- CFIHOS 2.0 — capital-facilities information handover and reference data;
- OPC 30081 PA-DIM 1.02.0 — process-automation device information model;
- NAMUR NOA / NE 175 / NE 176 — monitoring-and-optimization architecture and information model;
- IEEE 841-2021 — severe-duty petroleum/chemical-industry motors;
- IEEE 1584-2018 — arc-flash hazard calculations.

External standards are **challenge evidence, not canonical authority**. Copyrighted publication text is not copied into CEPIO. Open specifications must retain their own licensing and attribution requirements.

## Frozen v0.2 challenge

The new challenge contains 12 source-neutral questions:

| CQ | Competency pressure |
|---|---|
| RP-PE-001 | crude/feed slate, yield and refinery-margin planning |
| RP-PE-002 | production schedule, blending, storage and product movements |
| RP-PE-003 | field procedure execution and work-control gates |
| RP-PE-004 | alarm lifecycle, abnormal situations and control context |
| RP-PE-005 | damage mechanisms, RBI and integrity operating windows |
| RP-PE-006 | electrical assets, motors, isolation and arc-flash study context |
| RP-PE-007 | field-device diagnostics, process variables and functional location |
| RP-PE-008 | P&ID/process topology, engineering handover and source provenance |
| RP-PE-009 | lifecycle asset-management decision and value |
| RP-PE-010 | tankage, transfer-route and inventory constraints |
| RP-PE-011 | production assurance, capacity, availability and production loss |
| RP-PE-012 | brownfield monitoring/optimization data path and semantic device context |

The questions intentionally mix semantics that CEPIO already has with concepts it may not yet support. The benchmark must create genuine semantic pressure; a 100% initial score would indicate that the challenge is too weak or accidentally aligned to the existing vocabulary.

## Expected architectural outcomes

The expansion is designed to reveal different classes of pressure rather than pre-decide ontology additions:

- **CORE candidates** may emerge around generic electrical equipment, asset criticality, availability/capacity or reusable integrity concepts;
- **DOMAIN candidates** may emerge around continuous-process procedures, alarms, movements, blending, process integrity and refinery planning;
- **MAPPING candidates** are expected around DEXPI, CFIHOS, PA-DIM/IEC dictionaries and other external information models;
- **REJECT decisions** should be used whenever a literal challenge term would duplicate an existing CEPIO abstraction or encode an architecture/integration concern as ontology vocabulary;
- **PROFILE** should remain zero unless a genuinely enterprise-specific requirement appears.

No semantic remediation belongs in this v0.2 challenge PR. Gap triage is the next step after the frozen baseline is measured.
