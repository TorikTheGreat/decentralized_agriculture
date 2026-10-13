# snut_analysis: nutrition chapter, step 2 (analysis)

These scripts produce the numbers the nutrition chapter will rest on. All inputs live in `inputs.py`, each with its citation key and page/table locator, and were checked against the OCR text in `sources/ocr/`. These are results, not conclusions: the chapter text is drafted later (steps 3–4).

## Run

```
cd whitepaper/food_data_analysis/snut_analysis
../.venv/bin/python a1_area_energy.py      # calories only: area, electricity, PV land
../.venv/bin/python a2_nutrient_area_lp.py # open-field nutrient-area LP + Baldi contrast
../.venv/bin/python a2b_ce_lp.py           # same LP on measured CE yields (5 crops)
../.venv/bin/python fetch_pvgis.py         # PVGIS 5.3 API -> sources/pvgis_<date>/raw (network)
../.venv/bin/python a4_pv_land.py          # PV land per person at CR regional points and 52N
../.venv/bin/python a3_verify.py           # independent re-computation; exit 1 on failure
```

The scripts need `../food_data.duckdb` (built by `../build_db.py`), `../playground/results_caloric_yield.csv` and `scipy`.

## Results as of 2026-10-12 (all reproduced by `a3_verify.py`)

### A1: calories only

Controlled-environment (CE) figures are per m² of growing area under continuous cropping. Field figures assume one harvest per year.

| Dataset | kcal/m²/d | × field (world avg) | × field (top country) | m²/person at 2,100 / 2,400 / 2,800 kcal |
|---|---|---|---|---|
| wheeler2008crop potato (42.2 mol/d) | 68.3 | 14.5 | 6.6 | 31 / 35 / 41 |
| wheeler2008crop wheat (67 mol/d) | 42.5 | 12.8 | 4.6 | 49 / 56 / 66 |
| wheeler2008crop soybean | 29.3 | 9.1 | 7.2 | 72 / 82 / 96 |
| wheeler2006potato best (52.4 mol/d) | 141.0 | 30.0 | 13.6 | 15 / 17 / 20 |
| bugbee1988limits wheat record (150 mol/d) | 225.8 | 67.8 | 24.2 | 9 / 11 / 12 |
| Open field, FAOSTAT 2022 world average: potato / maize / wheat | 4.7 / 5.7 / 3.3 | 1 | | potato 446 / 510 / 595; maize 371 / 424 / 494 |

**What the multipliers depend on.** The ratio to field yields ranges from about 5× to about 70×, depending on:
- **the crop and study.** The highest values are single best studies or 0.2 m² plots, where edge effects are possible (wheeler1996bpc p.220).
- **the baseline**: the world-average field yield or the top national yield.
- **light.** Productivity rises with light, but radiation use efficiency falls (wheeler2008crop p.711).

**Lamp electricity per person-year at 2,400 kcal/d** (lamps only):

| Crop | Best tested LED, 3.0 µmol/J | Achievable LED, 4.1 µmol/J |
|---|---|---|
| Potato (wheeler2008crop) | 50 MWh | 37 MWh |
| Wheat (wheeler2008crop) | 128 MWh | 94 MWh |

- Total plant-factory electricity is 1.08–1.19× the lamp figure, because lighting is 84–93% of it (graamans2018plant).
- At the HPS-era assumption it is about 150 MWh. As a cross-check, tibbitts1994potato's own lamp figure is 97 MWh/yr at 2,800 kcal.

**PV land to power the lamps, at 2,400 kcal/d.** These figures use van Delden's assumptions: 52°N, lighting only, HVAC excluded.

| Crop | Area range |
|---|---|
| Potato (wheeler2008crop) | 217–452 m² |
| Wheat (wheeler2008crop) | 554–1,152 m² |

That is about the same land as an open field: potato needs 232 m² at the top national yield and 510 m² at the world average. Stacking saves floor area, not total land, unless the electricity comes from a source that needs little land (Costa Rica: mostly hydro and geothermal). These a1 figures use van Delden's own irradiation (3,200 MJ/m²/yr). For Costa Rica, see A4.

### A4: PV land at the Costa Rica regional points (PVGIS 5.3)

Lighting only, 2,400 kcal/d, wheeler2008crop yields. Regional points are city centres, not the test site. Method A applies van Delden's chain (20% PV efficiency, 75% land packing, no system losses) to PVGIS horizontal irradiation. Method B uses PVGIS system yield (optimal tilt, 14% loss, temperature model) and the same packing.

| Site (PVGIS database) | GHI kWh/m²/yr | E_y kWh/kWp/yr | Potato @4.1 µmol/J, A / B | 5-crop LP @4.1, A / B |
|---|---|---|---|---|
| CR highland, San José (ERA5) | 1,692 | 1,338 | 144 / 183 m² | 155–160 / 197–203 m² |
| CR Pacific lowland, Liberia (ERA5) | 1,795 | 1,384 | 136 / 177 m² | 146–151 / 190–196 m² |
| CR Caribbean lowland, Limón (ERA5) | 1,726 | 1,313 | 142 / 186 m² | 152–157 / 200–207 m² |
| 52°N Wageningen (SARAH3) | 1,090 | 1,028 | 224 / 238 m² | 241–249 / 256–264 m² |

- Costa Rica receives 1.55–1.65× the horizontal irradiation of 52°N, but the PV system yield is only 1.22–1.35× higher. PVGIS's temperature losses and the gain from tilting at 52°N narrow the gap. The real advantage is therefore smaller than the irradiation ratio suggests.
- PVGIS gives 3,924 MJ/m²/yr of horizontal irradiation at Wageningen, against van Delden's 3,200. Their figure is about 18% lower, and the source doesn't state where it comes from. That is why the a1 52°N land figures are higher than method A here.
- The PV land for potato calories in Costa Rica (136–186 m²) is below the top-national open-field potato figure (232 m²). It is not far below it, and still needs land.
- **Caveats:**
  - ERA5 is a coarse reanalysis and is the only database PVGIS offers for Central America; mountainous terrain makes it less reliable. A cross-check against IMN ground data or the Global Solar Atlas is pending.
  - The 75% land packing is van Delden's assumption, not verified for tilted rows.
  - HVAC is excluded, and in the tropics that is the cooling and dehumidification load.

### A2: minimum open-field area to meet energy, protein and the FAO/WHO 2004 RNIs (linear program)

**Base case** (iron at 10% bioavailability, zinc at moderate bioavailability, vitamin A at RE 1:6):
- 443 / 494 / 562 m²/person at 2,100 / 2,400 / 2,800 kcal, the same for women and men.
- The binding constraints are energy, pantothenate and calcium.
- The solution uses maize, carrots and spinach.

**Sensitivity runs:**

| Scenario | m²/person | Note |
|---|---|---|
| Iron at 5% bioavailability, women | 543 | iron becomes binding |
| Iron at 15%, zinc low, or vitamin A at 1:14 | no change | |
| Top national yields | 237 | |
| No crop above 25% of energy | 538–542 | |

- **FAO/WHO upper limits including Mg 350 mg/day: INFEASIBLE.** Section 11.6 (p.225) first calls dietary Mg "relatively innocuous" and then gives 350 mg/day "from foods and drinking water". Applying that limit to food is a literal reading the same passage undercuts. With all other upper limits applied, the result is unchanged at 494 m².
- **Not constrained, and reported instead:** B12 (cannot come from plants), vitamin D (made by the skin at latitudes inside 42°), iodine and selenium (depend on the soil or growing medium), and biotin (no USDA data).

### A2b: the same linear program on measured CE yields (wheeler2008crop, 5 crops)

- 41.6–51.5 m²/person, mostly potato, with lettuce and tomato.
- Binding constraints: energy, vitamin E and calcium.
- Light needed: about 1,400–1,900 mol/day, i.e. lamps of 57–77 MWh/yr at 2.5 µmol/J and 35–47 MWh/yr at 4.1.
- Benchmark: masuda2005ceef found 64.8 m²/person with more crops, more nutrient limits (minimum and maximum) and a Japanese RDA.

### Baldi contrast

baldi2024garden's 50 m² plot (30 m² cultivated; yields estimated from Italian averages, not measured) supplies the following share of one adult's needs per year:

| Nutrient | Share (women / men) |
|---|---|
| Energy | 2% |
| Protein | 4–5% |
| Vitamin C | 97% |
| Vitamin A | 50% / 41% |
| Vitamin K | 63% / 53% |
| Calcium | 3% |
| Iron | 3% / 6% |

The shares are against FAO/WHO RNIs, with USDA composition data.
- **Why these differ from Baldi's own figures** (vitamin C 59–73%, vitamin A 20–24%): Baldi used Italian SINU 2014 reference values for people over 75 (vitamin C 105/85 mg) and the Italian CREA composition tables.
- **The comparison shows the mismatch in scope.** A vegetable garden's 50 m² covers micronutrients like vitamin C but almost none of the energy. Energy sets the area: about 500 m² in open field, about 45 m² under heavy artificial light.

## Assumptions and limits, carried into the chapter

- **Field yields** are FAOSTAT 2022 national or world averages, one harvest per year. In the tropics, several vegetable cycles per year are possible, so field area is overstated for short-cycle crops.
- **CE yields** come from NASA chamber studies at 1,000–1,200 ppm CO₂, on hydroponic stacked shelves (wheeler2008crop). The chamber floor area was not reported.
- **Converting dry to fresh mass** uses USDA moisture. We assume the chamber's oven-dry mass is close to USDA dry matter; the potato check reproduces Tibbitts's and Wheeler's 3.7 kcal/g.
- **Conversion factors** in `../playground/compute_caloric_yield.py` are still partly unsourced. They affect rice, groundnut, sunflower and nuts, none of which appear in any solution. The "clean-basis crops only" run gives the same result.
- **The linear program is a minimum, not a diet.** It ignores losses, seed, rotation, paths, cooking losses, acceptability and protein quality. The protein requirement assumes PD-CAAS 1.0 (efsa2017drv p.19).
- **Niacin** counts preformed niacin only (no tryptophan), which is conservative. Folate is USDA total folate, which equals food folate for plants.
- **USDA composition data** describe US-grown produce. Selenium and iodine depend on the soil or growing medium.
- **Requirements** are FAO/WHO 2004 RNIs, which are population recommendations. Vitamin A is a "safe intake", and vitamin E is a "best estimate".
