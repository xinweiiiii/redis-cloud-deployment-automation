#!/usr/bin/env python3
"""
csv_to_redis_tf.py

Read a CSV or Excel file of Redis DB sizing and emit:
  1) terraform.auto.tfvars.json containing:
        - databases: map of DB entries (expanded by quantity)
        - creation_plans: aggregated size×throughput×replication reservations
  2) (optional) an HCL snippet with rediscloud_subscription_database resources
     wired to var.databases (use --emit-hcl)

Column expectations (auto-detected by fuzzy names):
- database name:        databaseName | database | db | name
- quantity:             quantity | qty | count | number | instances
- dataset size (in GB): datasetSizeInGB | memoryGB | sizeGB | datasetGB | size
- throughput ops/sec:   throughputOpsSec | throughput | opsSec | ops
- replication:          replication | replicated | enableReplication
- OSS Cluster API:      ossClusterAPI | support_oss_cluster_api | osscluster

Usage:
  python csv_to_redis_tf.py --input sizing.csv --out terraform.auto.tfvars.json
  python csv_to_redis_tf.py --input sizing.xlsx --sheet dbs --env prod --emit-hcl redis_databases.generated.tf
"""
import argparse, json, sys, re
from pathlib import Path

try:
    import pandas as pd
except Exception as e:
    print("This script requires pandas. Install with: pip install pandas openpyxl", file=sys.stderr)
    raise

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

def pick_column(df, candidates):
    cols_norm = {norm(c): c for c in df.columns}
    # exact normalized match first
    for cand in candidates:
        if cand in cols_norm:
            return cols_norm[cand]
    # fallback: contains
    for ncol, orig in cols_norm.items():
        for cand in candidates:
            if cand in ncol:
                return orig
    return None

def str_to_bool(val):
    if pd.isna(val):
        return False
    s = str(val).strip().lower()
    return s in {"1","true","yes","y","t"}

def sanitize_resource_name(name: str) -> str:
    # Terraform resource labels: letters, digits, underscores only; must not start with digit
    x = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip())
    if re.match(r"^\d", x):
        x = f"db_{x}"
    return x

def load_table(path: Path, sheet: str | None):
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet or 0)
    else:
        # try a few encodings
        for enc in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                return pd.read_csv(path, encoding=enc)
            except Exception:
                pass
        # final attempt default
        return pd.read_csv(path)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="CSV or Excel file with DB sizing")
    p.add_argument("--sheet", default=None, help="Excel sheet name (if input is .xlsx/.xls)")
    p.add_argument("--env", default=None, help="Optional environment filter (expects a column named env)")
    p.add_argument("--out", default="terraform.auto.tfvars.json", help="Output tfvars JSON path")
    p.add_argument("--emit-hcl", dest="emit_hcl", default=None, help="Optional: write an HCL snippet for DB resources")
    args = p.parse_args()

    path = Path(args.input)
    if not path.exists():
        p.error(f"Input file not found: {path}")

    df = load_table(path, args.sheet)

    # If env filter provided and column exists, filter
    if args.env and "env" in [c.lower() for c in df.columns]:
        df = df[df["env"].astype(str).str.lower() == args.env.lower()].copy()

    # Detect columns
    db_col  = pick_column(df, ["databasename","database","dbname","db","name"])
    qty_col = pick_column(df, ["quantity","qty","count","num","number","instances"])
    mem_col = pick_column(df, ["datasetsizeingb","datasetsizegb","memoryingb","memorygb","memory","sizegb","datasetgb","datasetsize","size"])
    tps_col = pick_column(df, ["throughputopssec","throughputopspersec","throughputops","throughput","opssec","opspersec","ops"])
    repl_col= pick_column(df, ["replication","replicated","isreplicated","replica","replicaenabled","enablereplication"])
    oss_col = pick_column(df, ["ossclusterapi","osscluster","supportossclusterapi","support_oss_cluster_api","osscluster_api"])
    modules_col = pick_column(df, ["modules","redis_modules"])

    missing = []
    if not db_col:   missing.append("database name")
    if not mem_col:  missing.append("dataset size (GB)")
    if missing:
        print(f"ERROR: Missing required column(s): {', '.join(missing)}", file=sys.stderr)
        print(f"Columns seen: {list(df.columns)}", file=sys.stderr)
        sys.exit(2)

    # Build normalized working frame
    work = {}
    work["database_name"] = df[db_col].astype(str)
    work["quantity"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(1).astype(int) if qty_col else 1
    work["dataset_size_in_gb"] = pd.to_numeric(df[mem_col], errors="coerce")
    work["throughput_ops_per_second"] = pd.to_numeric(df[tps_col], errors="coerce").fillna(0).astype(int) if tps_col else 0
    work["replication"] = df[repl_col].apply(str_to_bool) if repl_col else False
    work["support_oss_cluster_api"] = df[oss_col].apply(str_to_bool) if oss_col else False

    if modules_col:
        mods = df[modules_col].astype(str).fillna("").apply(lambda s: [m.strip() for m in s.split(",") if m.strip()])
    else:
        mods = None

    wf = pd.DataFrame(work)

    # Clean rows
    before = len(wf)
    wf = wf.dropna(subset=["database_name","dataset_size_in_gb"]).copy()
    wf["dataset_size_in_gb"] = wf["dataset_size_in_gb"].round().astype(int)
    wf = wf[wf["dataset_size_in_gb"] > 0]
    after = len(wf)
    if after < before:
        print(f"Skipped {before-after} row(s) due to missing/zero dataset_size_in_gb or name", file=sys.stderr)

    # Build databases map (expand quantity by suffixing -1..-N)
    databases = {}
    for idx, r in wf.iterrows():
        q = int(r.get("quantity", 1))
        base_name = str(r.get("database_name")).strip()
        base_mods = mods.iloc[idx] if modules_col else []
        for i in range(q):
            name = base_name if q == 1 else f"{base_name}-{i+1}"
            databases[name] = {
                "dataset_size_in_gb": int(r.get("dataset_size_in_gb", 0)),
                "replication": bool(r.get("replication", False)),
                "throughput_measurement_value": int(r.get("throughput_ops_per_second", 0)),
                "modules": base_mods,
                "support_oss_cluster_api": bool(r.get("support_oss_cluster_api", False)),
            }

    # Build creation_plans by grouping
    g = wf.groupby(
        ["dataset_size_in_gb","replication","throughput_ops_per_second"],
        dropna=False
    )["quantity"].sum().reset_index()

    creation_plans = [{
        "dataset_size_in_gb": int(row["dataset_size_in_gb"]),
        "quantity": int(row["quantity"]),
        "replication": bool(row["replication"]),
        "throughput_measurement_by": "operations-per-second",
        "throughput_measurement_value": int(row["throughput_ops_per_second"]),
    } for _, row in g.iterrows()]

    # Write tfvars JSON
    tfvars = {"databases": databases, "creation_plans": creation_plans}
    out_path = Path(args.out)
    out_path.write_text(json.dumps(tfvars, indent=2))
    print(f"Wrote {out_path}")

    # Optionally write HCL snippet for DB resources
    if args.emit_hcl:
        hcl_path = Path(args.emit_hcl)
        # Create a resource per DB using for_each over var.databases (recommended)
        hcl = [
            '// Generated by csv_to_redis_tf.py -- do not edit by hand',
            'resource "rediscloud_subscription_database" "db" {',
            '  for_each = var.databases',
            '  subscription_id              = rediscloud_subscription.sub.id',
            '  name                         = each.key',
            '  dataset_size_in_gb           = each.value.dataset_size_in_gb',
            '  replication                  = each.value.replication',
            '  throughput_measurement_by    = "operations-per-second"',
            '  throughput_measurement_value = each.value.throughput_measurement_value',
            '  modules                      = try(each.value.modules, [])',
            '  support_oss_cluster_api      = try(each.value.support_oss_cluster_api, false)',
            '}',
            '',
            '// In your subscription resource add:',
            '// dynamic "creation_plan" {',
            '//   for_each = var.creation_plans',
            '//   content {',
            '//     dataset_size_in_gb              = creation_plan.value.dataset_size_in_gb',
            '//     quantity                        = creation_plan.value.quantity',
            '//     replication                     = creation_plan.value.replication',
            '//     throughput_measurement_by       = "operations-per-second"',
            '//     throughput_measurement_value    = creation_plan.value.throughput_measurement_value',
            '//   }',
            '// }',
        ]
        hcl_path.write_text("\n".join(hcl))
        print(f"Wrote {hcl_path}")

if __name__ == "__main__":
    main()
