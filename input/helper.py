import re
import pandas as pd
from pathlib import Path

def normalise(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

"""
This function is to ensure column search capabilities in
a most robust manner
"""
def pick_column(df, candidates):
    # normalize columns; keep first occurrence to preserve df column order on collisions
    cols_norm = {}
    for c in df.columns:
        key = normalise(c)
        cols_norm.setdefault(key, c)

    # normalize candidate strings, dropping any None values
    cands_norm = [normalise(c) for c in candidates if c is not None]

    # exact match by candidate priority
    for cand in cands_norm:
        if cand in cols_norm:
            return cols_norm[cand]

    # substring fallback by candidate priority
    for cand in cands_norm:
        if not cand:
            continue
        for ncol, orig in cols_norm.items():
            if cand in ncol:
                return orig

    return None

def str_to_bool(val):
    if pd.isna(val):
        return False
    s = str(val).strip().lower()
    # Return boolean true for any of the below syntax
    return s in {"1","true"}

def sanitize_resource_name(name: str) -> str:
    # Terraform resource labels: cannot start with special characters or digit
    resource_name = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip()).lower()
    if not resource_name or re.match(r"^\d", resource_name):
        resource_name = f"db_{resource_name}" if resource_name else "db_resource"
    return resource_name

def load_table(path: Path, sheet: str | None):
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet or 0)
    else:
        # Try a few encoding to process the CSV file
        for enc in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                return pd.read_csv(path, encoding=enc)
            except Exception:
                pass

        return pd.read_csv(path)