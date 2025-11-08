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

    def run_cli(out_path: Path, *extra_args: str) -> None:
        cmd = [
            sys.executable,
            "-m",
            "prdt.cli",
            *extra_args,
            "--input",
            str(input_csv),
            "--outdir",
            str(out_path),
            "--score-cols",
            "phq9_total",
            "gad7_total",
        ]
        subprocess.run(cmd, check=True, cwd=repo_root, env=env)

    run_cli(outdir)

    clean_csv = outdir / "interim_clean.csv"
    report_json = outdir / "report.json"
    alerts_json = outdir / "alerts.json"
    dictionary_csv = outdir / "data_dictionary.csv"
    manifest_json = outdir / "run_manifest.json"
    phi_quarantine = outdir / "phi_quarantine.csv"

    assert clean_csv.is_file()
    assert report_json.is_file()
    assert any(outdir.glob("hist_*.png"))
    assert alerts_json.is_file()
    assert (outdir / "missingness.png").is_file()
    assert dictionary_csv.is_file()
    assert manifest_json.is_file()
    assert phi_quarantine.is_file()

    report = json.loads(report_json.read_text())
    missing = report["missing"]
    alpha = report["cronbach_alpha"]
    omega = report["mcdonald_omega"]
    alerts = report["alerts"]
    assert "count" in missing and "percent" in missing and "detail" in missing
    sample_col = missing["detail"][0]
    assert {"variable", "missing", "missing_pct"} <= sample_col.keys()
    assert alpha is None or isinstance(alpha, float)
    assert omega is None or isinstance(omega, float)
    assert isinstance(alerts, list)
    assert any(alert.get("type") == "phi" for alert in alerts)

    stats_only = tmp_path / "stats_only"
    run_cli(stats_only, "stats")
    assert (stats_only / "report.json").is_file()
    assert not (stats_only / "interim_clean.csv").exists()
    assert (stats_only / "data_dictionary.csv").is_file()
    assert (stats_only / "run_manifest.json").is_file()
    assert (stats_only / "phi_quarantine.csv").is_file()

    config_out = tmp_path / "config_stats"
    config_file = tmp_path / "profile.toml"
    config_text = f"""
[prdt]
command = "stats"
input = "{input_csv}"
outdir = "{config_out}"
score_cols = ["phq9_total", "gad7_total"]
[prdt.score]
scales = ["phq9", "gad7", "phq2_custom"]

[prdt.score.definitions.phq2_custom]
items = ["phq9_item1", "phq9_item2"]
method = "sum"
output = "phq2_score"
[prdt.scales.phq9]
items = ["phq9_item1", "phq9_item2"]

[prdt.scales.gad7]
items = ["gad7_item1", "gad7_item2"]

[prdt.alerts]
missing_pct = 0.0

[prdt.alerts.reliability]
cronbach_alpha_min = 0.95
mcdonald_omega_min = 0.95

[prdt.schema]
required = ["participant_id"]

[prdt.schema.ranges.phq9_item1]
min = 0
max = 3
"""
    config_file.write_text(config_text.strip(), encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "prdt.cli",
            "--config",
            str(config_file),
        ],
        check=True,
        cwd=repo_root,
        env=env,
    )
    assert (config_out / "report.json").is_file()
    config_alerts = config_out / "alerts.json"
    config_manifest = config_out / "run_manifest.json"
    config_dictionary = config_out / "data_dictionary.csv"
    config_phi = config_out / "phi_quarantine.csv"
    config_report = json.loads((config_out / "report.json").read_text())
    scale_rel = config_report["scale_reliability"]
    alert_block = config_report["alerts"]
    descriptives = config_report["descriptives"]
    assert set(scale_rel.keys()) == {"phq9", "gad7"}
    for meta in scale_rel.values():
        assert meta["items"]
        assert meta["cronbach_alpha"] is None or isinstance(meta["cronbach_alpha"], float)
        assert meta["mcdonald_omega"] is None or isinstance(meta["mcdonald_omega"], float)
    assert config_alerts.is_file()
    assert config_manifest.is_file()
    assert config_dictionary.is_file()
    assert config_phi.is_file()
    assert any(alert["type"] in {"missingness", "reliability"} for alert in alert_block)
    assert any(alert.get("type") == "phi" for alert in alert_block)
    assert any(entry.get("variable") == "phq2_score" for entry in descriptives)
