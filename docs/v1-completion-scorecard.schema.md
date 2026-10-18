# CEPIO v1 scorecard change discipline

The scorecard is intentionally simple YAML rather than a database. The repository is the audit trail.

A score change must satisfy all of the following:

- the affected gate remains within its fixed point budget;
- earned points correspond to independently verifiable evidence;
- evidence is phrased so a reviewer can locate the supporting repository, release, deployment or qualification artifact;
- release-gate state is not inferred from the maturity score;
- protected/customer evidence is referenced at an appropriate abstraction level rather than copied into the public repository;
- the calculator and scorecard tests remain green.

Point weights should be changed rarely. Reweighting changes the meaning of historical scores and therefore requires an explicit architecture/product rationale rather than routine progress maintenance.

The intended daily workflow is **read-only**: scheduled reporting reads the canonical score, detects evidence drift and recommends a scorecard PR when the evidence justifies a point change. It must not silently mutate canonical progress.
