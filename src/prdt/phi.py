from __future__ import annotations
import re
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class PhiPattern:
    name: str
    regex: str

PHI_PATTERNS: list[PhiPattern] = [
    PhiPattern("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    PhiPattern("phone", r"\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    PhiPattern("ssn", r"\b\d{3}-\d{2}-\d{4}\b"),
    PhiPattern("mrn", r"\bMRN\d+\b"),
    PhiPattern("url", r"https?://[^\s]+"),
]

def scan_phi_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], pd.DataFrame | None]:
    """Return dataframe with PHI columns removed, metadata, and quarantine copy."""
    flagged: list[dict] = []
    quarantine_cols: list[str] = []
    text_columns = [
        col for col in df.columns
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])
    ]

    for col in text_columns:
        series = df[col].dropna().astype(str)
        if series.empty:
            continue
        matches: list[dict] = []
        for pattern in PHI_PATTERNS:
            count = series.str.contains(pattern.regex, regex=True, na=False).sum()
            if count:
                matches.append({"pattern": pattern.name, "count": int(count)})
        # Heuristic: flag obvious PHI column names even if pattern doesn't match yet
        if not matches and any(token in col.lower() for token in ("name", "email", "phone", "mrn")):
            matches.append({"pattern": "column_name", "count": len(series)})
        if matches:
            flagged.append({"column": col, "matches": matches})
            quarantine_cols.append(col)

    quarantine_df = df[quarantine_cols].copy() if quarantine_cols else None
    if quarantine_cols:
        df = df.drop(columns=quarantine_cols)
    return df, flagged, quarantine_df
