# Drilling-contractor persona expansion — v0.2

## Purpose

Harness v0.1 proved CEPIO against ten contractor-management personas. This v0.2 challenge expands the test surface toward the real operating network around a drilling rig: offshore command, frontline drilling, technical maintenance, subsea/well control, specialist service companies, the operator/customer interface, finance, crewing, marine moves and procurement.

The original v0.1 persona and competency artifacts remain unchanged. The v0.2 expansion is a separate frozen challenge so semantic movement can be measured without rewriting the original benchmark.

## Persona coverage

The v0.2 persona pack contains 24 personas: the original ten plus fourteen additions.

### Existing v0.1 personas

- Rig Manager
- Drilling Superintendent
- Toolpusher
- Reliability Engineer
- Maintenance Planner
- HSE Manager
- Competency and Training Manager
- Supply Chain Manager
- Commercial Manager
- Fleet Executive

### Added v0.2 personas

- Offshore Installation Manager / Rig Superintendent
- Driller
- Assistant Driller
- Subsea / Well Control Engineer
- Chief Mechanic
- Chief Electrician
- Directional Drilling Service Lead
- Drilling Fluids Engineer
- Cementing Supervisor
- Operator Company Man / Wellsite Leader
- Finance Controller / CFO Representative
- Crewing / HR Manager
- Marine / Rig Move Manager
- Procurement / Category Manager

The IADC KSA, WellSharp/WellSharp Plus and competence-assurance role taxonomies are used as role-coverage challenges. They are references, not copied canonical CEPIO semantics.

## New competency pressure

The frozen `drilling-contractor-persona-expansion-v0.2` pack adds 14 questions covering:

1. offshore command authority and its HSE boundaries;
2. driller-to-current-activity and deviation context;
3. tour/shift handover continuity;
4. BOP/subsea readiness accountability;
5. chief-mechanic work ownership and availability consequence;
6. chief-electrician isolation and permit context;
7. directional-drilling service-provider accountability and acceptance evidence;
8. drilling-fluid properties, treatment and materials;
9. cementing readiness and post-job quality evidence;
10. operator acceptance and authorization of program deviations;
11. integrated rig margin/cash exposure;
12. crew rotation and mobilization readiness;
13. marine/jack-up rig-move execution readiness;
14. procurement exposure from material/service constraint to rig work or campaign consequence.

## Design rules

- Listing a persona is insufficient: every added persona must be exercised by at least one frozen competency question.
- Questions are phrased in operating language, not ontology vocabulary.
- Missing semantics are expected and desirable at this stage; the pack must create real pressure on CEPIO.
- A missing term is not permission to add that literal term to the ontology. Gaps must later be triaged as `CORE`, `DOMAIN`, `PROFILE`, `MAPPING` or `REJECT`.
- Operator, contractor and service-company responsibilities must remain distinct rather than being flattened into one enterprise actor.

## External grounding

Public IADC materials explicitly recognize roles such as driller, assistant driller, toolpusher/company man, drilling superintendent, rig superintendent/rig manager, chief mechanic, chief electrician, directional-drilling/MLWD personnel and subsea technicians. The CEPIO standards registry retains the public reference surfaces used by the harness.

## Next step

Run the expanded frozen pack against the current CEPIO ontology, quantify PASS/PARTIAL/FAIL and semantic-check coverage, then triage the newly exposed gaps before any ontology remediation is proposed.
