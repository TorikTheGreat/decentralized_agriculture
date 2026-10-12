#!/usr/bin/env python3
"""
A2. Minimum growing area to meet adult nutrient requirements from plants (open field),
by linear programming (method as in masuda2005ceef: minimise total area subject to
nutrient constraints), plus a contrast with baldi2024garden.

Decision variables: a_i = m2 of crop i (one harvest per year, FAOSTAT yield).
Supply of nutrient n per year = sum_i a_i * Y_i * c_i * x_{i,n}
  Y_i  FAOSTAT 2022 yield, kg m-2 yr-1 (world average or top national)
  c_i  basis/edible conversion from ../playground/compute_caloric_yield.py CROSSWALK
       (FLAGGED there; 'clean' crops have c=1)
  x    USDA SR Legacy nutrient per kg of the matched food
Constraints: supply >= requirement*365 for energy, protein (efsa2017drv) and the
FAO/WHO 2004 RNIs in inputs.RNI (one iron and one zinc variant per scenario).
Excluded nutrients (inputs.EXCLUDED) are reported, not constrained.
Missing USDA values are treated as 0 (conservative).

This is a LOWER BOUND for open-field, single-harvest, world-yield crops: no losses,
no seed, no rotation, no paths, no cooking losses, no diet acceptability.
"""
from pathlib import Path
import csv, sys, itertools
import duckdb
import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "playground"))
import inputs as I
from compute_caloric_yield import CROSSWALK  # noqa: E402

DB = HERE.parent / "food_data.duckdb"
FIELD_CSV = HERE.parent / "playground" / "results_caloric_yield.csv"
OUT = HERE / "results_a2_nutrient_lp.csv"
OUT_MIX = HERE / "results_a2_lp_mix.csv"
OUT_BALDI = HERE / "results_a2_baldi_contrast.csv"

NID = dict(kcal=1008, protein=1003, water=1051, vitC=1162, thiamin=1165, riboflavin=1166,
           niacin=1167, pantothenate=1170, vitB6=1175, folate=1177, bcar=1107, acar=1108,
           bcryp=1120, vitE=1109, vitK=1185, calcium=1087, iron=1089, magnesium=1090,
           zinc=1095, selenium=1103)


def usda_profile(con, desc_exact=None, pattern=None, cats=None):
    if desc_exact:
        where, args = "f.description = ?", [desc_exact]
    else:
        where = "f.description ILIKE ?" + (f" AND f.food_category_id IN ({','.join(map(str, cats))})" if cats else "")
        args = [pattern]
    fdc = con.execute(f"SELECT f.fdc_id, f.description FROM usda_sr.food f WHERE {where} "
                      "ORDER BY length(f.description) LIMIT 1", args).fetchone()
    if not fdc:
        raise SystemExit(f"USDA miss: {desc_exact or pattern}")
    vals = dict(con.execute("SELECT nutrient_id, amount FROM usda_sr.food_nutrient WHERE fdc_id=?",
                            [fdc[0]]).fetchall())
    per_kg = {k: (vals.get(v) or 0.0) * 10.0 for k, v in NID.items()}  # per 100 g -> per kg
    per_kg["_missing"] = [k for k, v in NID.items() if v not in vals]
    per_kg["_desc"] = fdc[1]
    return per_kg


def vitA_RE(p, factors):
    fb, fo = factors
    return p["bcar"] * fb + (p["acar"] + p["bcryp"]) * fo  # plants: no preformed retinol


def requirement_vector(sex, kcal, iron, zinc):
    s = 0 if sex == "F" else 1
    req = {"kcal": kcal, "protein": I.PROTEIN_G_PER_DAY[sex]}
    for n in ["vitA_RE", "vitE", "vitK", "vitC", "thiamin", "riboflavin", "niacin", "vitB6",
              "pantothenate", "folate", "calcium", "magnesium"]:
        req[n] = I.RNI[n][s]
    req["iron"] = I.RNI[iron][s]
    req["zinc"] = I.RNI[zinc][s]
    return req  # per day


def build_crops(con, yield_col, clean_only):
    field = {r["item"]: r for r in csv.DictReader(open(FIELD_CSV))}
    crops = []
    for item, pat, cats, basis, conv, _ in CROSSWALK:
        if basis == "industrial" or item not in field:
            continue
        if clean_only and basis != "clean":
            continue
        y = field[item][yield_col]
        if not y:
            continue
        p = usda_profile(con, pattern=pat, cats=cats)
        crops.append(dict(item=item, basis=basis, conv=conv,
                          kg_m2_yr=float(y) / 10000.0 * conv, p=p))
    return crops


def solve(crops, req, vitA_factors, use_ul=False, energy_cap=None):
    names = list(req)
    supply = np.zeros((len(names), len(crops)))  # per m2 per year
    for j, c in enumerate(crops):
        for i, n in enumerate(names):
            x = vitA_RE(c["p"], vitA_factors) if n == "vitA_RE" else c["p"][n]
            # x is per kg of food (kcal, g, mg or ug, matching the requirement unit)
            supply[i, j] = c["kg_m2_yr"] * x
    b = np.array([req[n] * 365.0 for n in names])
    A_ub, b_ub = [-supply], [-b]
    if use_ul:
        uls = I.UL if use_ul is True else use_ul
        for n, ul in uls.items():
            if n in names:
                A_ub.append(supply[[names.index(n)]]); b_ub.append(np.array([ul * 365.0]))
    if energy_cap:
        k = names.index("kcal")
        cap = np.diag(supply[k])
        A_ub.append(cap); b_ub.append(np.full(len(crops), energy_cap * req["kcal"] * 365.0))
    res = linprog(np.ones(len(crops)), A_ub=np.vstack(A_ub), b_ub=np.concatenate(b_ub),
                  bounds=[(0, None)] * len(crops), method="highs")
    if not res.success:
        return None
    x = res.x
    got = supply @ x
    ratio = {n: got[i] / b[i] for i, n in enumerate(names)}
    binding = [n for n in names if abs(ratio[n] - 1) < 1e-6]
    mix = {crops[j]["item"]: x[j] for j in range(len(crops)) if x[j] > 1e-6}
    return dict(area=x.sum(), ratio=ratio, binding=binding, mix=mix)


def main():
    con = duckdb.connect(str(DB), read_only=True)
    base_A = "RE 1:6/1:12 (Annex)"
    scenarios = []
    for sex, kcal in itertools.product(["F", "M"], I.KCAL_PER_DAY.values()):
        scenarios.append(dict(name="base", sex=sex, kcal=kcal, iron="iron_10", zinc="zinc_moderate",
                              vitA=base_A, yield_col="world_yield_kgha", clean=False, ul=False, cap=None))
    for sex in ["F", "M"]:
        common = dict(sex=sex, kcal=2400, iron="iron_10", zinc="zinc_moderate", vitA=base_A,
                      yield_col="world_yield_kgha", clean=False, ul=False, cap=None)
        scenarios += [
            {**common, "name": "iron 5%", "iron": "iron_5"},
            {**common, "name": "iron 15%", "iron": "iron_15"},
            {**common, "name": "zinc low bioavail.", "zinc": "zinc_low"},
            {**common, "name": "vitA 1:14/1:28", "vitA": "1:14/1:28 (p.26)"},
            {**common, "name": "with FAO/WHO ULs (Mg 350 etc.)", "ul": True},
            {**common, "name": "ULs except Mg (vitC, Ca, Zn)", "ul": {k: v for k, v in I.UL.items() if k != "magnesium"}},
            {**common, "name": "max 25% energy per crop", "cap": 0.25},
            {**common, "name": "clean-basis crops only", "clean": True},
            {**common, "name": "top national yields", "yield_col": "top_yield_kgha"},
        ]
    crop_cache = {}
    out, mixes = [], []
    print("A2  minimum OPEN-FIELD area (m2/person) meeting energy, protein and FAO/WHO RNIs")
    print("    excluded (not constrained):", ", ".join(I.EXCLUDED))
    print(f"\n{'scenario':<34}{'sex':<4}{'kcal':>6}{'m2':>8}  binding constraints / crops (m2)")
    for s in scenarios:
        key = (s["yield_col"], s["clean"])
        if key not in crop_cache:
            crop_cache[key] = build_crops(con, s["yield_col"], s["clean"])
        crops = crop_cache[key]
        req = requirement_vector(s["sex"], s["kcal"], s["iron"], s["zinc"])
        r = solve(crops, req, I.VITA_FACTORS[s["vitA"]], s["ul"], s["cap"])
        if r is None:
            print(f"{s['name']:<34}{s['sex']:<4}{s['kcal']:>6}{'INFEASIBLE':>8}")
            out.append({**{k: s[k] for k in ('name', 'sex', 'kcal')}, "m2_per_person": "infeasible"})
            continue
        mixtxt = ", ".join(f"{k} {v:.0f}" for k, v in sorted(r["mix"].items(), key=lambda kv: -kv[1]))
        print(f"{s['name']:<34}{s['sex']:<4}{s['kcal']:>6}{r['area']:>8.0f}  [{', '.join(r['binding'])}] {mixtxt}")
        out.append(dict(name=s["name"], sex=s["sex"], kcal=s["kcal"], iron=s["iron"], zinc=s["zinc"],
                        vitA=s["vitA"], yields=s["yield_col"], clean_only=s["clean"], UL=s["ul"],
                        energy_cap=s["cap"], m2_per_person=round(r["area"], 1),
                        binding=";".join(r["binding"]),
                        **{f"supply/req {n}": round(v, 2) for n, v in r["ratio"].items()}))
        for crop, a in r["mix"].items():
            mixes.append(dict(name=s["name"], sex=s["sex"], kcal=s["kcal"], crop=crop, m2=round(a, 2)))

    # data-quality note: USDA nutrients missing for crops used
    used = {c for m in mixes for c in [m["crop"]]}
    print("\nUSDA fields missing (treated as 0) for crops that appear in any solution:")
    for c in crop_cache[("world_yield_kgha", False)]:
        if c["item"] in used and c["p"]["_missing"]:
            print(f"  {c['item']:<30} {c['p']['_desc'][:45]:<46} missing: {', '.join(c['p']['_missing'])}")

    # ---------------- Baldi contrast ----------------
    print("\nBaldi 2024 plot (50 m2, 30 m2 cultivated; yields = area x ISTAT averages, not measured):")
    tot = {}
    for crop, area, kg, desc in I.BALDI_PLOT:
        p = usda_profile(con, desc_exact=desc)
        for n in NID:
            tot[n] = tot.get(n, 0.0) + kg * p[n]
        tot["vitA_RE"] = tot.get("vitA_RE", 0.0) + kg * vitA_RE(p, I.VITA_FACTORS[base_A])
    kg_total = sum(k for _, _, k, _ in I.BALDI_PLOT)
    rows = []
    for sex in ["F", "M"]:
        req = requirement_vector(sex, I.KCAL_PER_DAY["central"], "iron_10", "zinc_moderate")
        for n, r in req.items():
            rows.append(dict(sex=sex, nutrient=n, plot_supply_per_yr=round(tot[n], 1),
                             requirement_per_yr=round(r * 365, 1),
                             pct_of_one_person=round(100 * tot[n] / (r * 365), 1)))
    with open(OUT_BALDI, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"  {kg_total:.1f} kg/yr from the listed crops (minor species 0.82 kg omitted)")
    for sex in ["F", "M"]:
        line = ", ".join(f"{r['nutrient']} {r['pct_of_one_person']}%" for r in rows if r["sex"] == sex)
        print(f"  % of one adult {sex} (FAO/WHO RNI; energy 2,400; protein EFSA): {line}")
    con.close()

    keys = []
    for r in out:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(out)
    with open(OUT_MIX, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(mixes[0])); w.writeheader(); w.writerows(mixes)
    print(f"\nBenchmarks (m2/person, not computed here): {I.BENCHMARKS_M2_PER_PERSON}")
    print(f"wrote {OUT.name}, {OUT_MIX.name}, {OUT_BALDI.name}")


if __name__ == "__main__":
    main()
