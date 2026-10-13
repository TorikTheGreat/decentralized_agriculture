#!/usr/bin/env python3
"""
Fetch PVGIS 5.3 PVcalc output (EU JRC, https://re.jrc.ec.europa.eu/pvg_tools/en/)
for the sites used in a4_pv_land.py. Raw JSON is saved unmodified to
sources/pvgis_<date>/raw/ (gitignored); the query URL is recorded in PROVENANCE.md.

Per site, two runs with 1 kWp c-Si, 14% system loss, free-standing:
  - opt : optimal slope and azimuth (PVGIS-computed)
  - hor : horizontal (angle=0), so H(i)_y = global horizontal irradiation
Radiation database: PVGIS default for the location, plus ERA5 forced for the
52N reference so it is comparable with the Costa Rica sites (SARAH does not
cover Central America; PVGIS falls back to ERA5 there).
"""
import json, sys, time, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "sources" / f"pvgis_{date.today().isoformat()}"
API = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"

# Regional points, not specific sites. Coordinates are city centres.
SITES = {
    "cr_highland_sanjose":     (9.93, -84.08),   # Central Valley, ~1,150 m
    "cr_lowland_pacific_liberia": (10.63, -85.44),  # Guanacaste, dry Pacific lowland
    "cr_lowland_caribbean_limon": (9.99, -83.03),   # humid Caribbean lowland
    "nl_52N_wageningen":       (51.97, 5.66),    # van Delden 2021 reference latitude
}
RUNS = {"opt": "optimalangles=1", "hor": "angle=0&aspect=0"}


def main():
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    log = []
    for site, (lat, lon) in SITES.items():
        dbs = [None] + (["PVGIS-ERA5"] if site.startswith("nl_") else [])
        for db in dbs:
            for run, q in RUNS.items():
                url = f"{API}?lat={lat}&lon={lon}&peakpower=1&loss=14&{q}&outputformat=json"
                if db:
                    url += f"&raddatabase={db}"
                tag = f"{site}_{run}" + (f"_{db}" if db else "_default")
                with urllib.request.urlopen(url, timeout=60) as r:
                    data = json.loads(r.read())
                (OUT / "raw" / f"{tag}.json").write_text(json.dumps(data, indent=1))
                used = data["inputs"]["meteo_data"]["radiation_db"]
                log.append(f"| {tag} | {used} | `{url}` |")
                print(tag, used, data["outputs"]["totals"]["fixed"]["E_y"])
                time.sleep(1)
    (OUT / "PROVENANCE.md").write_text(
        f"# PVGIS 5.3 PVcalc output, retrieved {date.today().isoformat()}\n\n"
        "Source: European Commission Joint Research Centre, PVGIS 5.3, "
        "https://re.jrc.ec.europa.eu/pvg_tools/en/ (API: " + API + ").\n"
        "Fetched by whitepaper/food_data_analysis/snut_analysis/fetch_pvgis.py. "
        "Files are the unmodified JSON responses.\n\n"
        "| File stem | Radiation DB used | Query |\n|---|---|---|\n" + "\n".join(log) + "\n")


if __name__ == "__main__":
    sys.exit(main())
