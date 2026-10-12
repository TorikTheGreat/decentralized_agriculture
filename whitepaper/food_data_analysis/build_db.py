#!/usr/bin/env python3
"""
Build a local DuckDB database from the raw FAOSTAT + USDA FoodData Central CSVs.

The database (food_data.duckdb) is a REBUILDABLE BUILD ARTIFACT and is
git-ignored. The raw data is not committed to the repo: download it from the
primary sources listed in data/PROVENANCE.md (which also holds licences and
SHA-256 checksums), extract it under data/, then run this script.

    .venv/bin/python build_db.py

Tables are namespaced by source schema:
    faostat.*   -> FAOSTAT Crops & livestock products (QCL): main data + code lookups
    usda_sr.*   -> USDA FoodData Central, SR Legacy (2018 snapshot)
    usda_ff.*   -> USDA FoodData Central, Foundation Foods
"""
from pathlib import Path
import re
import sys
import duckdb

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DB_PATH = HERE / "food_data.duckdb"

SOURCES = {
    "faostat": DATA / "faostat_crops_livestock"
    / "Production_Crops_Livestock_E_All_Data_(Normalized)",
    "usda_sr": DATA / "usda_legacy_foods" / "FoodData_Central_sr_legacy_food_csv_2018-04",
    "usda_ff": DATA / "usda_foundation_foods"
    / "FoodData_Central_foundation_food_csv_2026-04-30",
}


def table_name(csv_path: Path) -> str:
    """Turn a CSV filename into a clean, lowercase SQL table name."""
    name = csv_path.stem.replace("Production_Crops_Livestock_E_", "")
    name = re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_").lower()
    return name or "unnamed"


def load_dir(con, schema: str, directory: Path) -> None:
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    csvs = sorted(directory.glob("*.csv"))
    if not csvs:
        sys.exit(
            f"No CSVs in {directory}\n"
            f"Download + extract the data first (see data/PROVENANCE.md)."
        )
    print(f"{schema}:")
    for csv in csvs:
        tbl = table_name(csv)
        path_sql = str(csv).replace("'", "''")
        create = (
            f'CREATE OR REPLACE TABLE {schema}."{tbl}" AS '
            f"SELECT * FROM read_csv_auto('{path_sql}'"
        )
        note = ""
        try:
            # Full-scan type detection (sample_size=-1) so types reflect the
            # whole file, not just the first rows.
            con.execute(create + ", sample_size=-1)")
        except duckdb.Error:
            # Some USDA metadata columns mix date formats and defeat type
            # inference. Load that file as all-text rather than fail the build;
            # numeric columns can be CAST in queries when needed.
            con.execute(create + ", all_varchar=true)")
            note = "  [all_varchar fallback]"
        n = con.execute(f'SELECT count(*) FROM {schema}."{tbl}"').fetchone()[0]
        print(f"  {schema}.{tbl:<30} {n:>12,} rows{note}")


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    print(f"Building {DB_PATH.name} ...\n")
    for schema, directory in SOURCES.items():
        load_dir(con, schema, directory)
    con.close()
    print(f"\nDone -> {DB_PATH}")


if __name__ == "__main__":
    main()
