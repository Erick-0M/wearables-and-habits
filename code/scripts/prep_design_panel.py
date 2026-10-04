"""Build user-quarter panel for the DiD design (issue #7). Exploratory.
Run in research-container from /home/repo-intro:  python scripts/prep_design_panel.py
Writes build/interm/design_panel_q.csv (read by scripts/design_did.R).
"""
import numpy as np, pandas as pd

I = "build/interm/"
a = pd.read_pickle(I + "purchases_flagged.pkl")
cat = a.Category.fillna(""); ttl = a.Title.fillna("")
END = pd.Period("2023-03", "M")                    # usable window from audit (#5)
a = a[a.month <= END].copy(); cat = cat[a.index]; ttl = ttl[a.index]

# placebo categories (unrelated to running/health)
a["pet"] = cat.isin(["PET_FOOD", "PET_SUPPLIES", "PET_TOY"])
a["book"] = cat.isin(["ABIS_BOOK"])
a["giftcard"] = cat.isin(["GIFT_CARD"])
a["cable"] = cat.isin(["ELECTRONIC_CABLE", "CHARGING_ADAPTER", "BATTERY"])
a["cleaning"] = cat.isin(["CLEANING_AGENT"])
a["grocery"] = cat.isin(["GROCERY", "FOOD", "COFFEE", "VEGETABLE", "FRUIT"])
a["shoe"] = cat.isin(["SHOES"])                    # all shoes (running shoes are a subset)
a["run_noshoe"] = a.run_any & ~a.run_shoe

# user windows, truncated at END
w = a.groupby("uid").month.agg(first="min", last="max")
for g_, f in [("g", "wear"), ("g_clean", "wear_clean"), ("g_shoe", "run_shoe")]:
    w[g_] = a[a[f]].groupby("uid").month.min()
mo = lambda x: x.apply(lambda d: d.n if pd.notna(d) else np.nan)
for g_ in ["g", "g_clean", "g_shoe"]:
    w["pre_" + g_] = mo(w[g_] - w["first"]); w["post_" + g_] = mo(w["last"] - w[g_])

# bundling: running shoe bought within +-1 month of the (first) wearable
a = a.merge(w[["g", "g_clean"]], left_on="uid", right_index=True)
near = lambda g_: ((a.month - a[g_]).apply(lambda d: d.n if pd.notna(d) else 99).abs() <= 1)
for g_ in ["g", "g_clean"]:
    a["nearshoe_" + g_] = a.run_shoe & near(g_)
    w["bundle_" + g_] = a.groupby("uid")["nearshoe_" + g_].max().reindex(w.index).fillna(False)
    # outcomes excluding the bundled shoe purchase itself
    a["run_shoe_ex_" + g_] = a.run_shoe & ~near(g_)
    a["run_any_ex_" + g_] = a.run_any & ~near(g_)

# quarterly panel over each user's observed window
q = lambda p: p.asfreq("Q")
a["q"] = a.month.apply(q)
flags = ["wear", "run_shoe", "run_any", "run_noshoe", "fit_gear", "supp", "med", "pet", "book", "giftcard", "cable",
         "cleaning", "grocery", "run_shoe_ex_g", "run_any_ex_g", "run_shoe_ex_g_clean", "run_any_ex_g_clean"]
agg = {f: (f, "sum") for f in flags}
agg.update(n=("qty", "size"), spend=("spend", "sum"))
G = a.groupby(["uid", "q"]).agg(**agg)
shoe = a[a.shoe & (a.price > 0)].groupby(["uid", "q"]).price.mean().rename("shoe_price")
idx = pd.MultiIndex.from_tuples([(u, qq) for u, f, l in zip(w.index, w["first"], w["last"]) for qq in pd.period_range(q(f), q(l), freq="Q")], names=["uid", "q"])
P = G.reindex(idx, fill_value=0).join(shoe).reset_index()
for f in flags:
    P[f + "_d"] = (P[f] > 0).astype(int)
P["ln_n"] = np.log1p(P.n); P["ln_spend"] = np.log1p(P.spend); P["ln_shoe_price"] = np.log(P.shoe_price)
P["t"] = P.q.apply(lambda x: x.year * 4 + x.quarter)
for g_ in ["g", "g_clean", "g_shoe"]:
    P[g_ + "_q"] = P.uid.map(w[g_].apply(lambda m: m.asfreq("Q").year * 4 + m.asfreq("Q").quarter if pd.notna(m) else np.nan))
for c in ["bundle_g", "bundle_g_clean"]:
    P[c] = P.uid.map(w[c]).astype(float)
# sample membership flags
ok = lambda g_: (w["pre_" + g_] >= 12) & (w["post_" + g_] >= 12)
P["id"] = P.uid.astype("category").cat.codes + 1
P["s_g"] = P.uid.map(~w.g.notna() | ok("g")).astype(int)                          # never-treated or >=12m pre/post
P["s_g_clean"] = P.uid.map(~w.g.notna() | (w.g_clean.notna() & ok("g_clean"))).astype(int)  # clean: drop non-clean adopters
P["s_g_shoe"] = P.uid.map(~w.g_shoe.notna() | ok("g_shoe")).astype(int)
P["adopter"] = P.uid.map(w.g.notna()).astype(int)       # for shoe-as-treatment robustness (drop wearable adopters)
P["q"] = P.q.astype(str)
P[["id","uid"]].drop_duplicates().to_csv(I + "design_id_map.csv", index=False)
P.drop(columns="uid").to_csv(I + "design_panel_q.csv", index=False)
print(P.shape, P.id.nunique())
print({g_: int((ok(g_) & w[g_].notna()).sum()) for g_ in ["g", "g_clean", "g_shoe"]},
      "bundlers (g, ok):", int((w.bundle_g & ok("g") & w.g.notna()).sum()),
      "(clean):", int((w.bundle_g_clean & ok("g_clean") & w.g_clean.notna()).sum()))
