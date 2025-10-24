#!/usr/bin/env python3
"""
re_stats_json.py 

Read a CSV/Excel sizing sheet and emit JSON payloads suitable for the Redis Cloud REST API:
1) --out-database: a JSON array of database-create payload, one object per DB (quantity is expanded)
2) --out-subscription: a JSON object containing a `creation_plan` array that aggregates by size/replication/throughput
3) --out-combined: a JSON object with both keys: { "databases": [...], subscription" {"creation_plan": [...]}}

Column Expectations (auto detected by fuzzy names):
- database name: databaseNames | database | db | name
- quantity: quantity | qty | count | number | instances
- dataset size (in GB): datasetSizeInGB | memoryGB | sizeGB | datasetGB
- throughput ops/sec: throughputOpsSec | throughput | opsSec | ops
- replication:          replication | replicated | enableReplication
- OSS Cluster API:      ossClusterAPI | support_oss_cluster_api | osscluster
- modules: modules | redis_modules

Usage:
python re_stats_json.py \
    --input sizing.csv \
    --out-databases databases.json \
    --out-subscription subscription.json \
    --out-combined redis_payloads.json

Notes:
- The redis cloud database create API typically expect fields like: name, dataset_size_in_gb, replication, throughput_measurement_by, throughput_measurement_value etc
- The Subscription Create/Update API accepts a `creation_plan` array with dataset_size_in_gb, quantity, replication, throughput_measurement_by, throughput_measurement_value
- This script emits JSON shaped
"""

from __future__ import annotations
import argparse, json, sys, re
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd 

# Use shared helpers (provided by the user in helper.py)
from helper import pick_column, str_to_bool, load_table, sanitize_resource_name, normalise # noqa: F401 (some may be unused)

# -----------------------------
# Config: canonical alias sets
# -----------------------------
_DEF_DB_ALIASES = ["databasename","database","dbname","db","name","databasenames","database_name"]
_DEF_QTY_ALIASES = ["quantity","qty","count","num","number","instances"]
_DEF_MEM_ALIASES = [
"datasetsizeingb","datasetsizegb","memoryingb","memorygb","memory",
"sizegb","datasetgb","datasetsize","size","dataset_size_in_gb","dataset_sizegb","dataset_size"
]
_DEF_OPS_ALIASES = ["throughputopssec","throughputopspersec","throughputops","throughput","opssec","opspersec","ops"]
_DEF_REPL_ALIASES= ["replication","replicated","isreplicated","replica","replicaenabled","enablereplication"]
_DEF_OSS_ALIASES = ["ossclusterapi","osscluster","supportossclusterapi","support_oss_cluster_api","osscluster_api"]
_DEF_MODS_ALIASES= ["modules","redis_modules"]

# -----------------------------
# Processing Logic 
# -----------------------------
def build_payloads(df: pd.DataFrame, prec: int = 3) -> Dict[str, Any]:
    db_col = pick_column(df, _DEF_DB_ALIASES)
    qty_col = pick_column(df, _DEF_QTY_ALIASES)
    mem_col = pick_column(df, _DEF_MEM_ALIASES)
    ops_col = pick_column(df, _DEF_OPS_ALIASES)
    repl_col= pick_column(df, _DEF_REPL_ALIASES)
    oss_col = pick_column(df, _DEF_OSS_ALIASES)
    mods_col= pick_column(df, _DEF_MODS_ALIASES)

    missing = []
    if not db_col:
        missing.append("database_name")
    if not mem_col:
        missing.append("dataset size (GB)")
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}. Columns seens: {list(df.colums)}")
    
    work: Dict[str, Any] = {}
    work["database_name"] = df[db_col].astype(str)
    work["quantity"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(1).astype(int) if qty_col else 1
    work["dataset_size_in_gb"] = pd.to_numeric(df[mem_col], errors="coerce").round(prec)
    work["throughput_ops_per_second"] = pd.to_numeric(df[ops_col], errors="coerce").fillna(0).astype(int) if ops_col else pd.Series([0]*len(df))
    work["replication"] = df[repl_col].apply(str_to_bool) if repl_col else False
    work["support_oss_cluster_api"] = df[oss_col].apply(str_to_bool) if oss_col else False

    if mods_col:
        mods_series = df[mods_col].astype(str).fillna("").apply(lambda s: [m.strip() for m in s.split(",") if m.strip()])
    else:
        mods_series = None

    wf = pd.DataFrame(work)

    # Clean up dataset
    before = len(wf)
    wf = wf.dropna(subset=["database_name", "dataset_size_in_gb"]).copy()
    wf["dataset_size_in_gb"] = pd.to_numeric(wf["dataset_size_in_gb"], errors="coerce")
    wf = wf[wf["dataset_size_in_gb"] > 0 ]
    after = len(wf)
    skipped = before - after

    databases: List[Dict[str, Any]] = []
    for idx, r in wf.iterrows():
        qty = int(r.get("quantity", 1)) if isinstance(work["quantity"], pd.Series) else int(work["quantity"]) if isinstance(work["quantity"], int) else 1
        database_name = str(r.get("database_name")).strip()
        database_mods = mods_series.iloc[idx] if mods_series is not None else []
        for i in range(max(qty,1)):
            name = database_name if qty == 1 else f"{database_name}-{i+1}"
            databases.append({
                "name": name,
                "dataset_size_in_gb": float(round(r.get("dataset_size_in_gb", 0.0), prec)),
                "replication": bool(r.get("replication", False)),
                "throughput_measurement_by": "operations-per-second",
                "throughput_measurement_value": int(r.get("throughput_ops_per_second", 0)),
                "modules": database_mods,
                "support_oss_cluster_api": bool(r.get("support_oss_cluster_api", False)),
            })
    
    # Build creation plan
    wf["size_key"] = wf["dataset_size_in_gb"].round(prec)
    g = wf.groupby(["size_key","replication","throughput_ops_per_second"], dropna=False)["quantity"].sum().reset_index()
    creation_plan = [
        {
        "dataset_size_in_gb": float(round(row["size_key"], prec)),
        "quantity": int(row["quantity"]),
        "replication": bool(row["replication"]),
        "throughput_measurement_by": "operations-per-second",
        "throughput_measurement_value": int(row["throughput_ops_per_second"]),
        }
        for _, row in g.iterrows()
    ]

    return {
        "databases": databases,
        "subscription": {"creation_plan": creation_plan},
        "skipped_rows": int(skipped),
    }

# -----------------------------
# CLI Entry Point
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV or Excel file path with DB sizing")
    ap.add_argument("--sheet", default=None, help="Excel sheet name (if input is .xlsx/.xls)")
    ap.add_argument("--out-databases", dest="out_dbs", default=None, help="Path to write databases JSON array")
    ap.add_argument("--out-subscription", dest="out_sub", default=None, help="Path to write subscription JSON with creation_plan")
    ap.add_argument("--out-combined", dest="out_combined", default="redis_payloads.json", help="Path to write combined JSON (default)")
    ap.add_argument("--precision", type=int, default=3, help="Decimal precision for dataset_size_in_gb")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        ap.error(f"Input file not found: {path}")
    
    try:
        df = load_table(path, args.sheet)
    except Exception as e:
        print(f"ERROR: failed to load table: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        payloads = build_payloads(df, prec=args.precision)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    # Write files
    if args.out_dbs:
        Path(args.out_dbs).write_text(json.dumps(payloads["databases"], indent=2))
        print(f"Wrote databases payload: {args.out_dbs}")
    if args.out_sub:
        Path(args.out_sub).write_text(json.dumps(payloads["subscription"], indent=2))
        print(f"Wrote subscription payload: {args.out_sub}")

    if args.out_combined:
        Path(args.out_combined).write_text(json.dumps({
        "databases": payloads["databases"],
        "subscription": payloads["subscription"],
        }, indent=2))
        print(f"Wrote combined payload: {args.out_combined}")


    if payloads.get("skipped_rows", 0):
        print(f"Note: Skipped {payloads['skipped_rows']} row(s) with missing/invalid name or dataset_size_in_gb)", file=sys.stderr)

if __name__ == "__main__":
    main()