.PHONY: test demo api validate

test:
	pytest -q

demo:
	PYTHONPATH=src python examples/demo.py

validate:
	PYTHONPATH=src python -c "from pathlib import Path; from cepio.validation import validate_shacl; r=validate_shacl(Path('examples/satorp_hydrocracker.ttl'), Path('shapes/core.shacl.ttl'), ontology_dir=Path('ontologies')); print(r); raise SystemExit(0 if r.conforms else 1)"

api:
	uvicorn cepio.api:app --reload
