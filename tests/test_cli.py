from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path


def test_cli_smoke(tmp_path):
    """End-to-end check: CLI should run and emit core outputs."""
    repo_root = Path(__file__).resolve().parents[1]
    input_csv = repo_root / "data" / "examples" / "surveys.csv"
    outdir = tmp_path / "run"

    env = os.environ.copy()
    env["PRDT_ANON_KEY"] = "testkey"

    cmd = [
        sys.executable,
        "-m",
        "prdt.cli",
        "--input",
        str(input_csv),
        "--outdir",
        str(outdir),
        "--score-cols",
        "phq9_total",
        "gad7_total",
    ]

    subprocess.run(cmd, check=True, cwd=repo_root, env=env)

    clean_csv = outdir / "interim_clean.csv"
    report_json = outdir / "report.json"

    assert clean_csv.is_file()
    assert report_json.is_file()
    assert any(outdir.glob("hist_*.png"))

    report = json.loads(report_json.read_text())
    missing = report["missing"]
    alpha = report["cronbach_alpha"]
    assert "count" in missing and "percent" in missing and "detail" in missing
    sample_col = missing["detail"][0]
    assert {"variable", "missing", "missing_pct"} <= sample_col.keys()
    assert alpha is None or isinstance(alpha, float)
