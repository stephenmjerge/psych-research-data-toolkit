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

def save_trend(df: pd.DataFrame, id_col: str, time_col: str, value_col: str, outdir: str) -> None:
    """Plot a simple time trend for each participant on one chart."""
    needed = [id_col, time_col, value_col]
    if not all(col in df.columns for col in needed):
        return

    os.makedirs(outdir, exist_ok=True)
    tmp = df[needed].dropna().copy()
    if tmp.empty:
        return

    # robust datetime handling
    tmp[time_col] = pd.to_datetime(tmp[time_col], errors="coerce")
    tmp = tmp.dropna(subset=[time_col]).sort_values([id_col, time_col])
    if tmp.empty:
        return

    plt.figure()
    for pid, grp in tmp.groupby(id_col):
        plt.plot(grp[time_col], grp[value_col], marker="o")
    plt.title(f"Trend: {value_col} by {id_col}")
    plt.xlabel(time_col)
    plt.ylabel(value_col)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"trend_{value_col}.png"))
    plt.close()