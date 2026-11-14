# Reviewed non-Fabric runtime migration; deployment is a separate authorized action.
FROM python:3.11.17-alpine3.24@sha256:5fb4bc53dd0180955e31e5245b648bbb24a4ac4ab03a1de81513642325220bcd AS os-base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
RUN apk upgrade --no-cache && apk add --no-cache dash

FROM os-base AS builder
WORKDIR /build
RUN python -m pip install --no-cache-dir --upgrade pip build "setuptools==84.2.1"
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

FROM os-base AS runtime
# MCP is required by the hosted composition. Fabric is not installed by default.
ARG CEPIO_RUNTIME_EXTRAS="mcp"
WORKDIR /app
RUN addgroup -S cepio && adduser -S -G cepio cepio && mkdir -p /data && chown -R cepio:cepio /app /data
COPY --from=builder /build/dist/cepio-*.whl /tmp/
COPY requirements/runtime-constraints.txt /tmp/constraints.txt
# Optional extras remain opt-in and require their own environment qualification.
RUN case ",${CEPIO_RUNTIME_EXTRAS}," in *,fabric-sql,*) apk add --no-cache libltdl krb5-libs libstdc++ ;; esac
RUN python -m pip install --no-cache-dir --upgrade pip "setuptools==84.2.1" \
    && wheel="$(ls /tmp/cepio-*.whl)" \
    && if [ -n "$CEPIO_RUNTIME_EXTRAS" ]; then \
         python -m pip install --no-cache-dir --only-binary=:all: -c /tmp/constraints.txt "${wheel}[${CEPIO_RUNTIME_EXTRAS}]"; \
       else \
         python -m pip install --no-cache-dir --only-binary=:all: -c /tmp/constraints.txt "$wheel"; \
       fi \
    && python -m pip check \
    && python -m pip uninstall --yes pip \
    && python -c "import pathlib,shutil,sysconfig; shutil.rmtree(pathlib.Path(sysconfig.get_path('stdlib'))/'ensurepip')" \
    && rm -f /tmp/cepio-*.whl /tmp/constraints.txt
COPY scripts/minimize_runtime.py scripts/harden_alpine.py /tmp/
RUN CEPIO_IMAGE_BUILD=1 python /tmp/harden_alpine.py \
    && python -c "from pathlib import Path; Path('/tmp/harden_alpine.py').unlink(); Path('/tmp/minimize_runtime.py').unlink()"
USER cepio
EXPOSE 8000
CMD ["sh", "-c", "uvicorn cepio.host_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
