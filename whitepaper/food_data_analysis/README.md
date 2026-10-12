# food_data_analysis

Data-science support for the nutrition section: deriving **caloric yield per unit area**
(and, later, micronutrient coverage per area) from primary datasets, rather than citing
secondary figures.

## Sources
- **FAOSTAT** — Crops & livestock products (QCL): crop **yield**. CC BY 4.0 + FAO
  non-commercial terms.
- **USDA FoodData Central** (SR Legacy 2018, Foundation Foods): **energy + full nutrient
  densities**. US-Gov public domain.

The raw data is **not committed** (git-ignored). Fetch it from the primary sources and
verify against the checksums in `data/PROVENANCE.md`. FAOSTAT is a living dataset, so a
later download may differ; a replication on fresher data producing updated figures is a
welcome contribution.

## Rebuild the database
```
.venv/bin/python build_db.py      # -> food_data.duckdb (git-ignored build artifact)
```
Loads every source CSV into a DuckDB file, namespaced by schema:
- `faostat.*`   — `all_data_normalized` (4.2M rows: Area, Item, Element, Year, Value) + code lookups (`areacodes`, `elements`, `itemcodes`, `flags`)
- `usda_sr.*`   — SR Legacy tables (`food`, `food_nutrient`, `nutrient`, `food_portion`, …)
- `usda_ff.*`   — Foundation Foods tables

## Query it
```python
import duckdb
con = duckdb.connect("food_data.duckdb", read_only=True)
con.execute("SELECT Item, Value, Unit FROM faostat.all_data_normalized "
            "WHERE Area='World' AND Element='Yield' AND Year=2022 LIMIT 5").fetchall()
```
Energy join (USDA): `food` → `food_nutrient` → `nutrient` where `name='Energy'` and
`unit_name='KCAL'`, amounts per 100 g.

## Gotchas (verified while building)
- FAOSTAT yields are `kg/ha` (÷10,000 → kg/m²). `Element='Yield'` name is shared across
  crop groups, so filter by exact `Item`, not a substring (`%potato%` also catches sweet
  potato).
- USDA has many entries per crop (flesh vs skin vs prepared). Match the intended raw item
  explicitly. Apply the refuse fraction (`food_portion`) for *edible* calories.

## Analysis (nutrition section)
Canonical caloric/protein/fat-yield-per-area analysis lives in `playground/`:
- **Report:** `playground/nutrition_data_analysis.md` (findings, adversarial verification, caveats, TODOs)
- **Compute:** `playground/compute_caloric_yield.py` → `results_caloric_yield.csv`
- **Figures:** `playground/make_figures.py` → `figures/`
Run with the repo `.venv` (`../../../.venv`), which has duckdb + pandas + matplotlib.
Key caveat carried in the report: the ranking is **open-field** yield (baseline CEA is measured against),
NOT a CEA-system footprint.
