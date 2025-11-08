from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import pandas as pd

@dataclass(frozen=True)
class ScaleDefinition:
    name: str
    items: list[str]
    method: str = "sum"  # sum | mean
    output: str | None = None
    reverse: list[str] | None = None
    min_item: float | None = None
    max_item: float | None = None
    cutoffs: dict[str, str] | None = None

    def output_column(self) -> str:
        return self.output or f"{self.name}_score"

SCALE_LIBRARY: dict[str, ScaleDefinition] = {
    "phq9": ScaleDefinition(
        name="phq9",
        items=[f"phq9_item{i}" for i in range(1, 10)],
        method="sum",
        min_item=0,
        max_item=3,
        cutoffs={
            "minimal": "0-4",
            "mild": "5-9",
            "moderate": "10-14",
            "moderately_severe": "15-19",
            "severe": "20-27",
        },
    ),
    "gad7": ScaleDefinition(
        name="gad7",
        items=[f"gad7_item{i}" for i in range(1, 8)],
        method="sum",
        min_item=0,
        max_item=3,
        cutoffs={
            "minimal": "0-4",
            "mild": "5-9",
            "moderate": "10-14",
            "severe": "15-21",
        },
    ),
}

def available_scales() -> list[str]:
    return sorted(SCALE_LIBRARY.keys())

def apply_scale_scores(df: pd.DataFrame, names: list[str]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Compute requested scales and append columns."""
    if not names:
        return df, []

    df = df.copy()
    metadata: list[dict[str, Any]] = []
    for name in names:
        if name not in SCALE_LIBRARY:
            raise SystemExit(f"[PRDT] Unknown scale '{name}'. Available: {', '.join(available_scales())}")

        definition = SCALE_LIBRARY[name]
        items = [col for col in definition.items if col in df.columns]
        if len(items) != len(definition.items):
            missing = sorted(set(definition.items) - set(items))
            raise SystemExit(f"[PRDT] Missing items for scale '{name}': {', '.join(missing)}")

        values = df[items].apply(pd.to_numeric, errors="coerce")

        if definition.reverse:
            for col in definition.reverse:
                if col in values.columns and definition.max_item is not None and definition.min_item is not None:
                    values[col] = definition.max_item + definition.min_item - values[col]

        if definition.method == "mean":
            score = values.mean(axis=1, skipna=True)
        else:
            score = values.sum(axis=1, skipna=True)

        out_col = definition.output_column()
        df[out_col] = score
        metadata.append({
            "name": definition.name,
            "output_column": out_col,
            "method": definition.method,
            "cutoffs": definition.cutoffs,
            "items": definition.items,
        })
    return df, metadata
