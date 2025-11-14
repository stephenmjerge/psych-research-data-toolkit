from __future__ import annotations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = REPO_ROOT / "data" / "examples" / "dataset_a_sample.csv"
OUTDIR = Path(__file__).resolve().parent
OUTDIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)
summary = {}
for col in ["phq9_total", "gad7_total", "pcl5_total"]:
    summary[col] = {
        "mean": float(df[col].mean()),
        "std": float(df[col].std(ddof=0)),
        "min": float(df[col].min()),
        "max": float(df[col].max()),
    }
missing = (df.isna().mean() * 100).round(2).to_dict()
summary["missing_pct"] = missing

(OUTDIR / "descriptives.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

plt.figure(figsize=(4,3))
df["phq9_total"].plot(kind="hist", bins=range(0,30,2), color="#4CAF50", edgecolor="black")
plt.title("PHQ-9 Total (Dataset A demo)")
plt.xlabel("Score")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig(OUTDIR / "hist_phq9_total.png", dpi=150)
plt.close()

plt.figure(figsize=(4,3))
missing_series = df.isna().mean().sort_values(ascending=False)[:5] * 100
missing_series.plot(kind="bar", color="#607d8b")
plt.ylabel("Missing (%)")
plt.title("Top missing fields")
plt.tight_layout()
plt.savefig(OUTDIR / "missingness.png", dpi=150)
plt.close()

print("Wrote demo outputs to", OUTDIR)
