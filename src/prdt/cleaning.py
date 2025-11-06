from __future__ import annotations
import pandas as pd

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (df.columns
                  .str.strip().str.lower()
                  .str.replace(" ", "_")
                  .str.replace("-", "_"))
    return df

def basic_clean(df: pd.DataFrame, drop_dupes: bool = True) -> pd.DataFrame:
    df = normalize_columns(df)
    if drop_dupes:
        df = df.drop_duplicates()
    df = df.replace({"NA": pd.NA, "N/A": pd.NA, "": pd.NA})
    return df
