from __future__ import annotations
import argparse, os
import pandas as pd
from .cleaning import basic_clean
from .anonymize import anonymize_column

def main():
    p = argparse.ArgumentParser(description="PRDT CLI")
    p.add_argument("--input", required=True, help="Path to input CSV")
    p.add_argument("--outdir", required=True, help="Directory for outputs")
    args = p.parse_args()

    df = pd.read_csv(args.input)
    df = basic_clean(df)

    if "participant_id" in df.columns:
        df = anonymize_column(df, "participant_id", out_col="anon_id")

    os.makedirs(args.outdir, exist_ok=True)
    df.to_csv(os.path.join(args.outdir, "interim_clean.csv"), index=False)
    print("[PRDT] cleaned + anonymized CSV saved to outputs")

if __name__ == "__main__":
    main()
