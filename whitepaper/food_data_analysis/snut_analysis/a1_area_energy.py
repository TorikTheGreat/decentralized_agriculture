#!/usr/bin/env python3
"""
A1. Area vs energy for dietary energy (calories only).

For each measured controlled-environment (CE) dataset in inputs.CE_DATA:
  kcal per g edible dry mass  = USDA kcal/100 g fresh / (100 - USDA water g/100 g)
  kcal m-2 d-1 (growing area) = edible DM g m-2 d-1 x kcal/g DM
  m2 per person               = kcal/day requirement / kcal m-2 d-1
  photons per kcal            = mol m-2 d-1 / kcal m-2 d-1
  lamp kWh per kcal           = photons per kcal x kWh/mol, kWh/mol = 1/(3.6 x umol/J)
  total PF kWh per kcal       = lamp kWh / lighting share (graamans2018plant, plant factories)
  PV land (52N, lighting only)= mol/d needed x (vandelden land per lit m2 / DLI) x (3.5 / efficacy)

Open-field baseline: ../playground/results_caloric_yield.csv (FAOSTAT 2022 world-average
and top-national yield x USDA kcal; one harvest per year assumed by FAOSTAT yield/yr).

Assumptions (ours) are printed with the results. CE rates are per day of crop
growth on GROWING area (stacked shelves for the NASA chamber), assuming continuous
year-round cropping; floor footprint is not reported in the sources.
"""
from pathlib import Path
import csv, duckdb
import inputs as I

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "food_data.duckdb"
FIELD_CSV = HERE.parent / "playground" / "results_caloric_yield.csv"
OUT = HERE / "results_a1_area_energy.csv"

FIELD_ITEM = {  # CE crop -> FAOSTAT item in the open-field results
    "potato": "Potatoes", "potato (best)": "Potatoes", "wheat": "Wheat",
    "wheat (record)": "Wheat", "soybean": "Soya beans", "tomato": "Tomatoes",
    "lettuce": None,  # not in the open-field results table
}


def usda_kcal_water(con, desc):
    r = con.execute("""
        SELECT max(CASE WHEN fn.nutrient_id=1008 THEN fn.amount END),
               max(CASE WHEN fn.nutrient_id=1051 THEN fn.amount END)
        FROM usda_sr.food f JOIN usda_sr.food_nutrient fn USING (fdc_id)
        WHERE f.description = ?""", [desc]).fetchone()
    if r is None or r[0] is None or r[1] is None:
        raise SystemExit(f"USDA miss: {desc}")
    return r  # kcal per 100 g fresh, water g per 100 g


def kwh_per_mol(umol_per_J):
    return 1.0 / (3.6 * umol_per_J)  # 1 mol = 1e6 umol; J -> kWh /3.6e6


def main():
    con = duckdb.connect(str(DB), read_only=True)
    field = {r["item"]: r for r in csv.DictReader(open(FIELD_CSV))}
    vd = I.VANDELDEN
    land_per_mol_d_at_vd = (vd["land_m2"] / vd["lit_m2"]) / vd["mol_m2_d"]  # m2 land per (mol/d)

    rows = []
    for d in I.CE_DATA:
        kcal100, water = usda_kcal_water(con, d["usda"])
        kcal_per_gdm = kcal100 / (100.0 - water)
        kcal_m2_d = d["dm"] * kcal_per_gdm
        mol_per_kcal = d["mol"] / kcal_m2_d
        fi = FIELD_ITEM.get(d["crop"])
        f = field.get(fi) if fi else None
        row = dict(source=d["key"], locator=d["loc"], crop=d["crop"], conditions=d["cond"],
                   edible_DM_g_m2_d=d["dm"], DLI_mol_m2_d=d["mol"],
                   usda_kcal_100g=kcal100, usda_water_g_100g=water,
                   kcal_per_g_DM=round(kcal_per_gdm, 3),
                   CE_kcal_m2_d=round(kcal_m2_d, 1),
                   CE_kcal_m2_yr=round(kcal_m2_d * 365),
                   field_world_kcal_m2_yr=int(f["world_kcal_m2"]) if f else None,
                   field_top_kcal_m2_yr=int(f["top_kcal_m2"]) if f else None)
        if f:
            row["ratio_CE_vs_field_world"] = round(kcal_m2_d * 365 / int(f["world_kcal_m2"]), 1)
            row["ratio_CE_vs_field_top"] = round(kcal_m2_d * 365 / int(f["top_kcal_m2"]), 1)
        for lvl, kcal in I.KCAL_PER_DAY.items():
            row[f"CE_m2_person_{kcal}"] = round(kcal / kcal_m2_d, 1)
            if f:
                row[f"field_world_m2_person_{kcal}"] = round(kcal * 365 / int(f["world_kcal_m2"]))
                row[f"field_top_m2_person_{kcal}"] = round(kcal * 365 / int(f["top_kcal_m2"]))
        row["mol_per_kcal"] = round(mol_per_kcal, 4)
        for name, eff in I.LED_EFFICACY_UMOL_PER_J.items():
            lamp = mol_per_kcal * kwh_per_mol(eff)
            row[f"lamp_kWh_per_kcal @{eff}"] = round(lamp, 4)
            row[f"lamp_kWh_person_yr_2400 @{eff}"] = round(lamp * 2400 * 365)
            row[f"PV_land_m2_person_2400_52N @{eff}"] = round(
                (2400 * mol_per_kcal) * land_per_mol_d_at_vd * (vd["led_umol_J"] / eff), 1)
        rows.append(row)
    con.close()

    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader(); w.writerows(rows)

    # ---------------- printed summary ----------------
    print("A1  calories only; CE per m2 GROWING area, continuous cropping assumed\n")
    print(f"{'source':<18}{'crop':<15}{'kcal/gDM':>9}{'kcal/m2/d':>10}{'xField(world)':>14}{'xField(top)':>12}"
          f"{'m2/p@2100':>10}{'@2400':>7}{'@2800':>7}{'mol/kcal':>9}")
    for r in rows:
        print(f"{r['source']:<18}{r['crop']:<15}{r['kcal_per_g_DM']:>9.2f}{r['CE_kcal_m2_d']:>10.1f}"
              f"{str(r.get('ratio_CE_vs_field_world','-')):>14}{str(r.get('ratio_CE_vs_field_top','-')):>12}"
              f"{r['CE_m2_person_2100']:>10}{r['CE_m2_person_2400']:>7}{r['CE_m2_person_2800']:>7}{r['mol_per_kcal']:>9.3f}")
    print("\nOpen-field m2/person (FAOSTAT 2022 x USDA), world average / top national:")
    for item in ["Potatoes", "Wheat", "Soya beans", "Maize (corn)", "Cassava, fresh", "Sweet potatoes", "Tomatoes"]:
        f = field[item]
        print(f"  {item:<16} world {int(f['world_kcal_m2']):>5} kcal/m2/yr -> "
              + ", ".join(f"{k}: {round(k*365/int(f['world_kcal_m2']))}" for k in I.KCAL_PER_DAY.values())
              + f" | top {int(f['top_kcal_m2']):>5} -> "
              + ", ".join(f"{k}: {round(k*365/int(f['top_kcal_m2']))}" for k in I.KCAL_PER_DAY.values()))

    print("\nLamp electricity per person-year at 2,400 kcal/d (kWh), by LED efficacy (umol/J):")
    effs = list(I.LED_EFFICACY_UMOL_PER_J.values())
    print(f"{'crop':<34}" + "".join(f"{e:>9}" for e in effs))
    for r in rows:
        print(f"{(r['source'][:12]+' '+r['crop']):<34}" + "".join(f"{r[f'lamp_kWh_person_yr_2400 @{e}']:>9}" for e in effs))
    lo, hi = I.LIGHTING_SHARE_OF_PF_ELECTRICITY["hot climate"], I.LIGHTING_SHARE_OF_PF_ELECTRICITY["cold climate"]
    print(f"  total plant-factory electricity = lamp / lighting share ({lo}-{hi}): multiply by {1/hi:.2f}-{1/lo:.2f}")

    print("\nPV land per person at 2,400 kcal/d, lighting only, 52N, van Delden assumptions (m2):")
    print(f"{'crop':<34}" + "".join(f"{e:>9}" for e in effs))
    for r in rows:
        print(f"{(r['source'][:12]+' '+r['crop']):<34}" + "".join(f"{r[f'PV_land_m2_person_2400_52N @{e}']:>9}" for e in effs))

    t = I.TIBBITTS
    print(f"\nCross-check tibbitts1994potato: own 139 kcal/m2/d at 3.7 kcal/g; ours for 37.5 g DM: "
          f"{37.5*rows[0]['kcal_per_g_DM']:.0f} kcal/m2/d (USDA potato {rows[0]['kcal_per_g_DM']:.2f} kcal/gDM). "
          f"Tibbitts lamps {t['lamp_kW_person']} kW/person continuous = {t['lamp_kW_person']*24*365:.0f} kWh/yr at {t['kcal_d']} kcal/d.")
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()
