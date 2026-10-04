"""Data-quality checks for Open e-commerce (issue #5). Needs build/interm/purchases_flagged.pkl from data_audit_open_ecommerce.py."""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
O = "analysis/outputs/"; I = "build/interm/"; D = "build/input/public/open_ecommerce/"
a = pd.read_pickle(I + "purchases_flagged.pkl"); a["year"] = a.date.dt.year
s = pd.read_csv(D + "survey.csv")
out = {}

# 1. missingness by year, and what missing rows look like
m = a.groupby("year").agg(rows=("uid", "size"), cat_missing=("Category", lambda x: 100 * x.isna().mean()), title_missing=("Title", lambda x: 100 * x.isna().mean()))
mp = a.assign(miss=a.Category.isna()).groupby("miss").price.median()
print(m, mp)
m.round(2).rename(columns={"rows": "Rows", "cat_missing": "Category missing (\\%)", "title_missing": "Title missing (\\%)"}).rename_axis("Year").to_latex(escape=False, buf=O + "dq_missing_by_year.tex", column_format="lrrr", float_format=lambda x: f"{x:,.1f}", formatters={"Rows": "{:,}".format})

# 2. duplicates: where do they sit?
key = ["uid", "date", "price", "qty", "Title", "Category"]
dup = a.duplicated(key, keep="first")
per_user = dup.groupby(a.uid).sum()
top = per_user.sort_values(ascending=False)
out["dup rows (all columns)"] = int(dup.sum()); out["dup share of rows (\\%)"] = 100 * dup.mean()
out["users with any dup"] = int((per_user > 0).sum()); out["dup rows in top-1\\% users (\\%)"] = 100 * top.head(int(len(top) * .01)).sum() / dup.sum()
out["dup share, missing-title rows (\\%)"] = 100 * dup[a.Title.isna()].mean(); out["dup share, titled rows (\\%)"] = 100 * dup[a.Title.notna()].mean()
out["dup wearable rows"] = int(dup[a.wear].sum())

# 3. user coverage: window length, purchases per user, gaps
g = a.groupby("uid").date.agg(["min", "max", "size"]); g["days"] = (g["max"] - g["min"]).dt.days
gap = a.sort_values(["uid", "date"]).groupby("uid").date.diff().dt.days.groupby(a.sort_values(["uid", "date"]).uid).max()
out["median window (months)"] = g.days.median() / 30.4; out["users window <12m (\\%)"] = 100 * (g.days < 365).mean()
out["users window <24m (\\%)"] = 100 * (g.days < 730).mean(); out["median purchases / user"] = g["size"].median()
out["users with <10 purchases (\\%)"] = 100 * (g["size"] < 10).mean(); out["median longest gap (days)"] = gap.median()
out["users with a gap >180 days (\\%)"] = 100 * (gap > 180).mean()
fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
ax[0].hist(g.days / 30.4, bins=60); ax[0].set_title("Observed window per user (months)")
ax[1].hist(np.log10(g["size"]), bins=60); ax[1].set_title("log10 purchases per user")
ax[2].hist(gap.dropna().clip(upper=730), bins=60); ax[2].set_title("Longest gap between purchases (days, cap 730)")
for r in ax: r.grid(alpha=.3)
fig.tight_layout(); fig.savefig(O + "dq_user_coverage.png", dpi=130); plt.close(fig)

# 4. price / quantity outliers
out["price > \\$500 rows"] = int((a.price > 500).sum()); out["price > \\$2000 rows"] = int((a.price > 2000).sum())
out["qty >= 10 rows"] = int((a.qty >= 10).sum()); out["spend > \\$5000 rows"] = int((a.spend > 5000).sum())
out["share of spend in top 0.1\\% rows (\\%)"] = 100 * a.spend.nlargest(int(len(a) * .001)).sum() / a.spend.sum()
print(a.nlargest(5, "spend")[["price", "qty", "Title"]])

# 5. rows per month (raw, before panel construction): steady?
rm = a.groupby(a.date.dt.to_period("M")).agg(rows=("uid", "size"), users=("uid", "nunique"))
rm.index = rm.index.to_timestamp(); rm = rm[rm.users >= 1000]
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
ax[0].plot(rm.index, rm.rows); ax[0].set_title("Purchase rows per month"); ax[1].plot(rm.index, rm.users); ax[1].set_title("Users with a purchase that month")
for r in ax: r.grid(alpha=.3)
fig.tight_layout(); fig.savefig(O + "dq_rows_per_month.png", dpi=130); plt.close(fig)

# 6. classification validation
def brand(t):
    t = t.lower()
    for b in ["fitbit", "apple watch", "garmin", "samsung", "galaxy", "amazfit", "xiaomi", "polar", "withings", "misfit", "huawei", "fossil", "suunto", "whoop", "oura", "tomtom", "jawbone"]:
        if b in t: return b
    return "other / unbranded"
w = a[a.wear].copy(); w["brand"] = w.Title.fillna("").map(brand)
bt = w.groupby("brand").agg(rows=("uid", "size"), clean=("wear_clean", "sum"), med_price=("price", "median")).sort_values("rows", ascending=False)
bt.rename(columns={"rows": "Rows", "clean": "In clean def.", "med_price": "Median price (\\$)"}).rename_axis("Brand").to_latex(escape=False, buf=O + "dq_wearable_brands.tex", column_format="lrrr", float_format=lambda x: f"{x:,.0f}", formatters={"Rows": "{:,}".format})
out["wearable rows non-kids / clean"] = f"{int(a.wear.sum()):,} / {int(a.wear_clean.sum()):,}"
out["non-kids wearables with price < \\$40 (\\%)"] = 100 * (w.price < 40).mean()
print(bt); print(w[(~w.wear_clean)].Title.str[:70].sample(12, random_state=2).to_string())
ra = a[a.run_any]
tb = ra.Category.value_counts(normalize=True).head(8) * 100
out["run\\_any rows in SHOES/TECH SHOE (\\%)"] = 100 * ra.Category.isin(["SHOES", "TECHNICAL_SPORT_SHOE"]).mean()
out["run\\_any rows with 'running shoe' in title (\\%)"] = 100 * ra.Title.str.contains("running shoe", case=False, na=False).mean()
print(tb); print(ra[~ra.Category.isin(["SHOES", "TECHNICAL_SPORT_SHOE", "SHORTS", "PANTS", "SOCKS", "SHIRT"])].Title.str[:70].sample(15, random_state=3).to_string())
print(a[a.med].Title.str[:60].sample(10, random_state=5).to_string())
out["medication rows w/ 'pet|dog|cat' in title (\\%)"] = 100 * a[a.med].Title.str.contains(r"\bdogs?\b|\bcats?\b|\bpets?\b", case=False, na=False).mean()

# 7. survey missingness
sm = s.drop(columns="Survey ResponseID").apply(lambda c: 100 * (c.isna() | c.astype(str).str.contains("Prefer not", case=False)).mean())
keep = ["Q-demos-age", "Q-demos-race", "Q-demos-education", "Q-demos-income", "Q-demos-gender", "Q-amazon-use-hh-size", "Q-substance-use-alcohol", "Q-personal-diabetes"]
sm[keep].round(1).rename("Missing / prefer not (\\%)").to_frame().to_latex(O + "dq_survey_missing.tex", column_format="lr", float_format=lambda x: f"{x:.1f}")

o = pd.Series(out).map(lambda v: f"{v:,.1f}" if isinstance(v, float) else (f"{v:,}" if isinstance(v, (int, np.integer)) else v)).rename("Value").to_frame()
o.to_latex(O + "dq_checks.tex", escape=False, column_format="lr")
print(o)
