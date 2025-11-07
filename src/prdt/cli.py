from __future__ import annotations
import argparse, os, json, sys
import pandas as pd
from .cleaning import basic_clean
from .anonymize import anonymize_column
from .stats import simple_report
from .plots import save_histograms, save_trend

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

def _prepare_dataframe(path: str, skip_anon: bool) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = basic_clean(df)
    if not skip_anon and "participant_id" in df.columns:
        df = anonymize_column(df, "participant_id", out_col="anon_id")
    return df

def _ensure_outdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _write_clean_csv(df: pd.DataFrame, outdir: str) -> None:
    _ensure_outdir(outdir)
    df.to_csv(os.path.join(outdir, "interim_clean.csv"), index=False)

def _write_report(df: pd.DataFrame, cols: list[str], outdir: str) -> None:
    _validate_score_columns(df, cols)
    report = simple_report(df, cols)
    _ensure_outdir(outdir)
    with open(os.path.join(outdir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

def _write_plots(df: pd.DataFrame, cols: list[str], outdir: str) -> None:
    _validate_score_columns(df, cols)
    _ensure_outdir(outdir)
    save_histograms(df, cols, outdir)
    value_col = cols[0]
    time_col = "date" if "date" in df.columns else None
    id_col = "anon_id" if "anon_id" in df.columns else ("participant_id" if "participant_id" in df.columns else None)
    if time_col and id_col:
        save_trend(df, id_col, time_col, value_col, outdir)

def _run_clean(args: argparse.Namespace) -> None:
    df = _prepare_dataframe(args.input, args.skip_anon)
    _write_clean_csv(df, args.outdir)
    print("[PRDT] saved: interim_clean.csv")

def _run_stats(args: argparse.Namespace) -> None:
    df = _prepare_dataframe(args.input, args.skip_anon)
    _write_report(df, args.score_cols, args.outdir)
    print("[PRDT] saved: report.json")

def _run_plot(args: argparse.Namespace) -> None:
    df = _prepare_dataframe(args.input, args.skip_anon)
    _write_plots(df, args.score_cols, args.outdir)
    print("[PRDT] saved: histogram(s) and trend plot (if feasible)")

def _run_full(args: argparse.Namespace) -> None:
    df = _prepare_dataframe(args.input, args.skip_anon)
    _write_clean_csv(df, args.outdir)
    _write_report(df, args.score_cols, args.outdir)
    _write_plots(df, args.score_cols, args.outdir)
    print("[PRDT] saved: interim_clean.csv, report.json, and plots")

def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--input", required=True, help="Path to input CSV")
    common.add_argument("--outdir", required=True, help="Directory for outputs")
    common.add_argument(
        "--score-cols",
        nargs="*",
        default=["phq9_total", "gad7_total"],
        help="Numeric score columns for descriptives/correlation/plots",
    )
    common.add_argument(
        "--skip-anon",
        action="store_true",
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
    if not raw_args or raw_args[0].startswith("-"):
        raw_args = ["run"] + raw_args
    args = parser.parse_args(raw_args)
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

if __name__ == "__main__":
    main()
