from __future__ import annotations
import os, subprocess, sys
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

    assert (outdir / "interim_clean.csv").is_file()
    assert (outdir / "report.json").is_file()
    assert any(outdir.glob("hist_*.png"))
