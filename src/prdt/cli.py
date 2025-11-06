from __future__ import annotations
import argparse, os, json
import pandas as pd
from .cleaning import basic_clean
from .anonymize import anonymize_column
from .stats import simple_report

def main():
    p = argparse.ArgumentParser(description="PRDT CLI")
    p.add_argument("--input", required=True, help="Path to input CSV")
    p.add_argument("--outdir", required=True, help="Directory for outputs")
    p.add_argument("--score-cols", nargs="*", default=["phq9_total","gad7_total"])
    args = p.parse_args()

    df = pd.read_csv(args.input)
    df = basic_clean(df)

    if "participant_id" in df.columns:
        df = anonymize_column(df, "participant_id", out_col="anon_id")

    os.makedirs(args.outdir, exist_ok=True)
    df.to_csv(os.path.join(args.outdir, "interim_clean.csv"), index=False)

    report = simple_report(df, args.score_cols)
    with open(os.path.join(args.outdir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print("[PRDT] saved: interim_clean.csv and report.json")

if __name__ == "__main__":
    main()
