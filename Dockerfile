FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN python -m pip install --no-cache-dir --upgrade pip build

COPY pyproject.toml setup.py /build/
COPY src /build/src
COPY ontologies /build/ontologies
COPY mappings /build/mappings
COPY shapes /build/shapes
COPY actions /build/actions
COPY policies /build/policies
COPY profiles /build/profiles
COPY ontology-modules.yaml /build/ontology-modules.yaml

RUN python -m build --wheel

FROM python:3.11-slim

# The hosted CEPIO process always serves /mcp, so MCP is part of the default host
# runtime. Deployments can install additional supported extras explicitly.
ARG CEPIO_RUNTIME_EXTRAS="mcp"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN addgroup --system cepio && adduser --system --ingroup cepio cepio

COPY --from=builder /build/dist/cepio-*.whl /tmp/
RUN python -m pip install --no-cache-dir --upgrade pip "setuptools>=84.1.0" \
    && wheel="$(ls /tmp/cepio-*.whl)" \
    && if [ -n "$CEPIO_RUNTIME_EXTRAS" ]; then \
         python -m pip install --no-cache-dir "${wheel}[${CEPIO_RUNTIME_EXTRAS}]"; \
       else \
         python -m pip install --no-cache-dir "$wheel"; \
       fi \
    && rm -f /tmp/cepio-*.whl

RUN mkdir -p /app /data && chown -R cepio:cepio /app /data
USER cepio

EXPOSE 8000

CMD ["sh", "-c", "uvicorn cepio.host_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
