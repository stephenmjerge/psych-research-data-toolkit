#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"

CONFIG="configs/dataset_a.toml"
INPUT_OVERRIDE="${DATASET_A_INPUT:-}"
OUTDIR_OVERRIDE="${DATASET_A_OUTDIR:-}"
ALLOW_PHI="${ALLOW_PHI_EXPORT:-}"

CMD=("python3" "-m" "prdt.cli" "--config" "$CONFIG")
if [[ -n "$OUTDIR_OVERRIDE" ]]; then
  CMD+=("--outdir" "$OUTDIR_OVERRIDE")
fi
if [[ -n "$INPUT_OVERRIDE" ]]; then
  CMD+=("--input" "$INPUT_OVERRIDE")
fi
if [[ "$ALLOW_PHI" =~ ^(1|true|yes)$ ]]; then
  CMD+=("--allow-phi-export")
fi

echo "[PRDT] Running Dataset A pipeline: ${CMD[*]}"
"${CMD[@]}"

default_outdir=$(python3 - <<'PY'
import tomllib, pathlib
cfg_text = pathlib.Path('configs/dataset_a.toml').read_text()
data = tomllib.loads(cfg_text)
if 'prdt' in data and isinstance(data['prdt'], dict):
    data = data['prdt']
print(data.get('outdir', 'outputs/dataset-a'))
PY
)
final_outdir="${OUTDIR_OVERRIDE:-$default_outdir}"
echo "[PRDT] Done. Outputs live under $final_outdir"
