from __future__ import annotations
import argparse, os, json
import pandas as pd
from .cleaning import basic_clean
from .anonymize import anonymize_column
from .stats import simple_report
from .plots import save_histograms, save_trend

def main():
    p = argparse.ArgumentParser(description="PRDT CLI")
    p.add_argument("--input", required=True, help="Path to input CSV")
    p.add_argument("--outdir", required=True, help="Directory for outputs")
    p.add_argument("--score-cols", nargs="*", default=["phq9_total","gad7_total"],
                   help="Numeric score columns for descriptives/correlation/plots")
    args = p.parse_args()

    # load + clean
    df = pd.read_csv(args.input)
    df = basic_clean(df)

    # anonymize if we have a participant_id column
    if "participant_id" in df.columns:
        df = anonymize_column(df, "participant_id", out_col="anon_id")

    # outputs: cleaned CSV
    os.makedirs(args.outdir, exist_ok=True)
    df.to_csv(os.path.join(args.outdir, "interim_clean.csv"), index=False)

    # stats JSON
    report = simple_report(df, args.score_cols)
    with open(os.path.join(args.outdir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    # plots
    save_histograms(df, args.score_cols, args.outdir)

    # simple time trend for the first score column, if date + id present
    if args.score_cols:
        value_col = args.score_cols[0]
        time_col = "date" if "date" in df.columns else None
        id_col = "anon_id" if "anon_id" in df.columns else ("participant_id" if "participant_id" in df.columns else None)
        if time_col and id_col:
            save_trend(df, id_col, time_col, value_col, args.outdir)

    print("[PRDT] saved: interim_clean.csv, report.json, and plots")

if __name__ == "__main__":
    main()