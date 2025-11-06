from __future__ import annotations
import pandas as pd

def describe_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    return sub.describe().T

def pearson_corr(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    return sub.corr(method="pearson")

def missing_summary(df: pd.DataFrame) -> dict:
    return df.isna().sum().to_dict()

def simple_report(df: pd.DataFrame, cols: list[str]) -> dict:
    desc = describe_columns(df, cols).reset_index().rename(columns={"index":"variable"})
    corr = pearson_corr(df, cols)
    return {
        "descriptives": desc.to_dict(orient="records"),
        "pearson_corr": corr.to_dict(),
        "missing": missing_summary(df)
    }
