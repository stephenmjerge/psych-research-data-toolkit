from __future__ import annotations
import argparse, os, json, sys, hashlib, subprocess, tempfile, platform
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore
from .cleaning import basic_clean
from .anonymize import anonymize_column
from .stats import simple_report, cronbach_alpha
from .plots import (
    save_histograms,
    save_trend,
    save_missingness_bar,
    save_scale_summary,
    save_scale_item_bars,
    _build_scale_scores_from_df,
)
from .scales import apply_scale_scores, ScaleDefinition
from .schema import normalize_schema, validate_schema, build_data_dictionary
from .phi import scan_phi_columns, PhiOptions
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

def _normalize_custom_scales(raw: object) -> dict[str, ScaleDefinition]:
    if not isinstance(raw, dict):
        return {}
    custom: dict[str, ScaleDefinition] = {}
    for name, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        items = payload.get("items")
        if isinstance(items, str):
            items_list = [items]
        elif isinstance(items, list):
            items_list = [str(i) for i in items]
        else:
            continue
        method = payload.get("method", "sum")
        reverse = payload.get("reverse")
        if isinstance(reverse, str):
            reverse = [reverse]
        elif isinstance(reverse, list):
            reverse = [str(r) for r in reverse]
        else:
            reverse = None
        cutoffs = payload.get("cutoffs")
        if not isinstance(cutoffs, dict):
            cutoffs = None
        min_item = payload.get("min_item")
        max_item = payload.get("max_item")
        custom[name] = ScaleDefinition(
            name=name,
            items=items_list,
            method=method,
            reverse=reverse,
            min_item=min_item,
            max_item=max_item,
            cutoffs=cutoffs,
            output=payload.get("output"),
        )
    return custom

def _normalize_phi_options(raw: object) -> PhiOptions | None:
    if not isinstance(raw, dict):
        return None
    extra = raw.get("extra_patterns")
    keywords = raw.get("keywords")
    ignore = raw.get("ignore_columns")
    allow = raw.get("allow_columns")

    def _as_list(value: object) -> list[str] | None:
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(v) for v in value]
        return None

    options = PhiOptions(
        extra_patterns=_as_list(extra),
        keywords=_as_list(keywords),
        ignore_columns=_as_list(ignore),
        allow_columns=_as_list(allow),
    )
    if not any([
        options.extra_patterns,
        options.keywords,
        options.ignore_columns,
        options.allow_columns,
    ]):
        return None
    return options

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
                       schema_rules: dict[str, object] | None = None,
                       custom_scale_defs: dict[str, ScaleDefinition] | None = None,
                       phi_options: PhiOptions | None = None) -> tuple[pd.DataFrame, dict[str, object], pd.DataFrame | None]:
    df_raw = pd.read_csv(path)
    provenance = {
        "input_path": os.path.abspath(path),
        "input_hash": _file_hash(path),
        "raw_rows": len(df_raw),
        "columns": list(df_raw.columns),
    }
    df = basic_clean(df_raw)
    if not skip_anon and "participant_id" in df.columns:
        try:
            df = anonymize_column(df, "participant_id", out_col="anon_id")
        except RuntimeError as exc:
            raise SystemExit(f"[PRDT] {exc} Set PRDT_ANON_KEY (e.g., export PRDT_ANON_KEY=\"$(openssl rand -hex 32)\").")

    df, phi_flags, phi_quarantine = scan_phi_columns(df, phi_options)
    if phi_flags:
        provenance["phi_columns"] = phi_flags

    scored = []
    if score_scales:
        df, scored = apply_scale_scores(df, score_scales, custom_scale_defs)
        provenance["scales_scored"] = scored

    if schema_rules:
        schema_messages = validate_schema(df, schema_rules)
        if schema_messages:
            provenance["schema_messages"] = schema_messages

    provenance["post_clean_rows"] = len(df)
    return df, provenance, phi_quarantine


def _configure_demo_args(args: argparse.Namespace) -> argparse.Namespace:
    """Seed a temp CSV for a one-command demo and set sensible defaults."""
    tmp_dir = tempfile.mkdtemp(prefix="prdt-demo-")
    demo_csv = os.path.join(tmp_dir, "demo.csv")
    demo_rows = [
        {"participant_id": "demo-001", "date": "2024-01-01", "phq9_total": 5, "gad7_total": 4},
        {"participant_id": "demo-002", "date": "2024-02-01", "phq9_total": 9, "gad7_total": 7},
        {"participant_id": "demo-003", "date": "2024-03-01", "phq9_total": 2, "gad7_total": 3},
    ]
    pd.DataFrame(demo_rows).to_csv(demo_csv, index=False)
    if args.outdir is None:
        stamp = datetime.now(timezone.utc).strftime("demo_%Y%m%dT%H%M%SZ")
        args.outdir = os.path.join("outputs", stamp)
    if getattr(args, "score_cols", None) is None:
        args.score_cols = ["phq9_total", "gad7_total"]
    args.input = demo_csv
    args.skip_anon = True  # avoid key requirement for the bundled demo
    if getattr(args, "allow_phi_export", None) is None:
        args.allow_phi_export = True
    return args

def _guard_against_phi(quarantine: pd.DataFrame | None,
                       phi_flags: list[dict] | None,
                       allow_export: bool) -> None:
    """Abort runs when PHI-like columns are present unless explicitly allowed."""
    if allow_export or quarantine is None or quarantine.empty:
        return
    columns = sorted({str(flag.get("column")) for flag in (phi_flags or []) if flag.get("column")})
    detail = ", ".join(columns) if columns else "PHI columns"
    raise SystemExit(
        "[PRDT] PHI-like columns detected "
        f"({detail}). Run aborted to prevent accidental export. "
        "If these columns are expected/synthetic, rerun with `--allow-phi-export` "
        "or add them under `[prdt.phi.allow_columns]` to keep processing."
    )

def _ensure_outdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _maybe_dry_run(
    args: argparse.Namespace,
    provenance: dict[str, object],
) -> bool:
    """Return True if dry-run is enabled and we should stop after validation."""
    if not getattr(args, "dry_run", False):
        return False
    rows = provenance.get("post_clean_rows") or provenance.get("raw_rows")
    columns = provenance.get("columns") if isinstance(provenance.get("columns"), list) else None
    parts = [
        f"input={provenance.get('input_path')}",
        f"outdir={args.outdir}",
        f"rows={rows}",
    ]
    if columns:
        parts.append(f"columns={len(columns)}")
    scored = provenance.get("scales_scored")
    if scored:
        parts.append(f"scales_scored={len(scored)}")
    sys.stderr.write("[PRDT] Dry run: validation complete. " + "; ".join(parts) + "\n")
    return True


def _write_html_report(outdir: str) -> None:
    path = os.path.join(outdir, "report.json")
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        data = json.load(f)
    alerts = data.get("alerts") or []
    missing = data.get("missing", {})
    cronbach = data.get("cronbach_alpha")
    omega = data.get("mcdonald_omega")
    scale_scores = data.get("scale_scores") or []
    html_lines = [
        "<html><head><title>PRDT Report</title></head><body>",
        "<h1>PRDT Report</h1>",
        "<p><strong>Outputs:</strong> report.json</p>",
        "<h2>Reliability</h2>",
        f"<p>Cronbach's alpha: {cronbach}</p>",
        f"<p>McDonald's omega: {omega}</p>",
        "<h2>Alerts</h2>",
    ]
    if alerts:
        html_lines.append("<ul>")
        for alert in alerts:
            html_lines.append(f"<li>{alert}</li>")
        html_lines.append("</ul>")
    else:
        html_lines.append("<p>No alerts.</p>")
    html_lines.append("<h2>Missingness</h2>")
    html_lines.append(f"<pre>{json.dumps(missing, indent=2)}</pre>")
    if scale_scores:
        html_lines.append("<h2>Scale Scores</h2><ul>")
        for entry in scale_scores:
            html_lines.append(f"<li>{entry}</li>")
        html_lines.append("</ul>")
    html_lines.append("</body></html>")
    with open(os.path.join(outdir, "report.html"), "w") as f:
        f.write("\n".join(html_lines))

def _write_data_dictionary(df: pd.DataFrame, outdir: str) -> None:
    _ensure_outdir(outdir)
    dictionary = build_data_dictionary(df)
    dictionary.to_csv(os.path.join(outdir, "data_dictionary.csv"), index=False)

def _write_phi_quarantine(quarantine: pd.DataFrame | None, outdir: str) -> None:
    path = os.path.join(outdir, "phi_quarantine.csv")
    if quarantine is None or quarantine.empty:
        if os.path.exists(path):
            os.remove(path)
        return
    _ensure_outdir(outdir)
    quarantine.to_csv(path, index=False)

def _format_phi_alerts(records: list[dict] | None) -> list[dict[str, object]]:
    if not records:
        return []
    alerts: list[dict[str, object]] = []
    for entry in records:
        column = entry.get("column")
        matches = entry.get("matches", [])
        alerts.append({
            "type": "phi",
            "column": column,
            "matches": matches,
            "message": f"PHI-like data detected in column '{column}'. Column removed from outputs.",
        })
    return alerts

def _write_clean_csv(df: pd.DataFrame, outdir: str) -> None:
    _ensure_outdir(outdir)
    df.to_csv(os.path.join(outdir, "interim_clean.csv"), index=False)
    _write_data_dictionary(df, outdir)

def _write_report(df: pd.DataFrame, cols: list[str], outdir: str,
                  scales: dict[str, list[str]] | None = None,
                  alerts: dict[str, object] | None = None,
                  extra_alerts: list[dict[str, object]] | None = None,
                  scale_metadata: list[dict[str, object]] | None = None) -> tuple[list[dict[str, object]], list[dict[str, object]] | None]:
    _validate_score_columns(df, cols)
    if scales:
        for name, items in scales.items():
            if not items:
                raise SystemExit(f"[PRDT] Scale '{name}' must include at least one column")
            _validate_score_columns(df, items)
    report = simple_report(df, cols, scales=scales, alerts=alerts, scale_metadata=scale_metadata)
    alert_items = report.get("alerts", []) or []
    if extra_alerts:
        alert_items.extend(extra_alerts)
        report["alerts"] = alert_items
    _ensure_outdir(outdir)
    with open(os.path.join(outdir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    _persist_alerts(outdir, alert_items)
    return alert_items, report.get("scale_scores")

def _write_plots(
    df: pd.DataFrame,
    cols: list[str],
    outdir: str,
    scale_scores: list[dict[str, object]] | None = None,
    scale_metadata: list[dict[str, object]] | None = None,
) -> list[str]:
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
    summary_file = save_scale_summary(scale_scores, outdir) if scale_scores else None
    if summary_file:
        produced.append(summary_file)
    if not scale_scores and scale_metadata:
        computed_scores = _build_scale_scores_from_df(df, scale_metadata)
        summary_file = save_scale_summary(computed_scores, outdir)
        if summary_file:
            produced.append(summary_file)
            scale_scores = computed_scores
    if scale_metadata:
        produced.extend(save_scale_item_bars(df, scale_metadata, outdir))
    return produced

def _run_clean(args: argparse.Namespace) -> None:
    df, provenance, phi_quarantine = _prepare_dataframe(
        args.input,
        args.skip_anon,
        args.score_scales,
        args.schema_rules,
        getattr(args, "custom_scale_definitions", None),
        getattr(args, "phi_options", None),
    )
    _guard_against_phi(phi_quarantine, provenance.get("phi_columns"), args.allow_phi_export or getattr(args, "dry_run", False))
    _ensure_score_cols(args, provenance)
    if _maybe_dry_run(args, provenance):
        return
    _write_clean_csv(df, args.outdir)
    _write_phi_quarantine(phi_quarantine, args.outdir)
    print("[PRDT] saved: interim_clean.csv")
    outputs = ["interim_clean.csv", "data_dictionary.csv"]
    if phi_quarantine is not None and not phi_quarantine.empty:
        outputs.append("phi_quarantine.csv")
    manifest_path, manifest_data = _write_manifest(args.outdir, args, provenance, [], outputs, None)
    drift_alerts = _run_drift_check(args.outdir, manifest_path, manifest_data)
    if drift_alerts:
        _persist_alerts(args.outdir, drift_alerts)

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
        elif alert.get("type") == "phi":
            msg = f"- PHI detected in {alert.get('column')}; column removed."
        else:
            msg = f"- {alert}"
        print(msg)
    if len(alerts) > 5:
        print("  ...")

def _persist_alerts(outdir: str, alerts: list[dict[str, object]]) -> None:
    path = os.path.join(outdir, "alerts.json")
    if alerts:
        _ensure_outdir(outdir)
        with open(path, "w") as f:
            json.dump(alerts, f, indent=2)
    else:
        if os.path.exists(path):
            os.remove(path)

def _previous_manifest(outdir: str, current_manifest: str) -> str | None:
    manifests = sorted(Path(outdir).glob("run_manifest_*.json"), key=os.path.getmtime)
    if not manifests:
        return None
    if len(manifests) == 1:
        return None
    prev = manifests[-2]
    if str(prev) == current_manifest:
        return None
    return str(prev)

def _load_manifest(path: str) -> dict | None:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

DRIFT_DELTA_THRESHOLD = 1.0

def _run_drift_check(outdir: str, manifest_path: str, manifest_data: dict) -> list[dict[str, object]]:
    previous_path = _previous_manifest(outdir, manifest_path)
    if not previous_path:
        return []
    previous = _load_manifest(previous_path)
    if not previous:
        return []

    current_scores = manifest_data.get("scale_scores") or []
    previous_scores = previous.get("scale_scores") or []
    if not current_scores or not previous_scores:
        return []

    prev_lookup = {entry.get("name"): entry for entry in previous_scores if isinstance(entry, dict)}
    drift_records = []
    alerts: list[dict[str, object]] = []
    for entry in current_scores:
        name = entry.get("name")
        if not name or name not in prev_lookup:
            continue
        prev_entry = prev_lookup[name]
        change = (entry.get("mean") or 0) - (prev_entry.get("mean") or 0)
        if abs(change) < DRIFT_DELTA_THRESHOLD:
            continue
        record = {
            "scale": name,
            "previous_mean": prev_entry.get("mean"),
            "current_mean": entry.get("mean"),
            "delta": change,
        }
        drift_records.append(record)
        alerts.append({
            "type": "drift",
            "scale": name,
            "delta": change,
            "message": f"{name} mean changed by {change:.2f} vs last run",
        })

    drift_path = os.path.join(outdir, "drift.json")
    if drift_records:
        with open(drift_path, "w") as f:
            json.dump(drift_records, f, indent=2)
    else:
        if os.path.exists(drift_path):
            os.remove(drift_path)
    return alerts

def _run_stats(args: argparse.Namespace) -> None:
    df, provenance, phi_quarantine = _prepare_dataframe(
        args.input,
        args.skip_anon,
        args.score_scales,
        args.schema_rules,
        getattr(args, "custom_scale_definitions", None),
        getattr(args, "phi_options", None),
    )
    _guard_against_phi(phi_quarantine, provenance.get("phi_columns"), args.allow_phi_export or getattr(args, "dry_run", False))
    _ensure_score_cols(args, provenance)
    if _maybe_dry_run(args, provenance):
        return
    _write_data_dictionary(df, args.outdir)
    phi_alerts = _format_phi_alerts(provenance.get("phi_columns"))
    scale_metadata = provenance.get("scales_scored")
    alerts, scale_scores = _write_report(
        df,
        args.score_cols,
        args.outdir,
        getattr(args, "scales", None),
        getattr(args, "alerts", None),
        extra_alerts=phi_alerts,
        scale_metadata=scale_metadata,
    )
    _maybe_print_alpha(args, df)
    _write_phi_quarantine(phi_quarantine, args.outdir)
    print("[PRDT] saved: report.json")
    outputs = ["report.json", "data_dictionary.csv"]
    if getattr(args, "html_report", False):
        _write_html_report(args.outdir)
        outputs.append("report.html")
    if alerts:
        outputs.append("alerts.json")
    if phi_quarantine is not None and not phi_quarantine.empty:
        outputs.append("phi_quarantine.csv")
    manifest_path, manifest_data = _write_manifest(args.outdir, args, provenance, alerts, outputs, scale_scores)
    drift_alerts = _run_drift_check(args.outdir, manifest_path, manifest_data)
    if drift_alerts:
        alerts.extend(drift_alerts)
        _persist_alerts(args.outdir, alerts)
    _print_alert_summary(alerts)
    _print_alert_summary(alerts)

def _maybe_print_alpha(args: argparse.Namespace, df: pd.DataFrame) -> None:
    if not getattr(args, "alpha", False):
        return
    cols = args.score_cols or []
    if len(cols) < 2:
        print("[PRDT] Cronbach alpha requires at least two --score-cols.")
        return
    value = cronbach_alpha(df, cols)
    if value is None:
        print("[PRDT] Cronbach alpha could not be computed (insufficient data).")
        return
    label = ", ".join(cols)
    print(f"[PRDT] Cronbach alpha ({label}): {value:.3f}")

def _run_plot(args: argparse.Namespace) -> None:
    df, provenance, phi_quarantine = _prepare_dataframe(
        args.input,
        args.skip_anon,
        args.score_scales,
        args.schema_rules,
        getattr(args, "custom_scale_definitions", None),
        getattr(args, "phi_options", None),
    )
    _guard_against_phi(phi_quarantine, provenance.get("phi_columns"), args.allow_phi_export or getattr(args, "dry_run", False))
    _ensure_score_cols(args, provenance)
    if _maybe_dry_run(args, provenance):
        return
    plot_files = _write_plots(
        df,
        args.score_cols,
        args.outdir,
        scale_metadata=provenance.get("scales_scored"),
    )
    _write_phi_quarantine(phi_quarantine, args.outdir)
    print("[PRDT] saved: histogram(s) and trend plot (if feasible)")
    outputs = list(plot_files)
    if phi_quarantine is not None and not phi_quarantine.empty:
        outputs.append("phi_quarantine.csv")
    manifest_path, manifest_data = _write_manifest(args.outdir, args, provenance, [], outputs, None)
    drift_alerts = _run_drift_check(args.outdir, manifest_path, manifest_data)
    if drift_alerts:
        _persist_alerts(args.outdir, drift_alerts)

def _run_full(args: argparse.Namespace) -> None:
    df, provenance, phi_quarantine = _prepare_dataframe(
        args.input,
        args.skip_anon,
        args.score_scales,
        args.schema_rules,
        getattr(args, "custom_scale_definitions", None),
        getattr(args, "phi_options", None),
    )
    _guard_against_phi(phi_quarantine, provenance.get("phi_columns"), args.allow_phi_export or getattr(args, "dry_run", False))
    _ensure_score_cols(args, provenance)
    if _maybe_dry_run(args, provenance):
        return
    _write_clean_csv(df, args.outdir)
    phi_alerts = _format_phi_alerts(provenance.get("phi_columns"))
    scale_metadata = provenance.get("scales_scored")
    alerts, scale_scores = _write_report(
        df,
        args.score_cols,
        args.outdir,
        getattr(args, "scales", None),
        getattr(args, "alerts", None),
        extra_alerts=phi_alerts,
        scale_metadata=scale_metadata,
    )
    plot_files = _write_plots(
        df,
        args.score_cols,
        args.outdir,
        scale_scores=scale_scores,
        scale_metadata=provenance.get("scales_scored"),
    )
    _write_phi_quarantine(phi_quarantine, args.outdir)
    if getattr(args, "html_report", False):
        _write_html_report(args.outdir)
    print("[PRDT] saved: interim_clean.csv, report.json, and plots")
    outputs = ["interim_clean.csv", "data_dictionary.csv", "report.json"]
    if getattr(args, "html_report", False):
        outputs.append("report.html")
    if alerts:
        outputs.append("alerts.json")
    outputs.extend(plot_files)
    if phi_quarantine is not None and not phi_quarantine.empty:
        outputs.append("phi_quarantine.csv")
    manifest_path, manifest_data = _write_manifest(args.outdir, args, provenance, alerts, outputs, scale_scores)
    drift_alerts = _run_drift_check(args.outdir, manifest_path, manifest_data)
    if drift_alerts:
        alerts.extend(drift_alerts)
        _persist_alerts(args.outdir, alerts)

def _run_demo(args: argparse.Namespace) -> None:
    print("[PRDT] Running demo with bundled sample data...")
    _run_full(args)
    print(f"[PRDT] Demo complete. Outputs written to: {args.outdir}")


def _run_doctor(args: argparse.Namespace) -> None:
    """Environment sanity checks for PRDT."""
    checks: list[tuple[str, bool, str]] = []
    py_ok = sys.version_info >= (3, 9)
    checks.append(("python>=3.9", py_ok, platform.python_version()))

    def _import_version(mod: str) -> tuple[bool, str]:
        try:
            module = __import__(mod)
            version = getattr(module, "__version__", "unknown")
            return True, str(version)
        except Exception as exc:  # pragma: no cover - defensive
            return False, str(exc)

    for mod in ("pandas", "numpy", "matplotlib"):
        ok, note = _import_version(mod)
        checks.append((mod, ok, note))

    anon_key = os.getenv("PRDT_ANON_KEY")
    key_ok = bool(anon_key) and len(str(anon_key)) >= 32
    checks.append(("PRDT_ANON_KEY set (>=32 chars)", key_ok, "set" if anon_key else "missing"))

    if args.input:
        exists = os.path.exists(args.input)
        checks.append(("input path exists", exists, args.input or ""))
    passed = all(flag for _, flag, _ in checks)
    for name, ok, note in checks:
        status = "OK" if ok else "FAIL"
        print(f"[PRDT][{status}] {name} ({note})")
    if not passed:
        sys.exit("[PRDT] Doctor checks failed. See items marked FAIL.")
    print("[PRDT] Doctor checks passed.")

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
    allow_phi_export = data.get("allow_phi_export")
    if isinstance(allow_phi_export, str):
        allow_phi_export = allow_phi_export.lower() in {"1", "true", "yes"}
    if isinstance(allow_phi_export, bool):
        data["allow_phi_export"] = allow_phi_export
    else:
        data.pop("allow_phi_export", None)

    normalized_scales = _normalize_scales(data.get("scales"))
    if normalized_scales:
        data["scales"] = normalized_scales
    else:
        data.pop("scales", None)

    score_entry = data.get("score")
    custom_scale_defs = {}
    if isinstance(score_entry, dict) and "definitions" in score_entry:
        custom_scale_defs = _normalize_custom_scales(score_entry.get("definitions"))
        data["custom_scale_definitions"] = custom_scale_defs
    score_list = _normalize_score_request(score_entry)
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

    phi_opts = _normalize_phi_options(data.get("phi"))
    if phi_opts:
        data["phi_options"] = phi_opts
    else:
        data.pop("phi_options", None)

    return data, config_meta

def _merge_config(args: argparse.Namespace, config: dict[str, object], allow_command_override: bool) -> argparse.Namespace:
    if not config:
        return args
    if allow_command_override and isinstance(config.get("command"), str):
        args.command = config["command"]  # type: ignore[assignment]
    for key in ("input", "outdir", "score_cols", "skip_anon", "allow_phi_export"):
        if getattr(args, key, None) is None and config.get(key) is not None:
            setattr(args, key, config[key])
    if config.get("scales") is not None:
        setattr(args, "scales", config["scales"])
    if config.get("alerts") is not None:
        setattr(args, "alerts", config["alerts"])
    if config.get("score") is not None:
        setattr(args, "score_scales", config["score"])
    if config.get("custom_scale_definitions") is not None:
        setattr(args, "custom_scale_definitions", config["custom_scale_definitions"])
    if config.get("schema") is not None:
        setattr(args, "schema_rules", config["schema"])
    if config.get("phi_options") is not None:
        setattr(args, "phi_options", config["phi_options"])
    return args

def _finalize_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> argparse.Namespace:
    if not hasattr(args, "score_cols"):
        args.score_cols = None
    if not hasattr(args, "input"):
        args.input = None
    if not hasattr(args, "outdir"):
        args.outdir = None
    if not hasattr(args, "scales"):
        args.scales = None
    if not hasattr(args, "alerts"):
        args.alerts = None
    if not hasattr(args, "score_scales"):
        args.score_scales = None
    if not hasattr(args, "custom_scale_definitions"):
        args.custom_scale_definitions = None
    if not hasattr(args, "schema_rules"):
        args.schema_rules = None
    if not hasattr(args, "phi_options"):
        args.phi_options = None
    if not hasattr(args, "allow_phi_export") or args.allow_phi_export is None:
        args.allow_phi_export = False
    if args.score_cols is None:
        args.score_cols = ["phq9_total", "gad7_total"]
    if args.command == "doctor":
        args.score_cols = getattr(args, "score_cols", []) or []
        args.alerts = getattr(args, "alerts", None)
        return args
    if args.outdir is None:
        stamp = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
        args.outdir = os.path.join("outputs", stamp)
        sys.stderr.write(f"[PRDT] No --outdir provided; using '{args.outdir}'.\n")
    if args.input is None:
        parser.error("Missing --input. Provide a CSV path or use --config <profile.toml>.")
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
    common.add_argument(
        "--allow-phi-export",
        action="store_true",
        default=None,
        help="Proceed even when PHI-like columns are detected (default aborts).",
    )
    common.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs/config and stop before writing outputs.",
    )
    common.add_argument(
        "--html-report",
        action="store_true",
        help="Also write report.html (plain-language summary) alongside report.json.",
    )

    parser = argparse.ArgumentParser(description="PRDT CLI")
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    sub.add_parser("clean", parents=[common], help="Clean + anonymize CSV and write interim_clean.csv")
    stats_parser = sub.add_parser("stats", parents=[common], help="Generate report.json (descriptives, corr., alpha, missing)")
    stats_parser.add_argument(
        "--alpha",
        action="store_true",
        help="Print Cronbach's α for --score-cols after computing stats.",
    )
    sub.add_parser("plot", parents=[common], help="Create histogram/time-trend plots")
    sub.add_parser("run", parents=[common], help="Run the full pipeline (clean + stats + plot)")
    demo = sub.add_parser("demo", help="Run PRDT against bundled sample data (no config needed)")
    demo.add_argument("--outdir", help="Directory for outputs (defaults to outputs/demo_<timestamp>)")
    sub.add_parser("doctor", help="Run environment checks (Python, deps, key, input path)")
    return parser

def main(argv: list[str] | None = None):
    parser = _build_parser()
    raw_args = list(sys.argv[1:] if argv is None else argv)
    config_path, cleaned = _split_config_args(raw_args)
    insert_default_command = not cleaned or cleaned[0].startswith("-")
    if insert_default_command:
        cleaned = ["run"] + cleaned
    args = parser.parse_args(cleaned)
    if args.command == "demo":
        config, config_meta = {}, {"path": None, "hash": None}
        args = _configure_demo_args(args)
    else:
        config, config_meta = _load_config(config_path)
        args = _merge_config(args, config, allow_command_override=insert_default_command)
    args = _finalize_args(args, parser)
    args._config_path = config_meta.get("path")
    args._config_hash = config_meta.get("hash")
    _log_config_summary(args)
    command = args.command
    actions = {
        "clean": _run_clean,
        "stats": _run_stats,
        "plot": _run_plot,
        "run": _run_full,
        "demo": _run_demo,
        "doctor": _run_doctor,
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
                    alerts: list[dict[str, object]], outputs: list[str],
                    scale_scores: list[dict[str, object]] | None = None) -> tuple[str, dict]:
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
        "phi_flags": provenance.get("phi_columns"),
        "alerts_count": len(alerts),
        "outputs": sorted(set(outputs)),
        "scale_scores": scale_scores,
        "python_version": sys.version,
    }
    _ensure_outdir(outdir)
    latest_path = os.path.join(outdir, "run_manifest.json")
    with open(latest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    versioned_path = os.path.join(outdir, f"run_manifest_{stamp}.json")
    with open(versioned_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return versioned_path, manifest

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


def _log_config_summary(args: argparse.Namespace) -> None:
    """Print a short summary of parsed config args for quick sanity-checks."""
    cfg = getattr(args, "_config_path", None)
    if not cfg:
        return
    parts = [
        f"config={cfg}",
        f"input={args.input}",
        f"outdir={args.outdir}",
    ]
    if args.score_cols:
        parts.append(f"score_cols={args.score_cols}")
    alerts = getattr(args, "alerts", None)
    if alerts:
        parts.append(f"alerts={alerts}")
    sys.stderr.write("[PRDT] Config summary: " + "; ".join(parts) + "\n")

if __name__ == "__main__":
    main()
