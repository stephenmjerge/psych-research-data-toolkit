from __future__ import annotations
import os
from typing import Any
import pandas as pd
import numpy as np

def _plots_disabled() -> bool:
    flag = os.environ.get("PRDT_DISABLE_PLOTS", "")
    return flag.lower() in {"1", "true", "yes", "on"}

if not _plots_disabled():
    import matplotlib.pyplot as plt
    plt.style.use("seaborn-v0_8")
else:
    plt = None  # type: ignore[assignment]

PALETTE = ["#4477AA", "#66CCEE", "#228833", "#CCBB44", "#EE6677", "#AA3377", "#BBBBBB"]

def save_histograms(df: pd.DataFrame, cols: list[str], outdir: str) -> list[str]:
    if _plots_disabled() or plt is None:
        return []
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
    if _plots_disabled() or plt is None:
        return None
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
    if _plots_disabled() or plt is None:
        return None
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

def _build_scale_scores_from_df(df: pd.DataFrame, metadata: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not metadata:
        return []
    results = []
    for meta in metadata:
        if not isinstance(meta, dict):
            continue
        out_col = meta.get("output_column")
        if not out_col or out_col not in df.columns:
            continue
        series = pd.to_numeric(df[out_col], errors="coerce")
        series = series.dropna()
        if series.empty:
            continue
        results.append({
            "name": meta.get("name"),
            "score_column": out_col,
            "mean": float(series.mean()),
            "std": float(series.std()) if len(series) > 1 else 0.0,
            "min": float(series.min()),
            "max": float(series.max()),
            "interpretation": None,
        })
    return results

def save_scale_summary(scale_scores: list[dict[str, Any]] | None, outdir: str) -> str | None:
    if _plots_disabled() or plt is None:
        return None
    if not scale_scores:
        return None
    valid = [entry for entry in scale_scores if isinstance(entry, dict) and entry.get("mean") is not None]
    if not valid:
        return None

    data = sorted(valid, key=lambda x: x.get("mean", 0), reverse=True)
    names = [entry.get("name", "scale") for entry in data]
    means = [entry.get("mean", 0) for entry in data]
    annotations = [entry.get("interpretation") or "" for entry in data]

    os.makedirs(outdir, exist_ok=True)
    plt.figure(figsize=(8, max(3, len(names) * 0.6)))
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(names))]
    bars = plt.barh(names, means, color=colors)
    for bar, text in zip(bars, annotations):
        if text:
            plt.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2, text, va="center")
    plt.xlabel("Mean score")
    plt.title("Scale Summary")
    plt.tight_layout()
    filename = "scale_summary.png"
    plt.savefig(os.path.join(outdir, filename))
    plt.close()
    return filename

def save_scale_item_bars(df: pd.DataFrame, metadata: list[dict[str, Any]] | None, outdir: str, limit: int = 4) -> list[str]:
    if _plots_disabled() or plt is None:
        return []
    if not metadata:
        return []
    os.makedirs(outdir, exist_ok=True)
    files: list[str] = []
    for meta in metadata[:limit]:
        items = meta.get("items")
        name = meta.get("name")
        if not items or not name:
            continue
        sub = df[items].apply(pd.to_numeric, errors="coerce")
        means = sub.mean().dropna()
        if means.empty:
            continue
        plt.figure(figsize=(max(6, len(means) * 0.5), 4))
        colors = [PALETTE[i % len(PALETTE)] for i in range(len(means))]
        plt.bar(range(len(means)), means.values, color=colors)
        plt.xticks(range(len(means)), means.index, rotation=45, ha="right")
        plt.ylabel("Mean")
        plt.title(f"Item Means: {name.upper()}")
        plt.tight_layout()
        filename = f"scale_items_{name}.png"
        plt.savefig(os.path.join(outdir, filename))
        plt.close()
        files.append(filename)
    return files
