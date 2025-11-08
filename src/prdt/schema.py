from __future__ import annotations
from typing import Any
import pandas as pd

def normalize_schema(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    schema: dict[str, Any] = {}
    required = raw.get("required")
    if isinstance(required, list):
        schema["required"] = [str(r) for r in required]
    types = raw.get("types")
    if isinstance(types, dict):
        schema["types"] = {str(k): str(v).lower() for k, v in types.items()}
    return schema

def validate_schema(df: pd.DataFrame, schema: dict[str, Any]) -> list[str]:
    """Return list of human-readable warnings/errors."""
    messages: list[str] = []
    required = schema.get("required") or []
    for col in required:
        if col not in df.columns:
            messages.append(f"Missing required column: {col}")
    types = schema.get("types") or {}
    for col, expected in types.items():
        if col not in df.columns:
            messages.append(f"Column '{col}' missing (expected type {expected})")
            continue
        series = df[col]
        if expected == "numeric":
            coerced = pd.to_numeric(series, errors="coerce")
            if coerced.isna().all() and not series.isna().all():
                messages.append(f"Column '{col}' cannot be coerced to numeric values.")
        elif expected == "date":
            coerced = pd.to_datetime(series, errors="coerce")
            if coerced.isna().all() and not series.isna().all():
                messages.append(f"Column '{col}' cannot be parsed as dates.")
    return messages

def build_data_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    info = []
    total = len(df)
    for col in df.columns:
        series = df[col]
        non_null = series.notna().sum()
        missing_pct = round((1 - non_null / total) * 100, 2) if total else 0.0
        example = series.dropna().iloc[0] if non_null else ""
        info.append({
            "column": col,
            "dtype": str(series.dtype),
            "non_null": int(non_null),
            "missing_pct": missing_pct,
            "example": example,
        })
    return pd.DataFrame(info)
