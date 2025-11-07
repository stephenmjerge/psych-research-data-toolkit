from __future__ import annotations
import pandas as pd

def describe_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    return sub.describe().T

def pearson_corr(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    return sub.corr(method="pearson")

def missing_summary(df: pd.DataFrame) -> dict:
    """Return count/percent missing for every column plus a row-wise detail list."""
    counts = df.isna().sum()
    total = len(df)
    if total:
        percents = (counts / total * 100).round(2)
    else:
        percents = counts.astype(float)

    detail = [
        {
            "variable": col,
            "missing": int(counts[col]),
            "missing_pct": float(percents[col]) if total else 0.0,
        }
        for col in df.columns
    ]

    return {
        "count": counts.astype(int).to_dict(),
        "percent": percents.astype(float).to_dict(),
        "detail": detail,
    }

def simple_report(df: pd.DataFrame, cols: list[str]) -> dict:
    desc = describe_columns(df, cols).reset_index().rename(columns={"index":"variable"})
    corr = pearson_corr(df, cols)
    return {
        "descriptives": desc.to_dict(orient="records"),
        "pearson_corr": corr.to_dict(),
        "missing": missing_summary(df)
    }
