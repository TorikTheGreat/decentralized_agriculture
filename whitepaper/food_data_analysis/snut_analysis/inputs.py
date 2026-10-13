"""
Sourced inputs for the nutrition-chapter (SNUT) analyses.

Every constant carries the citation key (whitepaper/bibliography.bib or the
proposed key in sources/citation_map.md) and a locator. Values were checked
against the OCR text in sources/ocr/ on 2026-10-12. "ASSUMPTION" marks a
modelling choice of ours, not a sourced value.
"""

# ---------------------------------------------------------------------------
# Daily energy requirement scenarios (kcal/person/day)
# ---------------------------------------------------------------------------
# faowhounu2004energy Tables 5.4-5.9 (pp.41-46): PAL 1.75 adult examples span
# roughly 2,100-2,800 kcal/d. rockstrom2025eatlancet Table 1 title (p.1632):
# reference diet at ~2,400 kcal/d population-level intake.
KCAL_PER_DAY = {"low": 2100, "central": 2400, "high": 2800}

# ---------------------------------------------------------------------------
# Controlled-environment (CE) measured productivities, EDIBLE DRY MASS
# g m-2 d-1 per m2 of GROWING area (stacked shelves where stated), with the
# daily light integral (mol PAR m-2 d-1) at which they were obtained.
# ---------------------------------------------------------------------------
CE_DATA = [
    # key, crop, usda_desc, edible_DM_g_m2_d, mol_m2_d, source, locator, conditions
    dict(key="wheeler2008crop", crop="potato", usda="Potatoes, flesh and skin, raw",
         dm=18.4, mol=42.2, loc="Table 2 p.711",
         cond="Norland, NFT, 12 h (+extension tests), 1000-1200 ppm CO2, 4 stacked shelves"),
    dict(key="wheeler2008crop", crop="wheat", usda="Wheat, hard red winter",
         dm=11.3, mol=67.0, loc="Table 2 p.711",
         cond="Yecora Rojo, NFT, 20 h, 1000-1200 ppm CO2"),
    dict(key="wheeler2008crop", crop="soybean", usda="Soybeans, mature seeds, raw",
         dm=6.0, mol=36.5, loc="Table 2 p.711", cond="McCall, NFT, 12 h"),
    dict(key="wheeler2008crop", crop="tomato", usda="Tomatoes, red, ripe, raw, year round average",
         dm=9.8, mol=38.6, loc="Table 2 p.711",
         cond="cherry type cv Reimann Philipp; USDA red ripe tomato used for composition"),
    dict(key="wheeler2008crop", crop="lettuce", usda="Lettuce, green leaf, raw",
         dm=7.1, mol=16.8, loc="Table 2 p.711", cond="Waldmann's Green, 16 h"),
    dict(key="wheeler2006potato", crop="potato (best)", usda="Potatoes, flesh and skin, raw",
         dm=37.5, mol=52.4, loc="Table 1 p.83 (Wheeler rounds to 38 g for 141 kcal, p.84)",
         cond="Denali, 12 h then 24 h light, transplant-adjusted; single best study"),
    dict(key="bugbee1988limits", crop="wheat (record)", usda="Wheat, hard red winter",
         dm=60.0, mol=150.0, loc="Abstract; Results",
         cond="oven-dry grain, 79 d, 20 h at ~2080 umol, 1200 ppm, 0.2 m2 plots (edge effects possible)"),
]
# tibbitts1994potato Table 3.4 p.29 / p.30: 37.5 g DW tuber m-2 d-1 = 139 kcal m-2 d-1
# at 3.7 kcal/g; 20.1 m2/person at 2,800 kcal/d; lamps 11.1 kW continuous per person
# (p.30, OCR line ~7736). Used only as a cross-check (no single DLI: 12 h then 24 h).
TIBBITTS = dict(dm=37.5, kcal_m2_d=139, m2_person=20.1, kcal_d=2800, lamp_kW_person=11.1)

# ---------------------------------------------------------------------------
# Lighting electricity
# ---------------------------------------------------------------------------
# kusuma2020led: best tested fixtures 2.5-3.0 umol/J (p.8 "current typical values
# of 2-3"; Table 1); achievable white+red 3.4, blue+red 4.1 (Abstract, p.6);
# theoretical 20% blue/80% red ~5.2 (0.2*3.76 + 0.8*5.52, Fig. 2 caption p.3).
# wheeler2008crop pp.711-712: HPS-era assumption 20% wall-plug->PAR, i.e.
# 150 W m-2 PAR ~ 750 umol m-2 s-1 => ~1 umol/J electrical (kept for reference).
LED_EFFICACY_UMOL_PER_J = {
    "HPS-era (wheeler2008 assumption)": 1.0,
    "current good fixture (kusuma 2.5)": 2.5,
    "best tested (kusuma 3.0)": 3.0,
    "achievable white+red (kusuma 3.4)": 3.4,
    "protected blue+red (kusuma 4.1 less ~10% for water/humidity cover, Abstract p.1)": 3.7,
    "achievable blue+red (kusuma 4.1, unprotected, water-cooled)": 4.1,
    "theoretical B20:R80 (kusuma ~5.2)": 5.2,
}
# graamans2018plant Sec 4.1 p.37 / Fig. 5 p.38 (VISUAL reading by reader agent):
# lighting is ~84% (hot site, Bandar Abbas weather file) to ~93% (Sweden) of
# plant-factory electricity; rest is cooling/dehumidification.
LIGHTING_SHARE_OF_PF_ELECTRICITY = {"hot climate": 0.84, "cold climate": 0.93}

# ---------------------------------------------------------------------------
# PV land per lit area (lighting only)
# ---------------------------------------------------------------------------
# vandelden2021vf Fig. 4c and caption, p.952: 9 m2 of lit layers need 28.2 m2
# of land for the PV array; PPFD 250 umol m-2 s-1 x 16 h (= 14.4 mol m-2 d-1),
# LED 3.5 umol/J (projected), PV 20%, 75% land packing, 52 deg N, HVAC excluded.
VANDELDEN = dict(land_m2=28.2, lit_m2=9.0, mol_m2_d=14.4, led_umol_J=3.5, latitude="52N")

# ---------------------------------------------------------------------------
# Nutrient requirements: FAO/WHO 2004, adults 19-50 (faowho2004vitmin
# Annex 1 pp.338-339, Annex 2 pp.340-341; chapter tables as noted)
# Units per day. Values verified against OCR of Annex pages 357-360 (PDF).
# ---------------------------------------------------------------------------
RNI = {
    # nutrient: (female 19-50, male 19-50, unit, note)
    "vitA_RE":   (500, 600, "ug RE", "recommended SAFE intake, not RNI (Annex 2 fn e)"),
    "vitE":      (7.5, 10.0, "mg a-TE", "best estimate, not RNI (Annex 2 fn g)"),
    "vitK":      (55, 65, "ug", "Table 6.4 p.123"),
    "vitC":      (45, 45, "mg", "Table 7.1 p.138"),
    "thiamin":   (1.1, 1.2, "mg", "Table 9.2 p.168"),
    "riboflavin":(1.1, 1.3, "mg", "Table 9.3 p.172"),
    "niacin":    (14, 16, "mg NE", "Table 9.4 p.176; we count PREFORMED niacin only (conservative)"),
    "vitB6":     (1.3, 1.3, "mg", "Table 9.5 p.179"),
    "pantothenate": (5.0, 5.0, "mg", "Table 9.6 p.182; adequate-intake basis"),
    "folate":    (400, 400, "ug DFE", "Table 15.1 p.296; food folate = DFE"),
    "calcium":   (1000, 1000, "mg", "Table 4.2 p.71 (Western diets); Table 4.4 p.83 gives 750 at 20-40 g animal protein"),
    "magnesium": (220, 260, "mg", "Table 11.2 p.224; provisional"),
    "zinc_moderate": (4.9, 7.0, "mg", "Table 12.4 p.240, moderate bioavailability"),
    "zinc_low":  (9.8, 14.0, "mg", "Table 12.4 p.240, low bioavailability"),
    "iron_15":   (19.6, 9.1, "mg", "Table 13.5 p.271, 15% bioavailability"),
    "iron_10":   (29.4, 13.7, "mg", "Table 13.5 p.271, 10% bioavailability"),
    "iron_5":    (58.8, 27.4, "mg", "Table 13.5 p.271, 5% bioavailability"),
}
# Excluded from the plant-only LP, with reasons (reported, not hidden):
EXCLUDED = {
    "vitB12": "cannot be supplied by plants: 'no species of plants have the enzymes necessary' (faowho2004vitmin p.279)",
    "vitD": "main route is skin synthesis between 42N and 42S (faowho2004vitmin p.53); Costa Rica inside band; plant food data absent (p.51). Masuda 2005 also excluded it",
    "iodine": "plant content depends on soil / growth medium (faowho2004vitmin p.305); USDA plant iodine data sparse",
    "selenium": "plant content depends on soil / growth medium (faowho2004vitmin pp.200-201); USDA values reflect US soils (reported, not constrained)",
    "biotin": "USDA SR has no biotin values for these foods",
}
# Upper limits stated in faowho2004vitmin (adult), used only in the 'UL' scenario:
UL = {"vitC": 1000, "calcium": 3000, "zinc": 45, "magnesium": 350}
# NOTE Mg: Sec 11.6 p.225 first says "Magnesium from dietary sources is relatively
# innocuous", then suggests 350 mg/day "from foods and drinking water" as tolerable.
# Applying it to food Mg is a literal reading the same passage undercuts; reported as a
# sensitivity only.
# Mg 350 mg/day "from foods and drinking water" (p.225); vit C 1 g (p.139);
# Ca 3 g (p.74); Zn 45 mg adult man (p.241).

# Vitamin A conversion (faowho2004vitmin): RE system 1:6 beta-carotene, 1:12 other
# provitamin A carotenoids (Annex 2 fn f p.340; retained p.29). Alternative 1:14 / 1:28
# "recommended" on p.26 (Van het Hof). Both scenarios are run.
VITA_FACTORS = {"RE 1:6/1:12 (Annex)": (1/6, 1/12), "1:14/1:28 (p.26)": (1/14, 1/28)}

# Protein: FAO/WHO 2004 does not cover protein. efsa2017drv Sec 3.4 p.19 / Table 3
# p.24: PRI 0.83 g/kg bw/d (assumes PD-CAAS 1.0); reference body weights 58.5 kg
# (women), 68.1 kg (men) (Table 17 p.91).
PROTEIN_G_PER_DAY = {"F": 0.83 * 58.5, "M": 0.83 * 68.1}

# ---------------------------------------------------------------------------
# Comparison benchmarks (not inputs to our computation)
# ---------------------------------------------------------------------------
# masuda2005ceef p.62-65 (OCR lines 14, 211-227): LP minimum area 129.14 m2 for 2
# people (64.8 m2/crew member excl. seedlings, 74.5 incl. 15% seedlings), 18 nutrients,
# 2,250 kcal/d sedentary male 30-39 (Japanese RDA 6th rev.), light 46.3 or 28.3
# mol m-2 d-1; B12 and D excluded. Cites Waters 2002: 75.3 m2/person (LP);
# Salisbury 2002: 111.3 m2/person at 50 mol m-2 d-1.
BENCHMARKS_M2_PER_PERSON = {
    "Masuda 2005 (LP, CEEF, 18 nutrients)": 64.8,
    "Waters 2002 via Masuda (LP)": 75.3,
    "Salisbury 2002 via Masuda (50 mol)": 111.3,
    "Tibbitts 1994 (potato, energy only, 2800 kcal)": 20.1,
    "Wheeler 2006 (potato, energy only, 2500 kcal)": 17.8,
}
# baldi2024garden Fig. 4 (p.7), per 50 m2 plot (30 m2 cultivated): crop area m2 and
# estimated yield kg/plot/yr (area x ISTAT Italian average yield; NOT measured, pp.2-3).
BALDI_PLOT = [
    # crop, area_m2, kg_per_yr, usda description
    ("tomato", 24.3, 76.5, "Tomatoes, red, ripe, raw, year round average"),
    ("sweet pepper", 1.07, 2.39, "Peppers, sweet, red, raw"),
    ("lettuce", 0.91, 2.01, "Lettuce, green leaf, raw"),
    ("eggplant", 0.56, 1.60, "Eggplant, raw"),
    ("zucchini", 0.5, 1.25, "Squash, summer, zucchini, includes skin, raw"),
    ("onion", 0.33, 1.10, "Onions, raw"),
    ("potato", 0.30, 0.94, "Potatoes, flesh and skin, raw"),
    ("cauliflower+broccoli", 0.28, 0.68, "Broccoli, raw"),
    ("cucumber", 0.39, 0.57, "Cucumber, with peel, raw"),
    ("celery", 0.16, 0.54, "Celery, raw"),
    ("black cabbage", 0.18, 0.50, "Kale, raw"),
    ("green bean", 0.43, 0.37, "Beans, snap, green, raw"),
    ("hot pepper", 0.13, 0.29, "Peppers, hot chili, red, raw"),
    ("garlic", 0.15, 0.13, "Garlic, raw"),
    ("parsley", 0.02, 0.04, "Parsley, fresh"),
]
# 'minor species' (0.27 m2, 0.82 kg) omitted: mixed, no single composition.
