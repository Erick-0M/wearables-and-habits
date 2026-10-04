"""Data audit + variable construction for Open e-commerce (issue #5). Exploratory.
Run in research-container from /home/repo-intro:  python scripts/data_audit_open_ecommerce.py
"""
import re
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

D = "build/input/public/open_ecommerce/"; O = "analysis/outputs/"; I = "build/interm/"
U = "Survey ResponseID"
a = pd.read_csv(D + "amazon-purchases.csv", parse_dates=["Order Date"]).rename(columns={
    "Order Date": "date", "Purchase Price Per Unit": "price", "Quantity": "qty", U: "uid"})
s = pd.read_csv(D + "survey.csv").rename(columns={U: "uid"})
a["spend"] = a.price * a.qty
a["month"] = a.date.dt.to_period("M")
cat = a.Category.fillna(""); ttl = a.Title.fillna("")

# ---- audit: missingness / quirks
aud = {
    "rows": len(a), "users": a.uid.nunique(), "survey users": s.uid.nunique(),
    "purchase users not in survey": len(set(a.uid) - set(s.uid)),
    "missing Category (%)": 100 * a.Category.isna().mean(), "missing Title (%)": 100 * a.Title.isna().mean(),
    "missing price (%)": 100 * a.price.isna().mean(), "missing qty (%)": 100 * a.qty.isna().mean(),
    "price<=0 rows": int((a.price <= 0).sum()), "qty>1 rows (%)": 100 * (a.qty > 1).mean(),
    "exact duplicate rows": int(a.duplicated().sum()),
    "date min": str(a.date.min().date()), "date max": str(a.date.max().date()),
}
print(pd.Series(aud))

# ---- variable construction
# Treatment: wearable activity/health trackers by Amazon Category (accessories such as WATCH_BAND, plain WATCH excluded)
WEAR = ["WEARABLE_COMPUTER", "BIOMETRIC_MONITOR"]
kids = ttl.str.contains(r"\bkids?\b|child|\bboys?\b|\bgirls?\b|toddler|\bace\b|junior", case=False, regex=True)
a["wear"] = cat.isin(WEAR) & ~kids   # all non-kids trackers
# cleanest treatment: non-kids, price >= $40 (drops pedometers/knockoffs), real device (not a compatible accessory), single unit
acc = ttl.str.contains(r"compatible|replacement|screen protector|\bfor (fitbit|apple|garmin|samsung)", case=False, regex=True)
a["wear_clean"] = a.wear & (a.price >= 40) & ~acc & (a.qty == 1)
a["med"] = cat.isin(["MEDICATION", "OTC_MEDICATION"])   # human medication (animal medication excluded)
# Outcome (proxy for running): running shoes / running apparel & gear. Title-based within relevant categories.
run_re = r"running|runner|trail shoe|jogging"
shoe_cat = cat.isin(["SHOES", "TECHNICAL_SPORT_SHOE"])
a["run_shoe"] = shoe_cat & ttl.str.contains(run_re, case=False, regex=True)
a["run_any"] = (ttl.str.contains(run_re, case=False, regex=True) & ~cat.isin(["TABLE_RUNNER", "BOOK", "ABIS_BOOK", "ABIS_DVD", "PHYSICAL_MOVIE"]) & ~ttl.str.contains("table runner|runner rug|rug runner|stair runner|carpet runner", case=False)) | (cat == "TECHNICAL_SPORT_SHOE")
a["fit_gear"] = cat.isin(["SPORTING_GOODS", "FITNESS_BENCH", "FITNESS_HOOP", "FITNESS_STEPPER", "FITNESS_EQUIPMENT", "WEARABLE_WEIGHT", "SPORT_ACTIVITY_GLOVE"])
a["supp"] = cat.isin(["NUTRITIONAL_SUPPLEMENT", "VITAMIN"])  # placebo-ish / other health outcome
print("flag rows:", a[["wear", "run_shoe", "run_any", "fit_gear", "supp"]].sum().to_dict())
print(a.loc[a.run_any, "Category"].value_counts().head(8))

a.drop(columns=["ASIN/ISBN (Product Code)", "Shipping Address State"]).to_pickle(I + "purchases_flagged.pkl")  # row-level flags for data_quality_checks.py
# user windows and first-treatment date
w = a.groupby("uid").month.agg(first="min", last="max")
w["n_months"] = (w["last"] - w["first"]).apply(lambda x: x.n) + 1
ft = a[a.wear].groupby("uid").month.min().rename("g")
ftc = a[a.wear_clean].groupby("uid").month.min().rename("g_clean")
w = w.join(ft).join(ftc)
print("clean treated:", w.g_clean.notna().sum(), " non-kids treated:", w.g.notna().sum(), " flag rows wear/clean/med:", a.wear.sum(), a.wear_clean.sum(), a.med.sum())
w["ever"] = w.g.notna()
w["rel_start"] = (w.g - w["first"]).apply(lambda x: x.n if pd.notna(x) else np.nan)   # months of pre-history
w["rel_end"] = (w["last"] - w.g).apply(lambda x: x.n if pd.notna(x) else np.nan)       # months of post-history
print(w.ever.sum(), "ever-treated;", ((w.rel_start >= 12) & (w.rel_end >= 12)).sum(), "with >=12m pre & post")

# user-month panel over each user's observed window (zeros filled)
gm = a.groupby(["uid", "month"]).agg(n=("qty", "size"), spend=("spend", "sum"),
    wear=("wear", "sum"), wear_clean=("wear_clean", "sum"), med=("med", "sum"), run_shoe=("run_shoe", "sum"), run_any=("run_any", "sum"),
    fit_gear=("fit_gear", "sum"), supp=("supp", "sum"))
idx = pd.MultiIndex.from_tuples([(u, m) for u, f, l in zip(w.index, w["first"], w["last"]) for m in pd.period_range(f, l, freq="M")], names=["uid", "month"])
P = gm.reindex(idx, fill_value=0).reset_index()
P = P.merge(w[["g", "g_clean", "ever"]], left_on="uid", right_index=True)
P["event_t"] = (P.month - P.g).apply(lambda x: x.n if pd.notna(x) else np.nan)
P["post"] = P.event_t >= 0
for v in ["run_shoe", "run_any", "med"]:
    P[v + "_d"] = (P[v] > 0).astype(int)
P["ln_spend"] = np.log1p(P.spend)
P.to_pickle(I + "panel_user_month.pkl"); w.to_pickle(I + "user_windows.pkl")
print("panel", P.shape)

# ---- aggregate stats table
def tex(df, path, fmt="{:,.2f}"):
    df.to_latex(path, float_format=lambda x: fmt.format(x), escape=True, column_format="l" + "r" * df.shape[1])
tab = pd.DataFrame({
    "Mean": [P.n.mean(), P.spend.mean(), P.wear.mean(), P.wear_clean.mean(), P.run_any.mean(), P.run_shoe.mean(), P.fit_gear.mean(), P.supp.mean(), P.med.mean()],
    "Sd": [P.n.std(), P.spend.std(), P.wear.std(), P.wear_clean.std(), P.run_any.std(), P.run_shoe.std(), P.fit_gear.std(), P.supp.std(), P.med.std()],
    "Pct zero": [100 * (P[v] == 0).mean() for v in ["n", "spend", "wear", "wear_clean", "run_any", "run_shoe", "fit_gear", "supp", "med"]],
}, index=["Purchases", "Spend (\\$)", "Wearable purchases (non-kids)", "Wearable purchases (clean)", "Running-related purchases", "Running-shoe purchases", "Fitness-gear purchases", "Supplement purchases", "Medication purchases"])
tex(tab, O + "audit_panel_summary.tex", "{:,.3f}")
w2 = pd.DataFrame({"Users": [len(w), w.ever.sum(), (w.ever & (w.rel_start >= 6)).sum(), (w.ever & (w.rel_start >= 12) & (w.rel_end >= 12)).sum(), (w.ever & (w.rel_start >= 24) & (w.rel_end >= 24)).sum(), w.g_clean.notna().sum(), (w.g_clean.notna() & (((w.g_clean - w["first"]).apply(lambda x: x.n if pd.notna(x) else np.nan)) >= 12) & (((w["last"] - w.g_clean).apply(lambda x: x.n if pd.notna(x) else np.nan)) >= 12)).sum()]},
    index=["All users", "Ever bought wearable (non-kids)", "\\quad $\\geq$6m pre-history", "\\quad $\\geq$12m pre and post", "\\quad $\\geq$24m pre and post", "Ever bought clean wearable", "\\quad $\\geq$12m pre and post"])
w2.to_latex(O + "audit_treated_counts.tex", escape=False, column_format="lr", float_format=lambda x: f"{x:,.0f}")
fm = lambda v: f"{v:,.2f}" if isinstance(v, float) else (f"{v:,}" if isinstance(v, (int, np.integer)) else str(v))
aud_t = pd.DataFrame({"Value": [fm(v) for v in aud.values()]}, index=[i.replace("%", "\\%").replace("<=", "$\\leq$").replace(">", "$>$") for i in aud])
aud_t.to_latex(O + "audit_quirks.tex", escape=False, column_format="lr")

# ---- time series (calendar), with smoothness check
mon = P.groupby("month").agg(users=("uid", "nunique"), n=("n", "sum"), spend=("spend", "sum"),
    wear=("wear", "sum"), wear_clean=("wear_clean", "sum"), med=("med", "sum"), run_any=("run_any", "sum"), run_shoe=("run_shoe", "sum"), fit_gear=("fit_gear", "sum"), supp=("supp", "sum"))
mon.index = mon.index.to_timestamp()
print(mon.users.tail(20).to_string())
mon = mon[mon.users >= 1000]  # after ~2023-03 almost no user is still observed; ratios there are noise
per = pd.DataFrame({"Purchases per active user": mon.n / mon.users, "Spend per active user (USD)": mon.spend / mon.users,
    "Wearable (non-kids) per 1000 users": 1000 * mon.wear / mon.users, "Wearable (clean) per 1000 users": 1000 * mon.wear_clean / mon.users, "Running-related per 1000 users": 1000 * mon.run_any / mon.users,
    "Running-shoe per 1000 users": 1000 * mon.run_shoe / mon.users, "Fitness-gear per 1000 users": 1000 * mon.fit_gear / mon.users,
    "Supplement per 1000 users": 1000 * mon.supp / mon.users, "Medication per 1000 users": 1000 * mon.med / mon.users})
fig, ax = plt.subplots(5, 2, figsize=(11, 12), sharex=True)
for k, (c, x) in enumerate(list(per.items()) + [("Active users (window)", mon.users)]):
    r = ax.flat[k]; r.plot(x.index, x.values, lw=1, color="#1f77b4"); r.plot(x.index, x.rolling(12, center=True).mean(), lw=1.8, color="#d62728")
    r.set_title(c, fontsize=9); r.grid(alpha=.3)
fig.suptitle("Calendar-month series (blue) and centered 12m MA (red)"); fig.tight_layout()
fig.savefig(O + "audit_calendar_series.png", dpi=130); plt.close(fig)
# smoothness: sd of month-to-month change relative to sd of level, and share of months with >3 sd jumps
sm = []
for c, x in list(per.items()) + [("Active users", mon.users)]:
    d = x.diff().dropna(); z = (d - d.mean()) / d.std()
    sm.append((c, x.mean(), d.std() / x.std(), int((z.abs() > 3).sum()), x.autocorr(1)))
smd = pd.DataFrame(sm, columns=["Series", "Mean", "Sd(diff)/Sd(level)", "Months $|z|>3$", "AR(1)"]).set_index("Series")
smd.to_latex(O + "audit_smoothness.tex", escape=False, column_format="lrrrr", float_format=lambda x: f"{x:,.2f}")
print(smd)

# ---- event-time series among ever-treated (bins pooled), outcome smoothness around adoption
E = P[P.ever & (P.event_t.between(-24, 24))]
ev = E.groupby("event_t")[["run_any", "run_shoe", "fit_gear", "supp", "med", "n", "spend"]].mean()
cnt = E.groupby("event_t").uid.nunique()
fig, ax = plt.subplots(2, 4, figsize=(15, 6), sharex=True)
for r, c in zip(ax.flat, ["n", "spend", "run_any", "run_shoe", "fit_gear", "supp", "med"]):
    r.plot(ev.index, ev[c], marker="o", ms=3, lw=1); r.axvline(0, color="k", ls="--", lw=.8); r.set_title(c + " per user-month", fontsize=9); r.grid(alpha=.3)
fig.suptitle("Ever-treated: mean by months since first wearable (unbalanced composition)"); fig.tight_layout()
fig.savefig(O + "audit_event_time_series.png", dpi=130); plt.close(fig)
# running outcome: treated vs never-treated in calendar time
fig, r = plt.subplots(figsize=(7, 4))
for e, lab in [(True, "Ever-treated"), (False, "Never-treated")]:
    g = P[(P.ever == e) & (P.month <= mon.index.max().to_period("M"))].groupby("month").run_any.mean(); g.index = g.index.to_timestamp()
    r.plot(g.index, 1000 * g.rolling(6, center=True).mean(), label=lab)
r.set_ylabel("Running-related per 1000 user-months\n(6m MA)"); r.legend(); r.grid(alpha=.3)
fig.tight_layout(); fig.savefig(O + "audit_run_treated_vs_never.png", dpi=130); plt.close(fig)

# ---- correlations (user level, pre-adoption window for treated, whole window for never-treated)
U_ = P.groupby("uid").agg(n=("n", "sum"), spend=("spend", "sum"), months=("month", "size"), wear=("wear", "sum"),
    run_any=("run_any", "sum"), run_shoe=("run_shoe", "sum"), fit_gear=("fit_gear", "sum"), supp=("supp", "sum"), med=("med", "sum"))
for v in ["n", "spend", "wear", "run_any", "run_shoe", "fit_gear", "supp", "med"]:
    U_[v + "_pm"] = U_[v] / U_.months
cv = ["n_pm", "spend_pm", "wear_pm", "run_any_pm", "run_shoe_pm", "fit_gear_pm", "supp_pm", "med_pm"]
lab = ["Purchases", "Spend", "Wearable", "Running", "Run shoes", "Fitness gear", "Supplements", "Medication"]
C = U_[cv].corr(method="spearman")
fig, r = plt.subplots(figsize=(6.5, 5.5)); im = r.imshow(C.values, cmap="RdBu_r", vmin=-1, vmax=1)
r.set_xticks(range(8), lab, rotation=45, ha="right"); r.set_yticks(range(8), lab)
for i in range(8):
    for j in range(8): r.text(j, i, f"{C.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
fig.colorbar(im); r.set_title("Spearman correlations of per-month user rates"); fig.tight_layout()
fig.savefig(O + "audit_correlations.png", dpi=130); plt.close(fig)

# ---- balance: LPM of ever-treated on survey demographics (+ joint F test)
S = s.merge(w[["ever", "n_months"]], left_on="uid", right_index=True)
age_map = {x: i for i, x in enumerate(sorted(S["Q-demos-age"].dropna().unique()))}
S["age"] = S["Q-demos-age"].map(age_map)
inc_order = ["Less than $25,000", "$25,000 - $49,999", "$50,000 - $74,999", "$75,000 - $99,999", "$100,000 - $149,999", "$150,000 or more"]
S["inc"] = S["Q-demos-income"].map({k: i for i, k in enumerate(inc_order)})
S["female"] = (S["Q-demos-gender"] == "Female").astype(float).where(S["Q-demos-gender"].notna())
S["college"] = S["Q-demos-education"].fillna("").str.contains("Bachelor|Graduate|graduate|degree", regex=True).astype(float).where(S["Q-demos-education"].notna())
S["white"] = (S["Q-demos-race"] == "White or Caucasian").astype(float).where(S["Q-demos-race"].notna())
S["hisp"] = (S["Q-demos-hispanic"] == "Yes").astype(float).where(S["Q-demos-hispanic"].notna())
S["hh"] = S["Q-amazon-use-hh-size"].replace({"4+": 4, "1 (just me!)": 1}).astype(float)   # (earlier version lost the "1 (just me!)" answers to NaN)
S["diab"] = (S["Q-personal-diabetes"] == "Yes").astype(float).where(S["Q-personal-diabetes"].notna())
S["smoke"] = (S["Q-substance-use-cigarettes"] == "Yes").astype(float).where(S["Q-substance-use-cigarettes"].notna())
S["alc"] = (S["Q-substance-use-alcohol"] == "Yes").astype(float).where(S["Q-substance-use-alcohol"].notna())
S["lnmonths"] = np.log(S.n_months)
print(S["Q-demos-income"].value_counts().head(8)); print(S["Q-demos-education"].value_counts())
S["ever_i"] = S.ever.astype(float)
# standardize covariates so coefficients are comparable (effect on P(ever) of +1 sd)
cov = {"age": "Age bracket", "female": "Female", "inc": "Income bracket", "college": "College+", "white": "White", "hisp": "Hispanic",
       "hh": "Household size", "diab": "Diabetes", "smoke": "Smokes", "alc": "Drinks alcohol", "lnmonths": "log months observed"}
Z = S[["ever_i"] + list(cov)].dropna().copy()
for c in cov: Z[c] = (Z[c] - Z[c].mean()) / Z[c].std()
m = smf.ols("ever_i ~ " + " + ".join(cov), Z).fit(cov_type="HC1")
ft = m.f_test(" , ".join(f"{c} = 0" for c in cov))
print(m.summary().tables[1]); print("joint F", ft.fvalue, ft.pvalue, "N", len(Z))
# also without exposure-length control (pure demographics)
cov2 = {k: v for k, v in cov.items() if k != "lnmonths"}
m2 = smf.ols("ever_i ~ " + " + ".join(cov2), Z).fit(cov_type="HC1")
ft2 = m2.f_test(" , ".join(f"{c} = 0" for c in cov2))
fig, r = plt.subplots(figsize=(6.5, 4.5))
for mm, off, nm in [(m2, .15, "demographics only"), (m, -.15, "+ log months observed")]:
    ci = mm.conf_int().drop("Intercept"); b = mm.params.drop("Intercept"); y = np.arange(len(b))[::-1] + off
    r.errorbar(b, y, xerr=[b - ci[0], ci[1] - b], fmt="o", ms=4, capsize=2, label=nm)
r.set_yticks(np.arange(len(cov))[::-1], [cov[i] for i in b.index]); r.axvline(0, color="k", lw=.8)
r.set_xlabel("Change in P(ever buys wearable) per +1 sd (LPM, HC1 95% CI)")
r.set_title(f"Balance: ever-treated vs never. Joint F p = {ft2.pvalue:.3f} / {ft.pvalue:.3f}", fontsize=9)
r.legend(fontsize=8); r.grid(alpha=.3); fig.tight_layout(); fig.savefig(O + "audit_balance_ever_treated.png", dpi=130); plt.close(fig)

# ---- balance on pre-period purchasing: first 12 months of each user's window
f12 = P[P.month <= P.groupby("uid").month.transform(lambda x: x.min() + 11)]
B = f12.groupby("uid").agg(n=("n", "mean"), spend=("spend", "mean"), run_any=("run_any", "mean"), run_shoe=("run_shoe", "mean"), fit_gear=("fit_gear", "mean"), supp=("supp", "mean")).join(w[["ever", "n_months"]])
B["ever_i"] = B.ever.astype(float); B = B[B.n_months >= 12].dropna()
bl = {"n": "Purchases/mo", "spend": "Spend/mo", "run_any": "Running-related/mo", "run_shoe": "Running shoes/mo", "fit_gear": "Fitness gear/mo", "supp": "Supplements/mo"}
for c in bl: B[c] = (B[c] - B[c].mean()) / B[c].std()
m3 = smf.ols("ever_i ~ " + " + ".join(bl), B).fit(cov_type="HC1"); ft3 = m3.f_test(" , ".join(f"{c} = 0" for c in bl))
# one-at-a-time (bivariate) too, since the rates are collinear
ci = m3.conf_int().drop("Intercept"); b = m3.params.drop("Intercept")
fig, r = plt.subplots(figsize=(6.5, 3.5)); y = np.arange(len(b))[::-1]
r.errorbar(b, y, xerr=[b - ci[0], ci[1] - b], fmt="o", capsize=2); r.set_yticks(y, [bl[i] for i in b.index]); r.axvline(0, color="k", lw=.8)
r.set_xlabel("Change in P(ever buys wearable) per +1 sd, first 12 months (LPM, HC1)")
r.set_title(f"Balance on early purchasing; joint F p = {ft3.pvalue:.3f}, N = {len(B):,}", fontsize=9); r.grid(alpha=.3)
fig.tight_layout(); fig.savefig(O + "audit_balance_prepurchasing.png", dpi=130); plt.close(fig)

# ---- adoption-timing balance among ever-treated (early vs late adopters), demographics
T = S[S.ever].merge(w[["g"]], left_on="uid", right_index=True)
T["g_year"] = T.g.apply(lambda p: p.year + (p.month - 1) / 12)
Zt = T[["g_year"] + list(cov2)].dropna().copy()
for c in list(cov2) + ["g_year"]: Zt[c] = (Zt[c] - Zt[c].mean()) / Zt[c].std()
m4 = smf.ols("g_year ~ " + " + ".join(cov2), Zt).fit(cov_type="HC1"); ft4 = m4.f_test(" , ".join(f"{c} = 0" for c in cov2))
ci = m4.conf_int().drop("Intercept"); b = m4.params.drop("Intercept")
fig, r = plt.subplots(figsize=(6.5, 4)); y = np.arange(len(b))[::-1]
r.errorbar(b, y, xerr=[b - ci[0], ci[1] - b], fmt="o", capsize=2); r.set_yticks(y, [cov2[i] for i in b.index]); r.axvline(0, color="k", lw=.8)
r.set_xlabel("Change in adoption date (sd units) per +1 sd covariate (HC1 95% CI)")
r.set_title(f"Balance across adoption cohorts (ever-treated); joint F p = {ft4.pvalue:.3f}, N = {len(Zt):,}", fontsize=9); r.grid(alpha=.3)
fig.tight_layout(); fig.savefig(O + "audit_balance_timing.png", dpi=130); plt.close(fig)
print("F-tests p:", ft2.pvalue, ft.pvalue, ft3.pvalue, ft4.pvalue)
with open(O + "audit_balance_ftests.tex", "w") as f:
    f.write("\\begin{tabular}{lrr}\\toprule\nRegression & Joint $F$ p-value & N \\\\\\midrule\n")
    for nm, p, n in [("Ever-treated on demographics", ft2.pvalue, int(m2.nobs)), ("Ever-treated on demographics + log months", ft.pvalue, int(m.nobs)),
                     ("Ever-treated on first-12m purchasing", ft3.pvalue, int(m3.nobs)), ("Adoption date on demographics (treated only)", ft4.pvalue, int(m4.nobs))]:
        f.write(f"{nm} & {p:.3f} & {n:,} \\\\\n")
    f.write("\\bottomrule\\end{tabular}\n")

# ---- user-quarter export for R (did). Outcomes as dummies; g = first treated quarter index (0 = never)
P["q"] = P.month.dt.asfreq("Q")
Q = P[P.month <= pd.Period("2022-12", "M")].groupby(["uid", "q"]).agg(n=("n", "sum"), spend=("spend", "sum"), mo=("month", "size"),
    **{v: (v, "sum") for v in ["run_any", "run_shoe", "med", "fit_gear", "supp"]}).reset_index()
Q = Q[Q.mo == 3]   # keep complete quarters only
for v in ["run_any", "run_shoe", "med", "fit_gear", "supp"]: Q[v + "_d"] = (Q[v] > 0).astype(int)
base = pd.Period("2018Q1", "Q")
Q["t"] = Q.q.apply(lambda x: (x - base).n + 1); Q["uidn"] = Q.uid.astype("category").cat.codes + 1
for gname in ["g", "g_clean"]:
    gq = w[gname].dropna().dt.asfreq("Q").apply(lambda x: (x - base).n + 1)
    Q[gname] = Q.uid.map(gq).fillna(0).astype(int)
Q["ln_spend"] = np.log1p(Q.spend)
Q.drop(columns="q").to_csv(I + "panel_user_quarter.csv", index=False)
print("quarter panel", Q.shape, (Q.g_clean > 0).groupby(Q.uid).max().sum(), "clean-treated users in panel")
