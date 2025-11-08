from __future__ import annotations
import os, hmac, hashlib
from pathlib import Path

DEFAULT_BAD_KEYS = {"changeme", "default", "test", "testkey"}

def _load_env_file() -> None:
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if not line or line.strip().startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key == "PRDT_ANON_KEY" and not os.getenv("PRDT_ANON_KEY"):
                os.environ[key] = value
import pandas as pd

def _key() -> bytes:
    _load_env_file()
    k = os.getenv("PRDT_ANON_KEY")
    if not k:
        raise RuntimeError("Set PRDT_ANON_KEY to a long random string.")
    if len(k) < 32 or k.lower() in DEFAULT_BAD_KEYS:
        raise RuntimeError("PRDT_ANON_KEY is too short or uses a default placeholder. See KEY_HANDLING.md.")
    return k.encode()

def hmac_token(x: str) -> str:
    return hmac.new(_key(), str(x).encode(), hashlib.sha256).hexdigest()[:16]

def anonymize_column(df: pd.DataFrame, col: str, out_col: str = "anon_id") -> pd.DataFrame:
    df = df.copy()
    if col not in df.columns:
        raise ValueError(f"Missing id column: {col}")
    df[out_col] = df[col].astype(str).apply(hmac_token)
    return df.drop(columns=[col])
