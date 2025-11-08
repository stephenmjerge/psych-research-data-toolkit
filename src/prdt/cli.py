from __future__ import annotations
import argparse, os, json, sys, hashlib, subprocess
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore
from .cleaning import basic_clean
from .anonymize import anonymize_column
from .stats import simple_report
from .plots import save_histograms, save_trend, save_missingness_bar
from .scales import apply_scale_scores
from .schema import normalize_schema, validate_schema, build_data_dictionary
from . import __version__

def _validate_score_columns(df: pd.DataFrame, cols: list[str]) -> None:
    """Ensure requested score columns exist and contain numeric data."""
    if not cols:
        raise SystemExit("[PRDT] Provide at least one --score-col for stats/plots.")

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise SystemExit(f"[PRDT] Missing score columns: {', '.join(missing)}")

    non_numeric = []
    for col in cols:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() == 0:
            non_numeric.append(col)
        df[col] = converted

    if non_numeric:
        raise SystemExit(f"[PRDT] Score columns contain no numeric values: {', '.join(non_numeric)}")

def _normalize_scales(raw_scales: object) -> dict[str, list[str]]:
    """Convert TOML scale definitions to a dictionary of name -> list[str]."""
    if not isinstance(raw_scales, dict):
        return {}

    normalized: dict[str, list[str]] = {}
    for name, payload in raw_scales.items():
        if isinstance(payload, dict):
            items = payload.get("items")
        else:
            items = payload

        if isinstance(items, str):
            items_list = [items]
        elif isinstance(items, list):
            items_list = [str(x) for x in items if isinstance(x, (str, int, float))]
        else:
            continue

        items_list = [str(item) for item in items_list if str(item).strip()]
        if items_list:
            normalized[str(name)] = items_list

    return normalized

def _normalize_score_request(raw_score: object) -> list[str]:
    if raw_score is None:
        return []
    if isinstance(raw_score, dict):
        values = raw_score.get("scales")
    else:
        values = raw_score

    if isinstance(values, str):
        return [values]
    if isinstance(values, list):
        return [str(v) for v in values]
    return []

def _normalize_alerts(raw_alerts: object) -> dict[str, object]:
    if not isinstance(raw_alerts, dict):
        return {}

    alerts: dict[str, object] = {}

    missing_pct = raw_alerts.get("missing_pct")
    if isinstance(missing_pct, (int, float)):
        alerts["missing_pct"] = float(missing_pct)

    rel_raw = raw_alerts.get("reliability")
    if isinstance(rel_raw, dict):
        reliability: dict[str, float] = {}
        for key in ("cronbach_alpha_min", "mcdonald_omega_min"):
            value = rel_raw.get(key)
            if isinstance(value, (int, float)):
                reliability[key] = float(value)
        if reliability:
            alerts["reliability"] = reliability

    return alerts

def _file_hash(path: str, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def _prepare_dataframe(path: str, skip_anon: bool,
                       score_scales: list[str] | None = None,
                       schema_rules: dict[str, object] | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    df_raw = pd.read_csv(path)
    provenance = {
        "input_path": os.path.abspath(path),
        "input_hash": _file_hash(path),
        "raw_rows": len(df_raw),
    }
    df = basic_clean(df_raw)
    if not skip_anon and "participant_id" in df.columns:
        df = anonymize_column(df, "participant_id", out_col="anon_id")

    scored = []
    if score_scales:
        df, scored = apply_scale_scores(df, score_scales)
        provenance["scales_scored"] = scored

    if schema_rules:
        schema_messages = validate_schema(df, schema_rules)
        if schema_messages:
            provenance["schema_messages"] = schema_messages

    provenance["post_clean_rows"] = len(df)
    return df, provenance

def _ensure_outdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _write_data_dictionary(df: pd.DataFrame, outdir: str) -> None:
    _ensure_outdir(outdir)
    dictionary = build_data_dictionary(df)
    dictionary.to_csv(os.path.join(outdir, "data_dictionary.csv"), index=False)

def _write_clean_csv(df: pd.DataFrame, outdir: str) -> None:
    _ensure_outdir(outdir)
    df.to_csv(os.path.join(outdir, "interim_clean.csv"), index=False)
    _write_data_dictionary(df, outdir)

def _write_report(df: pd.DataFrame, cols: list[str], outdir: str,
                  scales: dict[str, list[str]] | None = None,
                  alerts: dict[str, object] | None = None) -> list[dict[str, object]]:
    _validate_score_columns(df, cols)
    if scales:
        for name, items in scales.items():
            if not items:
                raise SystemExit(f"[PRDT] Scale '{name}' must include at least one column")
            _validate_score_columns(df, items)
    report = simple_report(df, cols, scales=scales, alerts=alerts)
    _ensure_outdir(outdir)
    with open(os.path.join(outdir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    alert_items = report.get("alerts", []) or []
    if alert_items:
        with open(os.path.join(outdir, "alerts.json"), "w") as f:
            json.dump(alert_items, f, indent=2)
    else:
        alerts_path = os.path.join(outdir, "alerts.json")
        if os.path.exists(alerts_path):
            os.remove(alerts_path)
    return alert_items

def _write_plots(df: pd.DataFrame, cols: list[str], outdir: str) -> list[str]:
    _validate_score_columns(df, cols)
    _ensure_outdir(outdir)
    produced = []
    produced.extend(save_histograms(df, cols, outdir))
    value_col = cols[0]
    time_col = "date" if "date" in df.columns else None
    id_col = "anon_id" if "anon_id" in df.columns else ("participant_id" if "participant_id" in df.columns else None)
    if time_col and id_col:
        trend_file = save_trend(df, id_col, time_col, value_col, outdir)
        if trend_file:
            produced.append(trend_file)
    missing_file = save_missingness_bar(df, outdir)
    if missing_file:
        produced.append(missing_file)
    return produced

def _run_clean(args: argparse.Namespace) -> None:
    df, provenance = _prepare_dataframe(args.input, args.skip_anon,
                                        args.score_scales, args.schema_rules)
    _ensure_score_cols(args, provenance)
    _write_clean_csv(df, args.outdir)
    print("[PRDT] saved: interim_clean.csv")
    _write_manifest(args.outdir, args, provenance, [], ["interim_clean.csv", "data_dictionary.csv"])

def _print_alert_summary(alerts: list[dict[str, object]]) -> None:
    if not alerts:
        return
    print(f"[PRDT][alerts] {len(alerts)} issue(s) detected (see alerts.json):")
    for alert in alerts[:5]:
        if alert.get("type") == "missingness":
            msg = (f"- Missingness: {alert.get('column')} "
                   f"{alert.get('percent')}% ≥ {alert.get('threshold')}%")
        elif alert.get("type") == "reliability":
            msg = (f"- Reliability: {alert.get('target')} {alert.get('metric')}="
                   f"{alert.get('value')} < {alert.get('threshold')}")
        else:
            msg = f"- {alert}"
        print(msg)
    if len(alerts) > 5:
        print("  ...")

def _run_stats(args: argparse.Namespace) -> None:
    df, provenance = _prepare_dataframe(args.input, args.skip_anon,
                                        args.score_scales, args.schema_rules)
    _ensure_score_cols(args, provenance)
    _write_data_dictionary(df, args.outdir)
    alerts = _write_report(df, args.score_cols, args.outdir,
                           getattr(args, "scales", None), getattr(args, "alerts", None))
    print("[PRDT] saved: report.json")
    _print_alert_summary(alerts)
    outputs = ["report.json", "data_dictionary.csv"]
    if alerts:
        outputs.append("alerts.json")
    _write_manifest(args.outdir, args, provenance, alerts, outputs)

def _run_plot(args: argparse.Namespace) -> None:
    df, provenance = _prepare_dataframe(args.input, args.skip_anon,
                                        args.score_scales, args.schema_rules)
    _ensure_score_cols(args, provenance)
    plot_files = _write_plots(df, args.score_cols, args.outdir)
    print("[PRDT] saved: histogram(s) and trend plot (if feasible)")
    _write_manifest(args.outdir, args, provenance, [], plot_files)

def _run_full(args: argparse.Namespace) -> None:
    df, provenance = _prepare_dataframe(args.input, args.skip_anon,
                                        args.score_scales, args.schema_rules)
    _ensure_score_cols(args, provenance)
    _write_clean_csv(df, args.outdir)
    alerts = _write_report(df, args.score_cols, args.outdir,
                           getattr(args, "scales", None), getattr(args, "alerts", None))
    plot_files = _write_plots(df, args.score_cols, args.outdir)
    print("[PRDT] saved: interim_clean.csv, report.json, and plots")
    _print_alert_summary(alerts)
    outputs = ["interim_clean.csv", "data_dictionary.csv", "report.json"]
    if alerts:
        outputs.append("alerts.json")
    outputs.extend(plot_files)
    _write_manifest(args.outdir, args, provenance, alerts, outputs)

def _split_config_args(argv: list[str]) -> tuple[str | None, list[str]]:
    config_path = None
    cleaned: list[str] = []
    it = iter(range(len(argv)))
    for idx in it:
        arg = argv[idx]
        if arg == "--config":
            if idx + 1 >= len(argv):
                raise SystemExit("[PRDT] --config requires a path")
            config_path = argv[idx + 1]
            next(it, None)
            continue
        if arg.startswith("--config="):
            config_path = arg.split("=", 1)[1]
            continue
        cleaned.append(arg)
    return config_path, cleaned

def _load_config(path: str | None) -> tuple[dict[str, object], dict[str, str]]:
    if not path:
        return {}, {}
    cfg_path = Path(path).expanduser()
    if not cfg_path.exists():
        raise SystemExit(f"[PRDT] Config file not found: {path}")
    content = cfg_path.read_bytes()
    data = tomllib.loads(content.decode())
    config_meta = {
        "path": str(cfg_path),
        "hash": hashlib.sha256(content).hexdigest(),
    }
    profile = data.get("prdt") if isinstance(data, dict) else None
    if isinstance(profile, dict):
        data = profile
    if not isinstance(data, dict):
        raise SystemExit("[PRDT] Config file must contain a [prdt] table or key/value pairs")
    base = cfg_path.parent
    for key in ("input", "outdir"):
        value = data.get(key)
        if isinstance(value, str) and value:
            data[key] = str((base / value).resolve())
    if "score_cols" in data and isinstance(data["score_cols"], str):
        data["score_cols"] = [data["score_cols"]]

    normalized_scales = _normalize_scales(data.get("scales"))
    if normalized_scales:
        data["scales"] = normalized_scales
    else:
        data.pop("scales", None)

    score_list = _normalize_score_request(data.get("score"))
    if score_list:
        data["score"] = score_list
    else:
        data.pop("score", None)

    normalized_alerts = _normalize_alerts(data.get("alerts"))
    if normalized_alerts:
        data["alerts"] = normalized_alerts
    else:
        data.pop("alerts", None)

    schema_cfg = normalize_schema(data.get("schema"))
    if schema_cfg:
        data["schema"] = schema_cfg
    else:
        data.pop("schema", None)

    return data, config_meta

def _merge_config(args: argparse.Namespace, config: dict[str, object], allow_command_override: bool) -> argparse.Namespace:
    if not config:
        return args
    if allow_command_override and isinstance(config.get("command"), str):
        args.command = config["command"]  # type: ignore[assignment]
    for key in ("input", "outdir", "score_cols", "skip_anon"):
        if getattr(args, key, None) is None and config.get(key) is not None:
            setattr(args, key, config[key])
    if config.get("scales") is not None:
        setattr(args, "scales", config["scales"])
    if config.get("alerts") is not None:
        setattr(args, "alerts", config["alerts"])
    if config.get("score") is not None:
        setattr(args, "score_scales", config["score"])
    if config.get("schema") is not None:
        setattr(args, "schema_rules", config["schema"])
    return args

def _finalize_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> argparse.Namespace:
    if not hasattr(args, "scales"):
        args.scales = None
    if not hasattr(args, "alerts"):
        args.alerts = None
    if not hasattr(args, "score_scales"):
        args.score_scales = None
    if not hasattr(args, "schema_rules"):
        args.schema_rules = None
    if args.score_cols is None:
        args.score_cols = ["phq9_total", "gad7_total"]
    missing = [field for field in ("input", "outdir") if getattr(args, field) is None]
    if missing:
        parser.error(f"Missing required options: {', '.join('--' + m.replace('_', '-') for m in missing)}")
    if args.skip_anon is None:
        args.skip_anon = False
    return args

def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--input", help="Path to input CSV")
    common.add_argument("--outdir", help="Directory for outputs")
    common.add_argument(
        "--score-cols",
        nargs="*",
        help="Numeric score columns for descriptives/correlation/plots",
    )
    common.add_argument(
        "--skip-anon",
        action="store_true",
        default=None,
        help="Skip anonymizing participant_id (default anonymizes when present)",
    )

    parser = argparse.ArgumentParser(description="PRDT CLI")
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    sub.add_parser("clean", parents=[common], help="Clean + anonymize CSV and write interim_clean.csv")
    sub.add_parser("stats", parents=[common], help="Generate report.json (descriptives, corr., alpha, missing)")
    sub.add_parser("plot", parents=[common], help="Create histogram/time-trend plots")
    sub.add_parser("run", parents=[common], help="Run the full pipeline (clean + stats + plot)")
    return parser

def main(argv: list[str] | None = None):
    parser = _build_parser()
    raw_args = list(sys.argv[1:] if argv is None else argv)
    config_path, cleaned = _split_config_args(raw_args)
    insert_default_command = not cleaned or cleaned[0].startswith("-")
    if insert_default_command:
        cleaned = ["run"] + cleaned
    args = parser.parse_args(cleaned)
    config, config_meta = _load_config(config_path)
    args = _merge_config(args, config, allow_command_override=insert_default_command)
    args = _finalize_args(args, parser)
    args._config_path = config_meta.get("path")
    args._config_hash = config_meta.get("hash")
    command = args.command
    actions = {
        "clean": _run_clean,
        "stats": _run_stats,
        "plot": _run_plot,
        "run": _run_full,
    }
    action = actions.get(command)
    if not action:
        parser.error(f"Unknown command: {command}")
    action(args)

def _git_sha() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return None

def _write_manifest(outdir: str, args: argparse.Namespace, provenance: dict[str, object],
                    alerts: list[dict[str, object]], outputs: list[str]) -> None:
    manifest = {
        "prdt_version": __version__,
        "git_sha": _git_sha(),
        "run_at": datetime.now(timezone.utc).isoformat(),
        "command": args.command,
        "score_scales": args.score_scales,
        "config_path": getattr(args, "_config_path", None),
        "config_hash": getattr(args, "_config_hash", None),
        "input": {
            "path": provenance.get("input_path"),
            "sha256": provenance.get("input_hash"),
            "raw_rows": provenance.get("raw_rows"),
            "post_clean_rows": provenance.get("post_clean_rows"),
        },
        "schema_messages": provenance.get("schema_messages"),
        "scales_scored": provenance.get("scales_scored"),
        "alerts_count": len(alerts),
        "outputs": sorted(set(outputs)),
        "python_version": sys.version,
    }
    _ensure_outdir(outdir)
    with open(os.path.join(outdir, "run_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

def _ensure_score_cols(args: argparse.Namespace, provenance: dict[str, object]) -> None:
    scored = provenance.get("scales_scored") or []
    if not isinstance(scored, list):
        return
    for entry in scored:
        if not isinstance(entry, dict):
            continue
        col = entry.get("output_column")
        if col and col not in args.score_cols:
            args.score_cols.append(col)

if __name__ == "__main__":
    main()
