from __future__ import annotations
import os
import pandas as pd
import matplotlib.pyplot as plt

def save_histograms(df: pd.DataFrame, cols: list[str], outdir: str) -> list[str]:
    os.makedirs(outdir, exist_ok=True)
    files: list[str] = []
    for c in cols:
        if c in df.columns:
            series = pd.to_numeric(df[c], errors="coerce").dropna()
            if series.empty:
                continue
            plt.figure()
            series.plot(kind="hist", bins=20, title=f"Distribution: {c}")
            plt.xlabel(c)
            plt.ylabel("Count")
            plt.tight_layout()
            filename = f"hist_{c}.png"
            plt.savefig(os.path.join(outdir, filename))
            plt.close()
            files.append(filename)
    return files

def save_trend(df: pd.DataFrame, id_col: str, time_col: str, value_col: str, outdir: str) -> str | None:
    """Plot a simple time trend for each participant on one chart."""
    needed = [id_col, time_col, value_col]
    if not all(col in df.columns for col in needed):
        return None

    os.makedirs(outdir, exist_ok=True)
    tmp = df[needed].dropna().copy()
    if tmp.empty:
        return None

    # robust datetime handling
    tmp[time_col] = pd.to_datetime(tmp[time_col], errors="coerce")
    tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce")
    tmp = tmp.dropna(subset=[time_col, value_col]).sort_values([id_col, time_col])
    if tmp.empty:
        return None

    plt.figure()
    for pid, grp in tmp.groupby(id_col):
        plt.plot(grp[time_col], grp[value_col], marker="o")
    plt.title(f"Trend: {value_col} by {id_col}")
    plt.xlabel(time_col)
    plt.ylabel(value_col)
    plt.tight_layout()
    filename = f"trend_{value_col}.png"
    plt.savefig(os.path.join(outdir, filename))
    plt.close()
    return filename

def save_missingness_bar(df: pd.DataFrame, outdir: str) -> str | None:
    """Render a bar chart of percent missing per column."""
    miss = df.isna().mean().sort_values(ascending=False) * 100
    miss = miss[miss > 0]
    if miss.empty:
        return None

    os.makedirs(outdir, exist_ok=True)
    plt.figure(figsize=(max(6, len(miss) * 0.8), 4))
    miss.plot(kind="bar", color="#c44e52")
    plt.ylabel("Percent Missing")
    plt.ylim(0, min(100, miss.max() + 5))
    plt.title("Missingness by Column")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    filename = "missingness.png"
    plt.savefig(os.path.join(outdir, filename))
    plt.close()
    return filename
