# Data provenance and licensing

Downloaded **2026-07-07** for the caloric-yield-per-area derivation in the nutrition section.

The raw data is intentionally **not committed to the repo** (git-ignored). Fetch it
from the primary sources below and run `build_db.py` to rebuild `food_data.duckdb`.
Note FAOSTAT is a *living* dataset (back-series get revised), so a later download
may differ from ours; the SHA-256 checksums below identify the exact bytes we used.
A replication run on fresher data producing updated figures is a welcome contribution.

## SHA-256 checksums (downloaded ZIPs, accessed 2026-07-07)
```
c5835418c18f9322e7decbd6800f93a216eaae3cdfa31acb08f0518c0c6d6853  Production_Crops_Livestock_E_All_Data_(Normalized).zip
b80817294b8850530aaedf2e515c02593b1824f763a0ff356e5c2081643e6fd0  FoodData_Central_sr_legacy_food_csv_2018-04.zip
d6d4f41dcd19a46abcdd67775379cb6f0292ff08daa7e0680fdd0982830bf57b  FoodData_Central_foundation_food_csv_2026-04-30.zip
```

## FAOSTAT — Crops and livestock products (QCL)
- File: `faostat_crops_livestock/Production_Crops_Livestock_E_All_Data_(Normalized).zip`
- Source: <https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip>
- Portal / schema: <https://www.fao.org/faostat/en/#data/QCL>
- Dataset last updated by FAO: 2025-12-31 (→ citation year 2025)
- **Licence: CC BY 4.0**, with FAO Database Terms of Use additions.

**Required attribution (verbatim structure mandated by FAO):**
> FAO. 2025. FAOSTAT: Crops and livestock products (QCL). Accessed on 7 July 2026. https://www.fao.org/faostat/en/#data/QCL. Licence: CC-BY-4.0.

**Use constraints (FAO db terms):**
- Non-commercial: datasets must not be used for or in conjunction with the promotion of a commercial enterprise or its products/services. Our academic, non-commercial whitepaper use is within terms.
- Embedded third-party data within FAOSTAT may not be redistributed without the original provider's consent.
- CONSEQUENCE for the project's open data commons: FAOSTAT-derived values CANNOT be folded into a maximally permissive, commercial-friendly commons. Cite/derive summary figures only; keep separate from the project's own permissively-licensed generated data.

## USDA FoodData Central
- Files: `usda_legacy_foods/FoodData_Central_sr_legacy_food_csv_2018-04.zip` (SR Legacy, 2018),
  `usda_foundation_foods/FoodData_Central_foundation_food_csv_2026-04-30.zip` (Foundation Foods),
  `usda_definitions/` (field descriptions / schema)
- Source: <https://fdc.nal.usda.gov/download-datasets/>
- **Licence: Public domain** (work of the U.S. federal government). No attribution obligation, no commercial or redistribution restriction. SR Legacy is the primary energy-density source; Foundation Foods used for cross-checking.

## Note
This directory holds externally-licensed reference data with mixed rights (FAOSTAT non-commercial vs USDA public domain). Any derived dataset the project publishes must keep the FAOSTAT-derived portion's restrictions straight and separate from the project's own openly-licensed data.
