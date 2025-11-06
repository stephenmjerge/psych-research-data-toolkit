from __future__ import annotations
import os
import pandas as pd
import matplotlib.pyplot as plt

def save_histograms(df: pd.DataFrame, cols: list[str], outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    for c in cols:
        if c in df.columns:
            plt.figure()
            df[c].dropna().astype(float).plot(kind="hist", bins=20, title=f"Distribution: {c}")
            plt.xlabel(c)
            plt.ylabel("Count")
            plt.tight_layout()
            plt.savefig(os.path.join(outdir, f"hist_{c}.png"))
            plt.close()
