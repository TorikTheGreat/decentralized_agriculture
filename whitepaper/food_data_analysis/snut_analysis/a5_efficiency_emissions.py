#!/usr/bin/env python3
"""
A5. Two derived quantities used in the chapter text, from the a1 lamp energies.
  1. Lamp-only conversion efficiency: food energy of 2,400 kcal/d for a year
     (4.184 kJ/kcal) divided by lamp electricity. Compared in the text with
     lovat2025vf p.2 (19 studies, median ~1%, range 0.4-1.9%; 1-2% rule of thumb).
  2. Lamp CO2 per person-year at grid intensities from the sources:
     ember2026ger 2025: global 458, Brazil 110, India 670 gCO2e/kWh (pp.23, 109, 96);
     ice2024sostenibilidad p.58: Costa Rica SEN 25.5 (2020, lowest 2019-24), 114 (2024).
Lighting only (no HVAC); a1 datasets at 3.0 and 4.1 umol/J.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results_a5_efficiency_emissions.csv"
FOOD_KWH = 2400 * 365 * 4.184 / 3600
GRID = {"Costa Rica 2020 (25.5)": 25.5, "Brazil 2025 (110)": 110, "Costa Rica 2024 (114)": 114,
        "World 2025 (458)": 458, "India 2025 (670)": 670}


def main():
    rows = []
    print(f"food energy, 2,400 kcal/d for a year: {FOOD_KWH:.0f} kWh")
    for r in csv.DictReader(open(HERE / "results_a1_area_energy.csv")):
        for e in ("3.0", "4.1"):
            kwh = float(r[f"lamp_kWh_person_yr_2400 @{e}"])
            row = dict(source=r["source"], crop=r["crop"], led_umol_J=e, lamp_kWh=round(kwh),
                       lamp_only_efficiency_pct=round(100 * FOOD_KWH / kwh, 2),
                       **{f"t CO2e/yr @ {k}": round(kwh * g / 1e6, 1) for k, g in GRID.items()})
            rows.append(row)
            print(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
