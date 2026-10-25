# Keep the current Python minor and Debian release explicit in both stages.
FROM python:3.11.17-slim-trixie@sha256:b7a9e5f6a93d6d4a31f129bbd4bdee69efccb6ded0fb230d78aafaf37af98377 AS os-base

# Apply only upgrades available from the base's existing stable repositories.
# Fail on index errors; upgrade cannot add/remove packages or change releases.
# Run before user setup and runtime minimization, while maintenance tools exist.
RUN apt-get update -o APT::Update::Error-Mode=any \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-remove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

FROM os-base AS builder

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

FROM os-base

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
    && python -m pip check \
    && python -m pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python3.11/ensurepip \
    && python -c "import importlib.util; assert importlib.util.find_spec('pip') is None; assert importlib.util.find_spec('ensurepip') is None" \
    && rm -f /tmp/cepio-*.whl

# The service never needs setuid/setgid helpers. Preserve OS packages and their
# scanner inventory, but remove file-based privilege transitions from the runtime.
RUN find / -xdev -type f -perm /6000 -exec chmod a-s {} + \
    && test -z "$(find / -xdev -type f -perm /6000 -print -quit)"

RUN mkdir -p /app /data && chown -R cepio:cepio /app /data

# Installation/user setup is complete. The HTTP host needs no mount/namespace,
# terminal administration or Perl CLI. Keep shared libraries and dpkg inventory.
COPY scripts/minimize_runtime.py /tmp/minimize_runtime.py
RUN CEPIO_IMAGE_BUILD=1 python /tmp/minimize_runtime.py --apply && rm /tmp/minimize_runtime.py
USER cepio

EXPOSE 8000

CMD ["sh", "-c", "uvicorn cepio.host_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
