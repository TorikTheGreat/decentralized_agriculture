#!/usr/bin/env python3
"""
Compute caloric (and protein/fat) yield per m2/yr for candidate crops, by joining
FAOSTAT crop yields (fresh field weight) to USDA SR Legacy nutrient densities.

  kcal/m2/yr = FAOSTAT_yield(kg/ha) * conv_factor * USDA_kcal(per100g) / 1000
  (same formula for protein g/m2/yr and fat g/m2/yr using their g/100g)

conv_factor bridges the BASIS MISMATCH between FAOSTAT (whole primary crop) and the
USDA food entry (often a milled/shelled/extracted fraction). Factors are standard
commodity extraction / edible-portion estimates and are FLAGGED for verification.

Reproducible: reads ../food_data.duckdb (build with ../build_db.py). Writes
results_caloric_yield.csv next to this script. Year fixed to 2022.
"""
from pathlib import Path
import duckdb, csv

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "food_data.duckdb"
YEAR = 2022
AREA_MIN_HA = 50_000   # min harvested area to count a country in the "top-yield" ceiling

# faostat_item (EXACT), usda_pattern, usda_cats, basis, conv_factor, rationale
CROSSWALK = [
 # ---- CLEAN basis (whole crop ~ USDA raw): conv 1.0 ----
 ("Potatoes","Potatoes, flesh and skin, raw",[11],"clean",1.0,""),
 ("Sweet potatoes","Sweet potato, raw, unprepared%",[11],"clean",1.0,""),
 ("Cassava, fresh","Cassava, raw",[11],"clean",1.0,""),
 ("Yams","Yam, raw",[11],"clean",1.0,""),
 ("Taro","Taro, raw",[11],"clean",1.0,""),
 ("Maize (corn)","Corn grain, yellow",[20],"clean",1.0,""),
 ("Wheat","Wheat, hard red winter",[20],"clean",1.0,"bread wheat (durum overstates protein)"),
 ("Sorghum","Sorghum grain",[20],"clean",1.0,""),
 ("Barley","Barley, hulled",[20],"clean-ish",0.80,"grain incl. hull -> hulled ~0.80"),
 ("Oats","Oats (Includes%",[20],"clean-ish",0.75,"grain incl. hull -> groat ~0.75"),
 ("Rye","Rye grain",[20],"clean",1.0,""),
 ("Millet","Millet, raw",[20],"clean",1.0,""),
 ("Quinoa","Quinoa, uncooked",[20],"clean",1.0,""),
 ("Buckwheat","Buckwheat",[20],"clean",1.0,""),
 ("Beans, dry","Beans, kidney, all types, mature seeds, raw",[16],"clean",1.0,""),
 ("Chick peas, dry","Chickpeas%mature seeds, raw",[16],"clean",1.0,""),
 ("Lentils, dry","Lentils, raw",[16],"clean",1.0,""),
 ("Soya beans","Soybeans, mature seeds, raw",[16],"clean",1.0,""),
 ("Cow peas, dry","Cowpeas, catjang, mature seeds, raw",[16],"clean",1.0,""),
 ("Pigeon peas, dry","Pigeon peas%mature seeds, raw",[16],"clean",1.0,""),
 ("Sesame seed","Seeds, sesame seeds, whole, dried",[12],"clean",1.0,"eaten whole"),
 ("Linseed","Seeds, flaxseed",[12],"clean",1.0,"eaten whole"),
 # fresh veg / fruit (minor peel refuse; treat clean)
 ("Tomatoes","Tomatoes, red, ripe, raw, year round average",[11],"clean",1.0,""),
 ("Cucumbers and gherkins","Cucumber, with peel, raw",[11],"clean",1.0,""),
 ("Lettuce and chicory","Lettuce, cos or romaine, raw",[11],"clean",1.0,""),
 ("Cabbages","Cabbage, raw",[11],"clean",1.0,""),
 ("Spinach","Spinach, raw",[11],"clean",1.0,""),
 ("Carrots and turnips","Carrots, raw",[11],"clean",1.0,""),
 ("Cauliflowers and broccoli","Broccoli, raw",[11],"clean",1.0,""),
 ("Onions and shallots, dry (excluding dehydrated)","Onions, raw",[11],"clean",1.0,""),
 ("Apples","Apples, raw, with skin%",[9],"clean",1.0,""),
 ("Oranges","Oranges, raw, all commercial varieties",[9],"clean",0.75,"peel ~25% refuse"),
 ("Watermelons","Watermelon, raw",[9],"clean",0.52,"rind ~48% refuse"),
 ("Grapes","Grapes, red or green%",[9],"clean",1.0,""),
 ("Avocados","Avocados, raw, all commercial varieties",[9],"clean",0.73,"skin+pit ~27%"),
 ("Mangoes, guavas and mangosteens","Mangos, raw",[9],"clean",0.68,"skin+stone ~32%"),
 # ---- BASIS-ADJUSTED (flagged) ----
 ("Rice","Rice, white, long-grain, regular, raw, unenriched%",[20],"adjusted",0.67,"paddy->milled ~0.67"),
 ("Bananas","Bananas, raw",[9],"adjusted",0.65,"peel removed ~0.65"),
 ("Plantains and cooking bananas","Plantains, green, raw",[9],"adjusted",0.65,"peel removed ~0.65"),
 ("Groundnuts, excluding shelled","Peanuts, virginia, raw%",[16],"adjusted",0.70,"in-shell->kernel ~0.70"),
 ("Sunflower seed","Seeds, sunflower seed kernels, dried",[12],"adjusted",0.55,"seed->dehulled kernel ~0.55"),
 ("Almonds, in shell","Nuts, almonds",[12],"adjusted",0.45,"in-shell->kernel ~0.45"),
 ("Walnuts, in shell","Nuts, walnuts, english",[12],"adjusted",0.45,"in-shell->kernel ~0.45"),
 ("Hazelnuts, in shell","Nuts, hazelnuts or filberts",[12],"adjusted",0.45,"in-shell->kernel ~0.45"),
 ("Cashew nuts, in shell","Nuts, cashew nuts, raw",[12],"adjusted",0.25,"in-shell->kernel ~0.25"),
 ("Coconuts, in shell","Nuts, coconut meat, raw",[12],"adjusted",0.35,"whole->meat ~0.35"),
 # ---- INDUSTRIAL (not a dietary staple / not CEA; flag) ----
 ("Sugar cane","Sugars, granulated%",[19],"industrial",0.12,"cane->sugar ~12% (extracted)"),
 ("Sugar beet","Sugars, granulated%",[19],"industrial",0.16,"beet->sugar ~16% (extracted)"),
 ("Oil palm fruit","Oil, palm",[4],"industrial",0.22,"fruit->palm oil ~22% (extracted)"),
]

def main():
    con = duckdb.connect(str(DB), read_only=True)

    def usda(pattern, cats):
        catf = f"AND f.food_category_id IN ({','.join(map(str,cats))})"
        return con.execute(f"""
          SELECT f.fdc_id, f.description,
            max(CASE WHEN fn.nutrient_id=1008 THEN fn.amount END) kcal,
            max(CASE WHEN fn.nutrient_id=1003 THEN fn.amount END) prot,
            max(CASE WHEN fn.nutrient_id=1004 THEN fn.amount END) fat
          FROM usda_sr.food f JOIN usda_sr.food_nutrient fn ON fn.fdc_id=f.fdc_id
          WHERE f.description ILIKE '{pattern.replace("'","''")}' {catf}
          GROUP BY 1,2 ORDER BY length(f.description) LIMIT 1
        """).fetchone()

    def world_yield(item):
        r = con.execute("""SELECT Value FROM faostat.all_data_normalized
            WHERE Area='World' AND Item=? AND Element='Yield' AND Unit='kg/ha' AND Year=?""",
            [item, YEAR]).fetchone()
        return r[0] if r else None

    def top_yield(item):
        # best national yield among countries harvesting > AREA_MIN_HA (exclude aggregates: Area Code < 5000)
        r = con.execute("""
          WITH y AS (SELECT "Area Code" ac, Area, Value v FROM faostat.all_data_normalized
                     WHERE Item=? AND Element='Yield' AND Unit='kg/ha' AND Year=? AND "Area Code" < 5000),
               a AS (SELECT "Area Code" ac, Value ha FROM faostat.all_data_normalized
                     WHERE Item=? AND Element='Area harvested' AND Unit='ha' AND Year=? AND "Area Code" < 5000)
          SELECT y.Area, y.v FROM y JOIN a ON a.ac=y.ac
          WHERE a.ha > ? ORDER BY y.v DESC LIMIT 1
        """,[item,YEAR,item,YEAR,AREA_MIN_HA]).fetchone()
        return r if r else (None,None)

    rows=[]
    for item,pat,cats,basis,conv,rat in CROSSWALK:
        u = usda(pat,cats)
        if not u: print("USDA MISS:",item,pat); continue
        fdc,desc,kcal,prot,fat = u
        wy = world_yield(item)
        tcountry,ty = top_yield(item)
        if wy is None: print("FAOSTAT MISS:",item); continue
        def perm2(yield_kgha, per100):
            return yield_kgha*conv*(per100 or 0)/1000.0
        rows.append(dict(
            item=item, basis=basis, conv=conv, rationale=rat,
            usda=desc, fdc=fdc,
            kcal_100g=kcal, prot_100g=prot, fat_100g=fat,
            world_yield_kgha=round(wy),
            world_kcal_m2=round(perm2(wy,kcal)),
            world_prot_g_m2=round(perm2(wy,prot),1),
            world_fat_g_m2=round(perm2(wy,fat),1),
            top_country=tcountry, top_yield_kgha=round(ty) if ty else None,
            top_kcal_m2=round(perm2(ty,kcal)) if ty else None,
        ))
    con.close()

    rows.sort(key=lambda r:-(r["world_kcal_m2"] or 0))
    # write CSV
    out = HERE/"results_caloric_yield.csv"
    with open(out,"w",newline="") as fh:
        w=csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    # print ranked
    print(f"\nCaloric yield per m2/yr, World {YEAR} (ranked). conv applied for basis.\n")
    print(f"{'crop':<34}{'basis':<11}{'kcal/kg':>8}{'kcal/m2':>9}{'prot g/m2':>10}{'fat g/m2':>9}{'top kcal/m2':>12}")
    for r in rows:
        print(f"{r['item'][:33]:<34}{r['basis']:<11}{(r['kcal_100g'] or 0)*10:>8.0f}"
              f"{r['world_kcal_m2']:>9}{r['world_prot_g_m2']:>10}{r['world_fat_g_m2']:>9}"
              f"{(r['top_kcal_m2'] or 0):>12}")
    print(f"\nwrote {out.name} ({len(rows)} crops)")

if __name__=="__main__":
    main()
