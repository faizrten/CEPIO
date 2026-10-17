.PHONY: test demo api validate blind-ask agent-challenge

test:
	pytest -q

demo:
	PYTHONPATH=src python examples/demo.py

blind-ask:
	PYTHONPATH=src python scripts/report_drilling_mvp_blind_ask.py --telemetry-points 600 --waveform-samples 512

agent-challenge:
	PYTHONPATH=src python scripts/run_agent_challenge_strict.py --agent reference --telemetry-points 600 --waveform-samples 512

validate:
	PYTHONPATH=src python -c "from pathlib import Path; from cepio.validation import validate_shacl; r=validate_shacl(Path('examples/satorp_hydrocracker.ttl'), Path('shapes/core.shacl.ttl'), ontology_dir=Path('ontologies')); print(r); raise SystemExit(0 if r.conforms else 1)"
	$(MAKE) blind-ask
	$(MAKE) agent-challenge

api:
	uvicorn cepio.api:app --reload
