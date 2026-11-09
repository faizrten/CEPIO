# Single-purpose read-only discovery image. This is NOT the CEPIO API image.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml setup.py /app/
COPY src /app/src
COPY ontologies /app/ontologies
COPY mappings /app/mappings
COPY shapes /app/shapes
COPY actions /app/actions
COPY policies /app/policies
COPY profiles /app/profiles
COPY ontology-modules.yaml /app/ontology-modules.yaml
COPY scripts/cognite_oid_m0_cloud.py /app/scripts/cognite_oid_m0_cloud.py

RUN python -m pip install --no-cache-dir \
      . "cognite-sdk>=8,<9" "azure-identity>=1.20,<2" "azure-storage-blob>=12.24,<13" \
    && python -m pip check \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin cepio
USER cepio

CMD ["python", "/app/scripts/cognite_oid_m0_cloud.py"]
