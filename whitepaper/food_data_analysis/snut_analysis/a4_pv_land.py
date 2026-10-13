#!/usr/bin/env python3
"""
A4. PV land needed to power the lamps, per person-year, at the Costa Rica regional
points and the 52N reference, from PVGIS 5.3 output fetched by fetch_pvgis.py.

Two methods:
  A  van Delden chain (vandelden2021vf Fig. 4 caption p.952): land = E_lamp /
     (G x 0.20 PV efficiency x 0.75 land packing), G = annual global horizontal
     irradiation. No system or temperature losses (as in the source).
  B  PVGIS system yield: E_y (kWh/kWp/yr, optimal tilt, 14% system loss, PVGIS
     temperature model). 1 kWp at 20% efficiency = 5 m2 module; / 0.75 packing
     = 6.67 m2 land per kWp. Packing is van Delden's assumption, carried over.
Lighting only, as in van Delden (HVAC excluded). Lamp energies from a1/a2b CSVs.
"""
import csv, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parents[2] / "sources" / "pvgis_2026-10-12" / "raw"
OUT = HERE / "results_a4_pv_land.csv"
PV_EFF, PACK = 0.20, 0.75
MJ_PER_KWH = 3.6


def totals(stem):
    d = json.loads((RAW / f"{stem}.json").read_text())
    t = d["outputs"]["totals"]["fixed"]
    return dict(E_y=t["E_y"], H_y=t["H(i)_y"], db=d["inputs"]["meteo_data"]["radiation_db"],
                slope=d["inputs"]["mounting_system"]["fixed"]["slope"]["value"])


SITES = [
    ("CR highland (San Jose)", "cr_highland_sanjose", "default"),
    ("CR Pacific lowland (Liberia)", "cr_lowland_pacific_liberia", "default"),
    ("CR Caribbean lowland (Limon)", "cr_lowland_caribbean_limon", "default"),
    ("52N Wageningen (SARAH3)", "nl_52N_wageningen", "default"),
    ("52N Wageningen (ERA5)", "nl_52N_wageningen", "PVGIS-ERA5"),
]


def lamp_loads():
    """kWh/person/yr at 2,400 kcal/d, at 3.0 and 4.1 umol/J."""
    loads = {}
    for r in csv.DictReader(open(HERE / "results_a1_area_energy.csv")):
        if r["source"] == "wheeler2008crop" and r["crop"] in ("potato", "wheat"):
            for e in ("3.0", "4.1"):
                loads[f"{r['crop']} calories only @{e}"] = float(r[f"lamp_kWh_person_yr_2400 @{e}"])
    for r in csv.DictReader(open(HERE / "results_a2b_ce_lp.csv")):
        if r["kcal"] == "2400" and r["iron"] == "iron_10":
            loads[f"5-crop nutrient LP {r['sex']} @4.1"] = float(r["lamp_kWh_yr @4.1"])
    return loads


def main():
    # reproduce van Delden 28.2 m2 land for 9 m2 lit (Fig. 4c)
    led_MJ = 1502 * 9
    land_vd = led_MJ / (3200 * PACK * PV_EFF)
    print(f"check: van Delden 9 x 1,502 MJ / (3,200 x 0.75 x 0.20) = {land_vd:.1f} m2 (source 28.2)")
    print(f"       van Delden G = 3,200 MJ/m2/yr = {3200/MJ_PER_KWH:.0f} kWh/m2/yr")
    loads = lamp_loads()
    rows = []
    for label, stem, db in SITES:
        h, o = totals(f"{stem}_hor_{db}"), totals(f"{stem}_opt_{db}")
        G = h["H_y"]
        print(f"\n{label}: GHI {G:.0f} kWh/m2/yr ({G*MJ_PER_KWH:.0f} MJ); "
              f"E_y opt {o['E_y']:.0f} kWh/kWp/yr at {o['slope']} deg [{o['db']}]")
        for name, kwh in loads.items():
            a = kwh / (G * PV_EFF * PACK)
            b = kwh / o["E_y"] / PV_EFF / PACK
            print(f"   {name:<32} {kwh:>7.0f} kWh -> land A {a:6.0f} m2 | B {b:6.0f} m2")
            rows.append(dict(site=label, radiation_db=o["db"], GHI_kWh_m2_yr=round(G),
                             E_y_opt_kWh_kWp_yr=round(o["E_y"]), opt_slope_deg=o["slope"],
                             load=name, lamp_kWh_person_yr=round(kwh),
                             land_m2_A_vandelden_chain=round(a), land_m2_B_pvgis_system=round(b)))
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()
