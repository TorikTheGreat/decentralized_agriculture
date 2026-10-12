#!/usr/bin/env python3
"""
A2b. Same LP as a2, but with the MEASURED controlled-environment edible yields of
wheeler2008crop Table 2 (potato, wheat, soybean, tomato, lettuce), continuous cropping.

Fresh yield kg m-2 yr-1 = edible DM g m-2 d-1 x 365 / 1000 / (1 - USDA water/100)
(dry mass converted to the USDA fresh basis with USDA moisture; ASSUMPTION: chamber
oven-dry mass ~ USDA dry matter). Per m2 of growing area (stacked shelves).
Lamp electricity per person-year is reported from the photon use of the solution
(mol = sum a_i x DLI_i x 365) at each LED efficacy in inputs.
Only 5 crops: the solution is a bound for THAT crop set, not for a full diet design.
"""
from pathlib import Path
import csv
import duckdb
import inputs as I
from a2_nutrient_area_lp import usda_profile, requirement_vector, solve

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "food_data.duckdb"
OUT = HERE / "results_a2b_ce_lp.csv"


def main():
    con = duckdb.connect(str(DB), read_only=True)
    crops = []
    for d in I.CE_DATA:
        if d["key"] != "wheeler2008crop":
            continue
        p = usda_profile(con, desc_exact=d["usda"])
        water = p["water"] / 10.0  # back to g/100 g
        fresh = d["dm"] * 365 / 1000.0 / (1 - water / 100.0)
        crops.append(dict(item=d["crop"], kg_m2_yr=fresh, p=p, mol=d["mol"]))
    con.close()
    print("A2b  LP on wheeler2008crop measured CE yields (5 crops), per m2 growing area")
    for c in crops:
        print(f"  {c['item']:<8} fresh {c['kg_m2_yr']:.1f} kg/m2/yr at {c['mol']} mol/m2/d")
    rows = []
    for sex in ["F", "M"]:
        for lvl, kcal in I.KCAL_PER_DAY.items():
            for iron in ["iron_10", "iron_15"]:
                req = requirement_vector(sex, kcal, iron, "zinc_moderate")
                r = solve(crops, req, I.VITA_FACTORS["RE 1:6/1:12 (Annex)"])
                if r is None:
                    print(f"  {sex} {kcal} {iron}: INFEASIBLE with these 5 crops")
                    rows.append(dict(sex=sex, kcal=kcal, iron=iron, m2_per_person="infeasible"))
                    continue
                mol_d = sum(a * next(c["mol"] for c in crops if c["item"] == k) for k, a in r["mix"].items())
                lamp = {f"lamp_kWh_yr @{e}": round(mol_d * 365 / (3.6 * e))
                        for e in I.LED_EFFICACY_UMOL_PER_J.values()}
                print(f"  {sex} {kcal} {iron}: {r['area']:.1f} m2 [{', '.join(r['binding'])}] "
                      + ", ".join(f"{k} {v:.1f}" for k, v in r["mix"].items())
                      + f" | {mol_d:.0f} mol/d; lamp kWh/yr @2.5: {lamp['lamp_kWh_yr @2.5']}, @4.1: {lamp['lamp_kWh_yr @4.1']}")
                rows.append(dict(sex=sex, kcal=kcal, iron=iron, m2_per_person=round(r["area"], 1),
                                 binding=";".join(r["binding"]), mol_per_day=round(mol_d),
                                 **{f"m2 {k}": round(v, 2) for k, v in r["mix"].items()}, **lamp))
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print(f"  Masuda 2005 benchmark: 64.8 m2/person (more crops, 46.3/28.3 mol). wrote {OUT.name}")


if __name__ == "__main__":
    main()
