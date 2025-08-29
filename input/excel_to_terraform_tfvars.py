#!/usr/bin/env python3
"""
 Read a CSV File of Redis Sizing and emit:
1) terraform.auto.tfvars.json - containing:
    - databases: map of DB entries (expanded by quantity)
    - creation_plans: aggregated size, throughput, replication

Column Expectations (auto detected by fuzzy names):
- database name: databaseNames | database | db | name
- quantity: quantity | qty | count | number | instances
- dataset size (in GB): datasetSizeInGB | memoryGB | sizeGB | datasetGB
- throughput ops/sec: throughputOpsSec | throughput | opsSec | ops
- replication:          replication | replicated | enableReplication
- OSS Cluster API:      ossClusterAPI | support_oss_cluster_api | osscluster

Usage:
python excel_to_terraform_tfvars.py --input sizing.csv --out terraform.auto.tfvars.json
"""

# TODO: Sort out the different region deployment

import argparse, json, sys, re
from pathlib import Path
# TODO: Define these helper functions or import from a separate module
from helper import pick_column, str_to_bool, load_table
import pandas as pd

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="CSV or Excel file path with DB sizing")
    p.add_argument("--sheet", default=None, help="Excel sheet name (if input is .xlsx/.xls)")
    p.add_argument("--out", default="terraform.auto.tfvars.json", help="Output tfvars JSON path")
    p.add_argument("--emit-hcl", dest="emit_hcl", default=None, help="Optional: write an HCL snippet for DB resources")
    args = p.parse_args()

    path = Path(args.input)
    if not path.exists():
        p.error(f"Input file not found: {path}")
    
    df = load_table(path, args.sheet)

    db_col = pick_column(df, ["databasename","database","dbname","db","name"])
    qty_col = pick_column(df, ["quantity","qty","count","num","number","instances"])
    mem_col = pick_column(df, ["datasetsizeingb","datasetsizegb","memoryingb","memorygb","memory","sizegb","datasetgb","datasetsize","size"])
    ops_col = pick_column(df, ["throughputopssec","throughputopspersec","throughputops","throughput","opssec","opspersec","ops"])
    repl_col= pick_column(df, ["replication","replicated","isreplicated","replica","replicaenabled","enablereplication"])
    oss_col = pick_column(df, ["ossclusterapi","osscluster","supportossclusterapi","support_oss_cluster_api","osscluster_api"])
    modules_col = pick_column(df, ["modules","redis_modules"])

    missing = []
    if not db_col: 
        missing.append("database_name")
    if not mem_col:
        missing.append("dataset size (GB)")
    if missing:
        print(f"ERROR: Missing required column(s): {', '.join(missing)}", file=sys.stderr)
        print(f"Columns seen: {list(df.columns)}", file=sys.stderr)
        sys.exit(2)

    PREC = 3

    # Build normalised working JSON frame
    work = {}
    work["database_name"] = df[db_col].astype(str)
    work["quantity"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(1).astype(int)
    work["dataset_size_in_gb"] = pd.to_numeric(df[mem_col], errors="coerce").round(PREC)
    work["throughput_ops_per_second"] = pd.to_numeric(df[ops_col], errors="coerce") \
        .fillna(0).astype(int) if ops_col else pd.Series([0] * len(df))
    work["replication"] = df[repl_col].apply(str_to_bool) if repl_col else False
    work["support_oss_cluster_api"] = df[oss_col].apply(str_to_bool) if oss_col else False

    if modules_col:
        mods = df[modules_col].astype(str).fillna("").apply(lambda s: [m.strip() for m in s.split(",") if m.strip()])
    else:
        mods = None

    wf = pd.DataFrame(work)

    print(wf)
    # Clean rows
    before = len(wf)
    wf = wf.dropna(subset=["database_name","dataset_size_in_gb"]).copy()
    wf["dataset_size_in_gb"] = wf["dataset_size_in_gb"]
    wf["size_key"] = wf["dataset_size_in_gb"].round(PREC)

    print(wf)
    after = len(wf)
    if after < before:
        print(f"Skipped {before - after} row(s) due to missing/zero dataset_size_in_gb or name", file=sys.stderr)

    # Build database map 
    databases = {}
    for idx, r in wf.iterrows():
        q = int(r.get("quantity", 1))
        database_name = str(r.get("database_name")).strip()
        base_mods = mods.iloc[idx] if modules_col else []
        for i in range(q):
            name = database_name if q == 1 else f"{database_name}-{i+1}"
            databases[name] = {
                "dataset_size_in_gb": float(round(r.get("dataset_size_in_gb", 0.0), PREC)),
                "replication": bool(r.get("replication", False)),
                "throughput_measurement_value": int(r.get("throughput_ops_per_second", 0)),
                "modules": base_mods,
                "support_oss_cluster_api": bool(r.get("support_oss_cluster_api", False)),
            }

    # Build creation plans by grouping
    g = wf.groupby(
        ["size_key", "replication", "throughput_ops_per_second"],
        dropna=False
    )["quantity"].sum().reset_index()


    creation_plans = [{
        "dataset_size_in_gb": float(round(row["size_key"], PREC)),
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