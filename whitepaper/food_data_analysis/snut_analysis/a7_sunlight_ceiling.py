#!/usr/bin/env python3
"""
A7. Sunlight-limited yield: food energy per m2 per year from sunlight alone (no lamps)
for a potato crop grown all year under glass, for four conversion cases.

Yield-potential equation of zhu2010photosynthesis (Eq. 1, p.238, adapted from Monteith):
    Y = 0.487 * St * eps_i * eps_c * eps_p        [harvested biomass energy, MJ m-2]
  St     annual horizontal irradiation (PVGIS 5.3, jrc2026pvgis; raw JSON in
         sources/pvgis_2026-10-12/), i.e. a year-round season. 0.487 = PAR fraction
         of solar energy (zhu2010 p.238).
  tau    0.82, greenhouse transmissivity assumed by vandelden2021vf (Fig. 4 caption, p.952).

Cases (efficiency on PAR incident on the crop, i.e. eps_i * eps_c where applicable):
  theoretical   eps_c 0.094 = 4.6% of total solar = 9.4% of PAR incident on the leaf,
                after reflection and transmission losses (zhu2010 pp.240, 242, Fig. 2),
                so no separate eps_i; C3 at 30 C and 387 ppm. Upper bound at those
                conditions only.
  NASA chamber  potato edible-biomass radiation use efficiency 0.44 g dry matter per mol
                PAR (wheeler2008crop Abstract and Table 2, p.711), 1000-1200 ppm CO2,
                42.2 mol m-2 d-1. Applied directly to solar PAR photons, using 217 kJ per
                mol of photosynthetic photons (bugbee1988limits p.869).
  field 380/550 soybean at SoyFACE, season-long eps_i 0.89 and eps_c 0.032 (380 ppm) or
                0.038 (550 ppm) (zhu2010 Table 1, p.239), with eps_p 0.68 = potato
                edible/total dry matter in the NASA chamber (wheeler2008 Table 2; a mass
                ratio used as the energy ratio, consistent here because all biomass is
                converted at one energy content).
  Energy        17.2 MJ per kg dry matter, low-lipid biomass (bugbee1988limits p.869, from
                Lieth 1968); food energy from USDA potato kcal per g dry matter (as in a1).
  Note: zhu2010 Table 1 St (620 MJ/m2) behaves as PAR; zhu2010 p.240 gives 0.032 on a
  PAR basis (~1.5% of full spectrum), consistent with 0.487 * total solar used here.

Assumptions: continuous cropping; temperature, water and nutrients non-limiting; no
losses; heating or cooling energy needed to hold temperature is not counted.
"""
from pathlib import Path
import csv, json
import duckdb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = ROOT / "sources" / "pvgis_2026-10-12" / "raw"
OUT = HERE / "results_a7_sunlight_ceiling.csv"

PAR, TAU, MJ_PER_KG, MJ_PER_MOL = 0.487, 0.82, 17.2, 0.217
EPS_P = 18.4 / 27.2
SITES = {"52N Wageningen (SARAH3)": "nl_52N_wageningen_hor_default",
         "CR highland (San Jose)": "cr_highland_sanjose_hor_default",
         "CR Pacific lowland (Liberia)": "cr_lowland_pacific_liberia_hor_default",
         "CR Caribbean lowland (Limon)": "cr_lowland_caribbean_limon_hor_default"}
CASES = ["theoretical (0.094, 30 C, 387 ppm)", "NASA chamber RUE (0.44 g/mol, 1000-1200 ppm)",
         "field soybean (0.89 x 0.032, 380 ppm)", "field soybean (0.89 x 0.038, 550 ppm)"]


def potato_kcal_per_kg_dm():
    con = duckdb.connect(str(HERE.parent / "food_data.duckdb"), read_only=True)
    r = con.execute("""
        SELECT max(CASE WHEN fn.nutrient_id=1008 THEN fn.amount END),
               max(CASE WHEN fn.nutrient_id=1051 THEN fn.amount END)
        FROM usda_sr.food f JOIN usda_sr.food_nutrient fn USING (fdc_id)
        WHERE f.description = 'Potatoes, flesh and skin, raw'""").fetchone()
    return r[0] / (100 - r[1]) * 1000


def edible_kg_dm(par_mj, case):
    if case.startswith("theoretical"):
        return par_mj * 0.094 * EPS_P / MJ_PER_KG
    if case.startswith("NASA"):
        return par_mj / MJ_PER_MOL * 0.44 / 1000
    ec = 0.032 if "380" in case else 0.038
    return par_mj * 0.89 * ec * EPS_P / MJ_PER_KG


def main():
    kcal_kg = potato_kcal_per_kg_dm()
    rows = []
    for site, stem in SITES.items():
        ghi = json.loads((RAW / f"{stem}.json").read_text())["outputs"]["totals"]["fixed"]["H(i)_y"]
        par_mj = PAR * ghi * 3.6 * TAU
        for case in CASES:
            kcal = edible_kg_dm(par_mj, case) * kcal_kg
            rows.append(dict(site=site, ghi_kWh_m2_yr=round(ghi), case=case,
                             par_mol_m2_d_under_glass=round(par_mj / MJ_PER_MOL / 365, 1),
                             kcal_m2_yr=round(kcal),
                             m2_person_2100=round(2100 * 365 / kcal), m2_person_2400=round(2400 * 365 / kcal),
                             m2_person_2800=round(2800 * 365 / kcal)))
            print(rows[-1])
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
