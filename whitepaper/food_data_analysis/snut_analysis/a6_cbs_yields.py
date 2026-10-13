#!/usr/bin/env python3
"""
A6. Dutch greenhouse yields (kg m-2 yr-1) from CBS StatLine table 37738
(cbs2026groenteteelt), fetched 2026-10-12 to sources/cbs_37738_groenteteelt_2026-10-12/
(gitignored; see PROVENANCE.md there). yield = harvest (mln kg) / cultivated area (ha).
CBS counts area once per year only for crops harvested repeatedly from the same plants
(fruit vegetables, strawberry) and for mushrooms and radish, so only those give a
per-year yield. National averages mix lit and unlit production.
"""
import csv, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CSV = glob.glob(str(ROOT / "sources" / "cbs_37738_groenteteelt_2026-10-12" / "*.csv"))[0]
CROPS = {"Tomaten": "tomato", "Komkommers": "cucumber", "Paprika's": "sweet pepper", "Aubergines": "aubergine"}

for r in csv.DictReader(open(CSV)):
    name = r["groente"].strip()
    if name in CROPS and r["periode"] in ("2005", "2025"):
        y = float(r["oogst_mln_kg"]) * 1e6 / (float(r["teeltoppervlakte_ha"]) * 1e4)
        print(f"{CROPS[name]:<13} {r['periode']}: {y:.1f} kg/m2/yr")
