.PHONY: test demo api validate blind-ask

test:
	pytest -q

demo:
	PYTHONPATH=src python examples/demo.py

blind-ask:
	PYTHONPATH=src python scripts/run_drilling_mvp_blind_ask.py --telemetry-points 600 --waveform-samples 512

validate:
	PYTHONPATH=src python -c "from pathlib import Path; from cepio.validation import validate_shacl; r=validate_shacl(Path('examples/satorp_hydrocracker.ttl'), Path('shapes/core.shacl.ttl'), ontology_dir=Path('ontologies')); print(r); raise SystemExit(0 if r.conforms else 1)"
	$(MAKE) blind-ask

api:
	uvicorn cepio.api:app --reload
