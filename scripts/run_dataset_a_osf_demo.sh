#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -d ".venv" ]]; then
  source .venv/bin/activate
else
  echo "[PRDT] Missing .venv; create it with 'python3 -m venv .venv && source .venv/bin/activate && pip install -e .[dev]'." >&2
  exit 1
fi

mkdir -p .cache/mpl
export MPLBACKEND=Agg
export MPLCONFIGDIR="$REPO_ROOT/.cache/mpl"
export PRDT_ANON_KEY="${PRDT_ANON_KEY:-$(openssl rand -hex 32)}"

DATASET_A_INPUT="${DATASET_A_INPUT:-$REPO_ROOT/data/examples/dataset_a_demo.csv}" \
DATASET_A_OUTDIR="${DATASET_A_OUTDIR:-$REPO_ROOT/outputs/dataset-a-osf}" \
scripts/run_dataset_a.sh
