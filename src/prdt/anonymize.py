from __future__ import annotations
import os, hmac, hashlib
import pandas as pd

def _key() -> bytes:
    k = os.getenv("PRDT_ANON_KEY")
    if not k:
        raise RuntimeError("Set PRDT_ANON_KEY to a long random string.")
    return k.encode()

def hmac_token(x: str) -> str:
    return hmac.new(_key(), str(x).encode(), hashlib.sha256).hexdigest()[:16]

def anonymize_column(df: pd.DataFrame, col: str, out_col: str = "anon_id") -> pd.DataFrame:
    df = df.copy()
    if col not in df.columns:
        raise ValueError(f"Missing id column: {col}")
    df[out_col] = df[col].astype(str).apply(hmac_token)
    return df.drop(columns=[col])
