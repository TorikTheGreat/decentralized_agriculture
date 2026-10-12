-- Example queries against food_data.duckdb  (build with: ../build_db.py)
-- Every table is namespaced by its source SCHEMA. You must qualify the name
-- because tables repeat across schemas (usda_sr.food AND usda_ff.food exist).
--   faostat.*  -> FAOSTAT QCL: all_data_normalized (+ areacodes, elements, itemcodes, flags)
--   usda_sr.*  -> USDA FoodData Central, SR Legacy (2018)
--   usda_ff.*  -> USDA FoodData Central, Foundation Foods

-- ── Simple single-table references ───────────────────────────────────────────

-- FAOSTAT main table (Area, Item, Element, Year, Unit, Value, ...)
SELECT Area, Item, Element, Year, Unit, Value
FROM faostat.all_data_normalized
WHERE Area = 'World' AND Element = 'Yield' AND Year = 2022
LIMIT 10;

-- FAOSTAT lookup table (to see exact Item names for the crosswalk)
SELECT * FROM faostat.itemcodes WHERE Item ILIKE '%potato%';

-- USDA foods (find the exact description string for a crop)
SELECT fdc_id, description FROM usda_sr.food WHERE description ILIKE '%peanut%';

-- USDA energy join: food -> food_nutrient -> nutrient (kcal per 100 g)
SELECT f.description, fn.amount AS kcal_per_100g
FROM usda_sr.food f
JOIN usda_sr.food_nutrient fn ON f.fdc_id = fn.fdc_id
JOIN usda_sr.nutrient      n  ON fn.nutrient_id = n.id
WHERE n.name = 'Energy' AND n.unit_name = 'KCAL'
  AND f.description ILIKE 'potatoes, raw%';

-- ── Fuller example: caloric yield per m²/yr (crosswalk join) ──────────────────
-- kcal/m²/yr = FAOSTAT yield (kg/m²) × USDA energy density (kcal/kg).
-- NOTE: the item names and USDA descriptions below are ILLUSTRATIVE — verify
-- each against faostat.itemcodes and usda_sr.food before trusting numbers
-- (e.g. '%potato%' matches both Potatoes and Sweet potatoes; USDA has many
-- potato entries: flesh vs skin vs prepared).
WITH crosswalk(faostat_item, usda_desc) AS (
    VALUES
      ('Potatoes',                     'Potatoes, raw, flesh and skin'),
      ('Sweet potatoes',               'Sweet potato, raw, unprepared'),
      ('Wheat',                        'Wheat, hard red winter'),
      ('Soya beans',                   'Soybeans, mature seeds, raw'),
      ('Groundnuts, excluding shelled','Peanuts, all types, raw')
),
yield_m2 AS (                       -- FAOSTAT: kg/ha -> kg/m²
    SELECT Item, Value / 10000.0 AS kg_per_m2
    FROM faostat.all_data_normalized
    WHERE Area = 'World' AND Element = 'Yield' AND Year = 2022
),
energy AS (                         -- USDA: kcal/100 g -> kcal/kg (one row per food)
    SELECT f.description, MIN(fn.amount) * 10.0 AS kcal_per_kg
    FROM usda_sr.food f
    JOIN usda_sr.food_nutrient fn ON f.fdc_id = fn.fdc_id
    JOIN usda_sr.nutrient      n  ON fn.nutrient_id = n.id
    WHERE n.name = 'Energy' AND n.unit_name = 'KCAL'
    GROUP BY f.description
)
SELECT c.faostat_item                        AS crop,
       round(y.kg_per_m2, 2)                 AS kg_per_m2_yr,
       round(e.kcal_per_kg)                  AS kcal_per_kg,
       round(y.kg_per_m2 * e.kcal_per_kg)    AS kcal_per_m2_yr
FROM crosswalk c
JOIN yield_m2 y ON y.Item = c.faostat_item
JOIN energy   e ON e.description = c.usda_desc
ORDER BY kcal_per_m2_yr DESC;
