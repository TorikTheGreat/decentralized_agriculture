#!/usr/bin/env python3
"""Figures for the caloric-yield analysis. Reads results_caloric_yield.csv,
writes PNGs to figures/. Palette: Okabe-Ito (colorblind-safe); industrial crops
hatched as secondary encoding so identity is never colour-alone."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"; FIG.mkdir(exist_ok=True)

# Okabe-Ito
BLUE, ORANGE, GRAY = "#0072B2", "#E69F00", "#7F7F7F"
BASIS_COLOR = {"clean": BLUE, "clean-ish": BLUE, "adjusted": ORANGE, "industrial": GRAY}
BASIS_HATCH = {"industrial": "///"}

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": "#888", "axes.linewidth": 0.6,
    "axes.grid": True, "grid.color": "#E6E6E6", "grid.linewidth": 0.6,
    "axes.axisbelow": True, "figure.dpi": 130, "savefig.dpi": 130,
    "axes.spines.top": False, "axes.spines.right": False,
})

rows = list(csv.DictReader(open(HERE / "results_caloric_yield.csv")))
for r in rows:
    for k in ("kcal_100g","world_kcal_m2","world_prot_g_m2","world_fat_g_m2","top_kcal_m2","conv"):
        r[k] = float(r[k]) if r[k] not in ("", "None", None) else 0.0

# ── Fig 1: caloric yield per area, ranked ────────────────────────────────────
d = sorted(rows, key=lambda r: r["world_kcal_m2"], reverse=True)
names = [r["item"].replace(", excluding shelled","").replace(" and gherkins","")
          .replace("Onions and shallots, dry (excluding dehydrated)","Onions")[:26] for r in d]
vals  = [r["world_kcal_m2"] for r in d]
cols  = [BASIS_COLOR[r["basis"]] for r in d]
hatch = [BASIS_HATCH.get(r["basis"]) for r in d]
fig, ax = plt.subplots(figsize=(7.6, 10))
y = range(len(d))
bars = ax.barh(list(y), vals, color=cols, height=0.72, edgecolor="white", linewidth=0.5)
for b, h in zip(bars, hatch):
    if h: b.set_hatch(h)
ax.set_yticks(list(y)); ax.set_yticklabels(names, fontsize=7.6)
ax.invert_yaxis()
for yi, v in zip(y, vals):
    ax.text(v + 30, yi, f"{v:,.0f}", va="center", fontsize=6.8, color="#333")
ax.set_xlabel("Caloric yield  (kcal · m⁻² · yr⁻¹, World 2022)")
ax.set_title("Caloric yield per unit area, by crop", fontsize=11, weight="bold", pad=10)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(facecolor=BLUE, label="edible staple (clean basis)"),
                   Patch(facecolor=ORANGE, label="basis-adjusted (milled/shelled/peeled)"),
                   Patch(facecolor=GRAY, hatch="///", label="industrial (extracted; not a food staple)")],
          loc="lower right", fontsize=7.6, frameon=False)
ax.margins(y=0.005)
fig.tight_layout(); fig.savefig(FIG/"fig1_caloric_yield_ranking.png", bbox_inches="tight"); plt.close(fig)

# ── Fig 2: energy density (per kg) vs per-area yield — THE distinction ────────
fig, ax = plt.subplots(figsize=(7.8, 5.6))
for r in rows:
    ax.scatter(r["kcal_100g"]*10, r["world_kcal_m2"], s=42,
               color=BASIS_COLOR[r["basis"]],
               hatch=BASIS_HATCH.get(r["basis"]), edgecolor="white", linewidth=0.6, zorder=3)
label_these = {"Walnuts, in shell":"walnut","Soya beans":"soybean","Groundnuts, excluding shelled":"peanut",
    "Sunflower seed":"sunflower","Potatoes":"potato","Maize (corn)":"maize","Cassava, fresh":"cassava",
    "Sugar beet":"sugar beet","Oil palm fruit":"oil palm","Lettuce and chicory":"lettuce",
    "Almonds, in shell":"almond","Wheat":"wheat","Rice":"rice","Cashew nuts, in shell":"cashew"}
for r in rows:
    if r["item"] in label_these:
        ax.annotate(label_these[r["item"]], (r["kcal_100g"]*10, r["world_kcal_m2"]),
                    xytext=(5,3), textcoords="offset points", fontsize=7, color="#333")
ax.set_xlabel("Energy density  (kcal · kg⁻¹ of the edible food)")
ax.set_ylabel("Caloric yield per area  (kcal · m⁻² · yr⁻¹)")
ax.set_title("Energy density ≠ caloric yield per area", fontsize=11, weight="bold", pad=8)
ax.text(0.98, 0.03, "high density, low area →  oilseeds & nuts\nhigh area →  tubers, cereals",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, color="#666")
fig.tight_layout(); fig.savefig(FIG/"fig2_density_vs_area.png", bbox_inches="tight"); plt.close(fig)

# ── Fig 3: protein & fat per area, key crops (one axis: grams) ────────────────
key = ["Soya beans","Groundnuts, excluding shelled","Oil palm fruit","Sunflower seed",
       "Maize (corn)","Wheat","Potatoes","Lentils, dry","Chick peas, dry","Spinach",
       "Cabbages","Avocados"]
kd = [next(r for r in rows if r["item"]==k) for k in key]
kd.sort(key=lambda r: r["world_prot_g_m2"]+r["world_fat_g_m2"], reverse=True)
labels = [r["item"].replace(", excluding shelled","").replace(", dry","")[:22] for r in kd]
prot = [r["world_prot_g_m2"] for r in kd]; fat = [r["world_fat_g_m2"] for r in kd]
fig, ax = plt.subplots(figsize=(7.6, 5.4))
yy = range(len(kd)); hh = 0.38
ax.barh([i+hh/2 for i in yy], prot, height=hh, color="#009E73", label="protein")
ax.barh([i-hh/2 for i in yy], fat,  height=hh, color="#CC79A7", label="fat")
ax.set_yticks(list(yy)); ax.set_yticklabels(labels, fontsize=8); ax.invert_yaxis()
ax.set_xlabel("Yield per area  (g · m⁻² · yr⁻¹, World 2022)")
ax.set_title("Protein and fat yield per area, selected crops", fontsize=11, weight="bold", pad=8)
ax.legend(loc="lower right", fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(FIG/"fig3_protein_fat_per_area.png", bbox_inches="tight"); plt.close(fig)

print("wrote:", *(p.name for p in sorted(FIG.glob("*.png"))))
