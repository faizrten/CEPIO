#!/usr/bin/env bash
# Upstream v1.34.0 Linux amd64 release; no service uploads or paid integration.
set -euo pipefail
destination="${1:?destination required}"
mkdir -p "$destination"
curl --fail --silent --show-error --location --retry 2 \
  https://github.com/oasdiff/oasdiff/releases/download/v1.34.0/oasdiff_1.34.0_linux_amd64.tar.gz \
  --output "$destination/oasdiff.tar.gz"
printf '%s  %s\n' 7c88e09fd500b231af2819eb21f6fdfc7bcdfe2741d2c1937c59e7b72c8a575a "$destination/oasdiff.tar.gz" | sha256sum --check
tar -xzf "$destination/oasdiff.tar.gz" -C "$destination" oasdiff
"$destination/oasdiff" --version
