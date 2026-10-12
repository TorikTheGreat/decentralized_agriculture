#!/usr/bin/env python3
"""
A3. Independent checks of a1/a2/a2b outputs, via a separate code path:
  - raw SQL + pandas instead of the analysis helper functions
  - recompute nutrient supply of each saved LP mix and test every constraint
  - re-solve the base LPs with a different algorithm (interior point vs dual simplex)
  - re-derive key a1 numbers by plain arithmetic and compare with the CSV
Exit code 1 if any check fails.
"""
from pathlib import Path
import csv, sys, math
import duckdb, pandas as pd
import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "playground"))
import inputs as I
from compute_caloric_yield import CROSSWALK

con = duckdb.connect(str(HERE.parent / "food_data.duckdb"), read_only=True)
fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def usda_row(desc=None, pattern=None, cats=None):
    if desc:
        q = "SELECT fdc_id FROM usda_sr.food WHERE description = ?"; a = [desc]
    else:
        q = ("SELECT fdc_id FROM usda_sr.food WHERE description ILIKE ?"
             + (f" AND food_category_id IN ({','.join(map(str, cats))})" if cats else "")
             + " ORDER BY length(description) LIMIT 1"); a = [pattern]
    fdc = con.execute(q, a).fetchone()[0]
    df = con.execute("SELECT nutrient_id, amount FROM usda_sr.food_nutrient WHERE fdc_id=?", [fdc]).df()
    return df.set_index("nutrient_id")["amount"]


print("A1 checks")
a1 = pd.read_csv(HERE / "results_a1_area_energy.csv")
pot = usda_row("Potatoes, flesh and skin, raw")
kcal_gdm = pot[1008] / (100 - pot[1051])
check(abs(kcal_gdm - 3.7) < 0.05, f"potato kcal/g DM {kcal_gdm:.3f} ~ 3.7 used by tibbitts1994/wheeler2006")
check(abs(37.5 * kcal_gdm - 139) < 1.5, f"tibbitts 37.5 g DM -> {37.5*kcal_gdm:.1f} kcal/m2/d vs source 139")
check(abs(38.0 * kcal_gdm - 141) < 1.5, f"wheeler2006 38 g DM -> {38*kcal_gdm:.1f} kcal/m2/d vs source 141")
r = a1[(a1.source == "wheeler2008crop") & (a1.crop == "potato")].iloc[0]
check(abs(r.CE_kcal_m2_d - 18.4 * kcal_gdm) < 0.1, "a1 potato kcal/m2/d matches 18.4 x kcal/gDM")
check(abs(r.CE_m2_person_2400 - 2400 / (18.4 * kcal_gdm)) < 0.1, "a1 potato m2/person @2400")
mol_d = 2400 * 42.2 / (18.4 * kcal_gdm)
check(abs(r["lamp_kWh_person_yr_2400 @2.5"] - mol_d * 365 / (3.6 * 2.5)) < 2, "a1 potato lamp kWh/yr @2.5")
vd = I.VANDELDEN
check(abs(r["PV_land_m2_person_2400_52N @3.4"] - mol_d * (28.2 / 9 / 14.4) * (3.5 / 3.4)) < 0.2, "a1 potato PV land @3.4")
check(abs(28.2 / 9 - 3.133) < 0.001, "van Delden 28.2/9 = 3.13 m2 land per lit m2")

print("\nA2 checks (recompute supply of saved mixes from raw USDA + FAOSTAT CSV)")
field = {row["item"]: row for row in csv.DictReader(open(HERE.parent / "playground" / "results_caloric_yield.csv"))}
cw = {c[0]: c for c in CROSSWALK}
NID = dict(kcal=1008, protein=1003, vitC=1162, thiamin=1165, riboflavin=1166, niacin=1167,
           pantothenate=1170, vitB6=1175, folate=1177, vitE=1109, vitK=1185, calcium=1087,
           iron=1089, magnesium=1090, zinc=1095)
mix = pd.read_csv(HERE / "results_a2_lp_mix.csv")
lp = pd.read_csv(HERE / "results_a2_nutrient_lp.csv")
for sex in ["F", "M"]:
    m = mix[(mix.name == "base") & (mix.sex == sex) & (mix.kcal == 2400)]
    sup = {n: 0.0 for n in list(NID) + ["vitA_RE"]}
    for _, row in m.iterrows():
        item, pat, cats, basis, conv, _ = cw[row.crop]
        u = usda_row(pattern=pat, cats=cats)
        kg = row.m2 * float(field[item]["world_yield_kgha"]) / 1e4 * conv
        for n, nid in NID.items():
            sup[n] += kg * 10 * float(u.get(nid, 0) or 0)
        sup["vitA_RE"] += kg * 10 * (float(u.get(1107, 0) or 0) / 6 + (float(u.get(1108, 0) or 0) + float(u.get(1120, 0) or 0)) / 12)
    s = 0 if sex == "F" else 1
    req = {"kcal": 2400, "protein": I.PROTEIN_G_PER_DAY[sex], "iron": I.RNI["iron_10"][s],
           "zinc": I.RNI["zinc_moderate"][s], "vitA_RE": I.RNI["vitA_RE"][s]}
    for n in ["vitE", "vitK", "vitC", "thiamin", "riboflavin", "niacin", "vitB6", "pantothenate",
              "folate", "calcium", "magnesium"]:
        req[n] = I.RNI[n][s]
    worst = min(sup[n] / (req[n] * 365) for n in req)
    check(worst >= 0.999, f"base {sex} 2400: every constraint met (min supply/req = {worst:.4f})")
    area = m.m2.sum()
    saved = float(lp[(lp.name == "base") & (lp.sex == sex) & (lp.kcal == 2400)].m2_per_person.iloc[0])
    check(abs(area - saved) < 0.5, f"base {sex} 2400: mix area {area:.1f} = reported {saved}")

    # re-solve with a different algorithm, raw matrices built here
    crops = [c for c in CROSSWALK if c[3] != "industrial" and c[0] in field and field[c[0]]["world_yield_kgha"]]
    A, names = [], list(req)
    for item, pat, cats, basis, conv, _ in crops:
        u = usda_row(pattern=pat, cats=cats)
        kgm2 = float(field[item]["world_yield_kgha"]) / 1e4 * conv
        col = []
        for n in names:
            if n == "vitA_RE":
                v = float(u.get(1107, 0) or 0) / 6 + (float(u.get(1108, 0) or 0) + float(u.get(1120, 0) or 0)) / 12
            else:
                v = float(u.get(NID[n], 0) or 0)
            col.append(kgm2 * 10 * v)
        A.append(col)
    A = np.array(A).T
    b = np.array([req[n] * 365 for n in names])
    res = linprog(np.ones(A.shape[1]), A_ub=-A, b_ub=-b, bounds=[(0, None)] * A.shape[1], method="highs-ipm")
    check(res.success and abs(res.fun - saved) < 0.5, f"base {sex} 2400: interior-point optimum {res.fun:.1f} = {saved}")

print("\nA2b checks")
ce = pd.read_csv(HERE / "results_a2b_ce_lp.csv")
for _, row in ce[ce.kcal == 2400].iterrows():
    cols = [c for c in ce.columns if c.startswith("m2 ") and not pd.isna(row[c])]
    check(abs(sum(row[c] for c in cols) - row.m2_per_person) < 0.3,
          f"a2b {row.sex} {row.iron}: crop areas sum to {row.m2_per_person}")

print("\nAll checks passed." if not fails else f"\n{len(fails)} check(s) FAILED")
sys.exit(1 if fails else 0)
