#!/usr/bin/env bash
# Run the complete suite and generate Jenkins-compatible test/coverage reports.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mkdir -p reports

uv run --locked pytest \
  --junitxml=reports/junit.xml \
  --cov=finsecure_pay \
  --cov-report=term-missing \
  --cov-report=xml:reports/coverage.xml
