#!/usr/bin/env python3
"""
A6. Dutch greenhouse yields (kg m-2 yr-1) from CBS StatLine table 37738
(cbs2026groenteteelt), fetched 2026-10-12 to sources/cbs_37738_groenteteelt_2026-10-12/
(gitignored; see PROVENANCE.md there). yield = harvest (mln kg) / cultivated area (ha).
CBS counts area once per year only for crops harvested repeatedly from the same plants
(fruit vegetables, strawberry) and for mushrooms and radish, so only those give a
per-year yield.
Food energy from USDA SR Legacy (usdafdc2018srlegacy); area per person at 2,100/2,400/2,800 kcal/d.
Sweet pepper: CBS does not split colours; USDA red sweet pepper used (green is lower in kcal).
"""
import csv, glob
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[3]
CSV = glob.glob(str(ROOT / "sources" / "cbs_37738_groenteteelt_2026-10-12" / "*.csv"))[0]
CROPS = {"Tomaten": "tomato", "Komkommers": "cucumber", "Paprika's": "sweet pepper", "Aubergines": "aubergine"}
USDA = {"tomato": "Tomatoes, red, ripe, raw, year round average", "cucumber": "Cucumber, with peel, raw",
        "sweet pepper": "Peppers, sweet, red, raw", "aubergine": "Eggplant, raw"}
con = duckdb.connect(str(ROOT / "whitepaper" / "food_data_analysis" / "food_data.duckdb"), read_only=True)
def kcal100(desc):
    return con.execute("""SELECT fn.amount FROM usda_sr.food f JOIN usda_sr.food_nutrient fn USING (fdc_id)
                          WHERE f.description = ? AND fn.nutrient_id = 1008""", [desc]).fetchone()[0]
rows = []

for r in csv.DictReader(open(CSV)):
    name = r["groente"].strip()
    if name in CROPS and r["periode"] in ("2005", "2025"):
        y = float(r["oogst_mln_kg"]) * 1e6 / (float(r["teeltoppervlakte_ha"]) * 1e4)
        c = CROPS[name]; k = kcal100(USDA[c]) * 10 * y
        rows.append(dict(crop=c, year=r["periode"], kg_m2_yr=round(y, 1), kcal_100g=kcal100(USDA[c]),
                         kcal_m2_yr=round(k), **{f"m2_person_{d}": round(d * 365 / k) for d in (2100, 2400, 2800)}))
        print(rows[-1])
with open(Path(__file__).resolve().parent / "results_a6_cbs_yields.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
