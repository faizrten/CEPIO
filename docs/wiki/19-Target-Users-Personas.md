# Target Users / Personas

## Who CEPIO is for

CEPIO targets people responsible for industrial operating decisions and the teams building governed applications for them. The strongest near-term product focus is asset reliability and maintenance, followed by wider refinery/process and drilling-contractor operations. This prioritization is a product interpretation of the repository's lighthouse application roadmap and persona artifacts; it is not evidence of deployed adoption.

The roadmap identifies the **Asset Reliability / Maintenance Command Center** as the lighthouse application, with Reliability Engineer, Maintenance Planner, Operations Engineer, Maintenance Manager and Plant Manager as primary personas. Its intended job is to connect degradation detection, consequence assessment, intervention options, recommendation, authorization, work execution and verified outcome. That complete application remains a roadmap objective.

## Industrial end users

The checked-in v0.2 persona catalogs contain **24 drilling-contractor personas** and **26 refinery/process-manufacturing personas**. These are role definitions with objectives and information needs. Their presence establishes modeled demand, not a delivered application or complete runtime coverage for every role.

| User group | Representative catalog roles | Decisions and information needs |
|---|---|---|
| Operations and shift execution | Rig Manager, Toolpusher, Driller, Assistant Driller; Operations Manager, Console Operator, Field Operator, Shift Supervisor | Current state, operating limits, abnormal situations, readiness, handover and unresolved work |
| Reliability and maintenance | Reliability Engineer, Maintenance Planner, Chief Mechanic, Chief Electrician; Asset Management Lead | Failure prevention, condition-based intervention, backlog, availability, criticality and lifecycle tradeoffs |
| Safety, integrity and authority | HSE Manager, Offshore Installation Manager, Subsea / Well Control Engineer; Process Safety Manager, Inspection / Corrosion Engineer | Barriers, permits, isolations, test evidence, degradation risk and bounded authorization |
| Process and technical engineering | Drilling Superintendent, Directional Drilling Service Lead, Drilling Fluids Engineer, Cementing Supervisor; Process Engineer, APC Engineer, Electrical / Power Systems Engineer, Instrumentation / Analyzer Engineer | Program execution, process constraints, equipment or measurement integrity, technical deviations and acceptance evidence |
| Planning and logistics | Marine / Rig Move Manager, Procurement / Category Manager, Supply Chain Manager; Refinery Economist, Production Scheduler / Blend Planner, Tank Farm / Product Movements Manager, Turnaround Manager | Executable schedules, materials, inventory, suppliers, movements, constraints and readiness |
| Workforce readiness | Competency and Training Manager, Crewing / HR Manager | Assignments, role requirements, assessment evidence, valid certifications, rotations and mobilization readiness |
| Commercial and leadership | Commercial Manager, Finance Controller, Fleet Executive, Operator Company Man; Plant Manager, Contractor and Services Manager | Contract obligations, acceptance, production loss, margin, value leakage, capital allocation and accountability |
| Specialist assurance and information | Quality Manager, Environmental Manager, Energy Manager, Production Assurance Engineer, Engineering Information Manager, OT / Automation Engineer | Specifications, emissions, utilities, production exposure, engineering topology, provenance and safe automation interfaces |

The two catalogs overlap in roles such as Reliability Engineer and Finance Controller. The counts describe domain catalog entries, not 50 unique occupations or 50 complete products.

## Platform users and sponsors

Application developers, integration engineers, ontology/domain engineers, agent developers and platform/security administrators are enabling users. They configure profiles, bind source data, build experiences, define governed procedures and maintain identity, policy and audit boundaries. This grouping is a proposed product taxonomy derived from existing API, SDK, profile, integration and governance capabilities; it is separate from the two industrial persona catalogs.

Operations, asset, engineering and digital leadership are plausible sponsors. Buyer segmentation, purchasing authority, willingness to pay and adoption have not been established by the persona artifacts.

AI agents are software consumers acting under authenticated authority. Persona context can guide questions and presentation; authorization comes from runtime identity and policy. A role label does not grant execution rights or create a separate version of enterprise truth.

## Persona-to-capability contract

The design direction is to connect each persona's responsibilities and decisions to frozen competency questions, required capabilities, CEPIO evidence, Functions, Decisions, Actions and assurance results.

For example, a Reliability Engineer needs to determine whether increasing vibration warrants intervention, considering failure history, production exposure, outstanding work and supporting evidence. This requires more than the existence of a `FailureMode` class. The catalog, semantic pack, runtime fixture and eventual application must each make their own coverage explicit.

## Source artifacts

- [Drilling persona catalog](../../generalization/personas/drilling-contractor-v0.2.yaml)
- [Refinery persona catalog](../../generalization/personas/refinery-process-manufacturing-v0.2.yaml)
- [Lighthouse application roadmap](../roadmap.md#lighthouse-application--asset-reliability--maintenance-command-center)


## Related documentation

- [Wiki home](Home.md)
- [Target Users / Personas](19-Target-Users-Personas.md)
- [Competency & Assurance](20-Competency-Assurance.md)
