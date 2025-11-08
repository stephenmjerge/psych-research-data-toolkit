from __future__ import annotations
import pandas as pd
import numpy as np

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

def mcdonald_omega(df: pd.DataFrame, cols: list[str]) -> float | None:
    """Approximate McDonald's omega using first principal component loadings."""
    if len(cols) < 2:
        return None

    items = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if items.empty or len(items) < 2:
        return None

    cov = np.cov(items.T, ddof=1)
    if not np.all(np.isfinite(cov)):
        return None

    try:
        eigvals, eigvecs = np.linalg.eigh(cov)
    except np.linalg.LinAlgError:
        return None

    idx = np.argsort(eigvals)[::-1]
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]
    leading_val = eigvals[0]
    if leading_val <= 0:
        return None

    loadings = np.sqrt(leading_val) * eigvecs[:, 0]
    specific_vars = np.diag(cov) - loadings**2
    specific_vars = np.clip(specific_vars, 0, None)
    numerator = np.sum(loadings) ** 2
    denominator = numerator + np.sum(specific_vars)
    if denominator == 0:
        return None
    return float(numerator / denominator)

def item_total_correlations(df: pd.DataFrame, cols: list[str]) -> dict[str, float] | None:
    if len(cols) < 2:
        return None
    items = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if items.empty or len(items) < 2:
        return None
    total = items.sum(axis=1)
    correlations: dict[str, float] = {}
    for col in cols:
        series = items[col]
        rest = total - series
        if series.var(ddof=1) == 0 or rest.var(ddof=1) == 0:
            correlations[col] = float("nan")
            continue
        correlations[col] = float(series.corr(rest))
    return correlations

def alpha_if_item_dropped(df: pd.DataFrame, cols: list[str]) -> dict[str, float] | None:
    if len(cols) < 3:
        return None
    stats: dict[str, float] = {}
    for col in cols:
        remaining = [c for c in cols if c != col]
        stats[col] = cronbach_alpha(df, remaining) or float("nan")
    return stats

def scale_reliability_summary(df: pd.DataFrame, scales: dict[str, list[str]]) -> dict[str, dict[str, object]]:
    summary: dict[str, dict[str, object]] = {}
    for name, items in scales.items():
        items_list = [str(col) for col in items if str(col).strip()]
        alpha = cronbach_alpha(df, items_list) if len(items_list) >= 2 else None
        omega = mcdonald_omega(df, items_list) if len(items_list) >= 2 else None
        item_corr = item_total_correlations(df, items_list)
        alpha_drop = alpha_if_item_dropped(df, items_list)
        summary[name] = {
            "items": items_list,
            "cronbach_alpha": alpha,
            "mcdonald_omega": omega,
            "item_total_correlations": item_corr,
            "alpha_if_item_dropped": alpha_drop,
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

def _missing_alerts(missing: dict, threshold: float) -> list[dict[str, object]]:
    alerts = []
    percents = missing.get("percent", {})
    for col, pct in percents.items():
        try:
            value = float(pct)
        except (TypeError, ValueError):
            continue
        if value >= threshold:
            alerts.append({
                "type": "missingness",
                "column": col,
                "percent": value,
                "threshold": threshold,
            })
    return alerts

def _reliability_alerts(overall: dict[str, float | None],
                        scales: dict[str, dict[str, object]] | None,
                        thresholds: dict[str, float]) -> list[dict[str, object]]:
    alerts: list[dict[str, object]] = []
    alpha_min = thresholds.get("cronbach_alpha_min")
    omega_min = thresholds.get("mcdonald_omega_min")

    def maybe_add(label: str, dtype: str, value: float | None, limit: float | None):
        if limit is None or value is None:
            return
        if value < limit:
            alerts.append({
                "type": "reliability",
                "target": label,
                "metric": dtype,
                "value": value,
                "threshold": limit,
            })

    maybe_add("overall", "cronbach_alpha", overall.get("cronbach_alpha"), alpha_min)
    maybe_add("overall", "mcdonald_omega", overall.get("mcdonald_omega"), omega_min)

    if scales:
        for name, metrics in scales.items():
            maybe_add(name, "cronbach_alpha", metrics.get("cronbach_alpha"), alpha_min)
            maybe_add(name, "mcdonald_omega", metrics.get("mcdonald_omega"), omega_min)

    return alerts

def _interpret_cutoffs(score: float | None, cutoffs: dict[str, str] | None) -> str | None:
    if score is None or cutoffs is None:
        return None
    parsed: list[tuple[str, float | None, float | None]] = []
    for label, value in cutoffs.items():
        text = str(value)
        if "+" in text:
            low = text.replace("+", "").strip()
            try:
                parsed.append((label, float(low), None))
            except ValueError:
                continue
        elif "-" in text:
            parts = text.split("-", 1)
            try:
                parsed.append((label, float(parts[0]), float(parts[1])))
            except ValueError:
                continue
        else:
            try:
                val = float(text)
                parsed.append((label, val, val))
            except ValueError:
                continue
    for label, low, high in parsed:
        if low is not None and score < low:
            continue
        if high is not None and score > high:
            continue
        return label
    return None

def simple_report(
    df: pd.DataFrame,
    cols: list[str],
    scales: dict[str, list[str]] | None = None,
    alerts: dict[str, object] | None = None,
    scale_metadata: list[dict[str, object]] | None = None,
) -> dict:
    desc = describe_columns(df, cols).reset_index().rename(columns={"index":"variable"})
    corr = pearson_corr(df, cols)
    alpha = cronbach_alpha(df, cols)
    omega = mcdonald_omega(df, cols)
    report = {
        "descriptives": desc.to_dict(orient="records"),
        "pearson_corr": corr.to_dict(),
        "cronbach_alpha": alpha,
        "mcdonald_omega": omega,
        "missing": missing_summary(df),
    }
    scale_block = None
    scale_scores: list[dict[str, object]] = []
    metadata_map = {meta.get("name"): meta for meta in (scale_metadata or []) if isinstance(meta, dict)}
    if scales:
        scale_block = scale_reliability_summary(df, scales)
        for name, meta in metadata_map.items():
            if name in scale_block:
                scale_block[name]["cutoffs"] = meta.get("cutoffs")
        report["scale_reliability"] = scale_block

        for name, meta in metadata_map.items():
            out_col = meta.get("output_column")
            if not out_col or out_col not in df.columns:
                continue
            series = pd.to_numeric(df[out_col], errors="coerce")
            if series.dropna().empty:
                continue
            mean_val = float(series.mean())
            std_val = float(series.std()) if len(series) > 1 else 0.0
            interpretation = _interpret_cutoffs(mean_val, meta.get("cutoffs"))
            scale_scores.append({
                "name": name,
                "score_column": out_col,
                "mean": mean_val,
                "std": std_val,
                "min": float(series.min()),
                "max": float(series.max()),
                "interpretation": interpretation,
            })
        if scale_scores:
            report["scale_scores"] = scale_scores

    alert_items: list[dict[str, object]] = []
    if alerts:
        missing_threshold = alerts.get("missing_pct")
        if isinstance(missing_threshold, (int, float)):
            alert_items.extend(_missing_alerts(report["missing"], float(missing_threshold)))

        reliability_thresholds = alerts.get("reliability")
        if isinstance(reliability_thresholds, dict):
            alert_items.extend(
                _reliability_alerts(
                    {"cronbach_alpha": alpha, "mcdonald_omega": omega},
                    scale_block,
                    reliability_thresholds,
                )
            )
    report["alerts"] = alert_items
    return report
