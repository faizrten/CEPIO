# Candidate only: production Dockerfile and deployment workflows are unchanged.
FROM python:3.11.17-alpine3.24@sha256:5fb4bc53dd0180955e31e5245b648bbb24a4ac4ab03a1de81513642325220bcd AS os-base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
RUN apk upgrade --no-cache && apk add --no-cache dash

FROM os-base AS builder
WORKDIR /build
COPY . /build
RUN python -m pip install --no-cache-dir --upgrade pip build "setuptools==84.2.1" && python -m build --wheel

FROM os-base AS test-runner
RUN apk add --no-cache git
WORKDIR /build
COPY . /build
RUN python -m pip install --no-cache-dir --upgrade pip "setuptools==84.2.1" && python -m pip install --no-cache-dir -c experiments/base-images/runtime-constraints.txt '.[dev]' && python -m pip install --no-cache-dir --target /test-tools pytest
WORKDIR /work

FROM os-base AS installed
ARG CEPIO_RUNTIME_EXTRAS="mcp"
WORKDIR /app
RUN addgroup -S cepio && adduser -S -G cepio cepio && mkdir -p /data && chown -R cepio:cepio /app /data
COPY --from=builder /build/dist/cepio-*.whl /tmp/
COPY experiments/base-images/runtime-constraints.txt /tmp/constraints.txt
RUN case ",${CEPIO_RUNTIME_EXTRAS}," in *,fabric-sql,*) apk add --no-cache libltdl krb5-libs libstdc++ ;; esac
RUN python -m pip install --no-cache-dir --upgrade pip "setuptools==84.2.1" && wheel="$(ls /tmp/cepio-*.whl)" && python -m pip install --no-cache-dir --only-binary=:all: -c /tmp/constraints.txt "${wheel}[${CEPIO_RUNTIME_EXTRAS}]" && python -m pip check && python -m pip freeze --all > /tmp/runtime-freeze.txt

FROM installed AS runtime
RUN python -m pip uninstall --yes pip && python -c "import pathlib, shutil, sysconfig; shutil.rmtree(pathlib.Path(sysconfig.get_path('stdlib'))/'ensurepip', ignore_errors=True)" && rm -f /tmp/cepio-*.whl /tmp/constraints.txt
COPY scripts/minimize_runtime.py /tmp/minimize_runtime.py
COPY experiments/alpine-hardening/harden.py /tmp/harden.py
RUN CEPIO_IMAGE_BUILD=1 python /tmp/harden.py && python -c "from pathlib import Path; Path('/tmp/harden.py').unlink(); Path('/tmp/minimize_runtime.py').unlink()"
USER cepio
EXPOSE 8000
CMD ["sh", "-c", "uvicorn cepio.host_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
