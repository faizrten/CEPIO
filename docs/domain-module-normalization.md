# CEPIO domain-module normalization from SEO and AD

SEO (refinery/petrochemical + EPC/operations) and AD (asset-heavy drilling contractor) are reference customer ontologies, not CEPIO's canonical type system.

## Normalization rule

Promote a concept into CEPIO only when it is reusable outside the source customer's implementation. Keep company/project/regulator-specific semantics in a customer profile.

```text
CEPIO FOUNDATION
  core | lifecycle | kinetic
          |
          v
CEPIO INDUSTRIAL COMMON
  asset | work | reliability | HSE | supply | performance
  workforce | agentic operations | industrial
          |
          +-------------------------------+
          v                               v
CEPIO DOMAIN                         CEPIO ENTERPRISE
  process industry                      commercial
  EPCIC                                 enterprise
  drilling
  energy
          |
          v
CUSTOMER PROFILES
  SEO / SATORP                          AD / ARO
```

SEO and AD share only four exact class names (`WorkOrder`, `FailureMode`, `ProcessSafetyEvent`, `SparePart`), but they share much more semantically. SEO `Equipment` and AD `EquipmentItem` both map to `ind:Equipment`; SEO `Permit` and AD `PermitRecord` both map to `hse:WorkPermit`; SEO spare stock and AD `PartStock` both use `supply:InventoryPosition`.

## Module responsibilities

- **asset**: Site, Area, FunctionalLocation, AssetSystem, InstalledAsset, AssetPosition.
- **work management**: WorkOperation, MaintenanceNotification, MaintenanceCampaign, Turnaround, WorkPackage; retains `ind:WorkOrder`.
- **reliability**: FailureMode, FailureEvent, DowntimeEvent, ComponentLife, ConditionSignal, RemainingUsefulLifeEstimate.
- **HSE**: WorkPermit, SafetyCase, RiskAssessment, ProcessSafetyEvent, Incident, DroppedObjectEvent, CorrectiveAction, AuditFinding, inspection/compliance/drill/exposure/security concepts.
- **supply**: InventoryPosition and MaterialRequirement around existing SparePart and Supplier.
- **performance**: KPIObservation, Scorecard, ScoreDimension, AssetScore, AssetStatus, Benchmark, CompositeScore, FleetException and ActionPerformance.
- **workforce**: CrewMember, CrewAssignment, Certification, TrainingRequirement, TrainingCompliance, CompetencyAssessment and CompetencyEvidence.
- **agentic operations**: Agent, Recommendation, ActionCase, ControlPoint, AgentRun and AuditEntry. These extend the kinetic layer but grant no execution authority by themselves.
- **process industry**: ProcessStream, UtilityMeter, emissions, quality, operational events and optimization forecasts over ProcessUnit.
- **EPCIC**: DesignTag, DesignValue, CommissioningSystem, EPCPackage, CommissioningActivity, HandoverDocument, HandoverFinding and ProjectControlRecord. The key bridge is `InstalledAsset -> realizesDesignTag -> DesignTag`.
- **drilling**: FleetUnit, OperatingRig, ConstructionRig, RigSystem, DrillingEquipment, WellContext, DrillingCampaign, RigOperationalEvent and drilling contract specializations.
- **commercial**: ContractObligation, FinancialActual, RevenueRecord, CostRecord, CapitalItem, EconomicEvent, ValueAtRisk, PriceDeck and EconomicScenario.

## AD shared features

AD's feature model is treated as a design signal rather than copied as business entities: `Entity` maps to CEPIO Entity, `RigLinked` becomes an explicit relationship to OperatingRig, `DatedEvent` maps to Event plus temporal semantics, `Measured` maps to Measurement, `Ranked` maps to performance semantics, `Flagged` maps to Risk/State, `AgentAttributed` maps to agentic/provenance, and TableSourced/MeasureSourced become provenance rather than domain classes. `GovernedChange` belongs in the kinetic action/audit layer.

## Customer-profile concepts deliberately not promoted

Examples: SEO `AmiralAsset`; AD `AramcoInspection`, `OapProtocolCheck`, `ReiScore`, `ReiCategoryScore`, `ReiHseComponent`, `AroReiPerformance` and leadership-risk profile concepts. These remain valid customer concepts but map onto CEPIO common/domain types.

## Identity rule

CEPIO v0.2 runtime currently resolves types by local name. Canonical local names therefore remain globally unique across modules. Before customer profile RDF is loaded directly, the runtime should move to qualified type IDs/IRIs with backwards-compatible aliases; until then, profile semantics stay in mapping files or external Fabric definitions.

## Mapping files

- `mappings/seo_to_cepio.csv`: all 42 SEO Fabric entity types.
- `mappings/ad_to_cepio.csv`: all 59 AD core entity types.
- `ontology-modules.yaml`: module/dependency catalogue.
