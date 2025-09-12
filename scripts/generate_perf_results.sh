#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="docs/scoreboard/profiles"
mkdir -p "${OUT_DIR}"

export PPC_PROFILE_OUT="${OUT_DIR}"

# Preserve the same perf binary runs as before
scripts/run_tests.py --running-type="performance"

echo "Perf runs completed. HTML profiles are in ${OUT_DIR}"
