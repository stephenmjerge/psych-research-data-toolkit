from __future__ import annotations
import pandas as pd

def describe_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    return sub.describe().T

def pearson_corr(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    return sub.corr(method="pearson")

def cronbach_alpha(df: pd.DataFrame, cols: list[str]) -> float | None:
    """Compute Cronbach's alpha for provided columns; return None if not enough data."""
    if len(cols) < 2:
        return None

    items = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if items.empty or len(items) < 2:
        return None

    item_vars = items.var(axis=0, ddof=1)
    total_var = items.sum(axis=1).var(ddof=1)
    if total_var == 0 or item_vars.isna().any():
        return None

    k = len(cols)
    alpha = (k / (k - 1)) * (1 - item_vars.sum() / total_var)
    return float(alpha)

def scale_alpha_summary(df: pd.DataFrame, scales: dict[str, list[str]]) -> dict[str, dict[str, object]]:
    summary: dict[str, dict[str, object]] = {}
    for name, items in scales.items():
        items_list = [str(col) for col in items if str(col).strip()]
        alpha = cronbach_alpha(df, items_list) if len(items_list) >= 2 else None
        summary[name] = {
            "items": items_list,
            "cronbach_alpha": alpha,
        }
    return summary

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

def simple_report(df: pd.DataFrame, cols: list[str], scales: dict[str, list[str]] | None = None) -> dict:
    desc = describe_columns(df, cols).reset_index().rename(columns={"index":"variable"})
    corr = pearson_corr(df, cols)
    alpha = cronbach_alpha(df, cols)
    report = {
        "descriptives": desc.to_dict(orient="records"),
        "pearson_corr": corr.to_dict(),
        "cronbach_alpha": alpha,
        "missing": missing_summary(df),
    }
    if scales:
        report["scale_alphas"] = scale_alpha_summary(df, scales)
    return report
