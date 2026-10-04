# Balanced-panel unit-level synthetic control with category-mix and demographic matching (issue #9). Exploratory.
# Run in research-container from /home/repo-intro:  python scripts/synth_control_balanced.py [L]   (L = pre = post quarters, default 8)
# Sample: clean sample, users observed in EVERY quarter 2018Q1-2022Q4 (t=8073..8092); adopters need the whole window g-L..g+L inside it.
# Predictors for adopter i (adoption quarter g) and every donor j (same calendar window g-L..g-1 for both), four blocks, each
# column standardized by the donor-pool SD and scaled so a block's total weight is: outcome path 2, ln(1+n) path 1, category mix 1, demographics 1:
#   (1) outcome indicator in each of the L pre quarters (the outcome being studied);
#   (2) ln(1+#purchases) in each pre quarter;
#   (3) pre-window category mix: share of purchases in running-related, fitness gear, supplements, medication, pet, books,
#       gift cards, cables/batteries, cleaning, grocery, plus ln(1+total spend);
#   (4) survey demographics: age band, income band, household size, female, college, white, diabetes, smoker, alcohol, survey-missing flag.
# Weights: non-negative, sum to one, on the K=150 nearest donors (full predictor distance), least squares.
# Gap_e = adopter minus synthetic, e=-L..L (0 = adoption quarter); Post = mean of e=1..L. Placebo = pseudo-adopters from donors.
import sys, numpy as np, pandas as pd
from scipy.optimize import minimize

O = "analysis/outputs/"; L = int(sys.argv[1]) if len(sys.argv) > 1 else 8; K = 150; T0, T1 = 8073, 8092
P = pd.read_csv("build/interm/design_panel_q.csv"); C = pd.read_csv("build/interm/design_covariates.csv").set_index("id")
S = P[P.s_g_clean == 1]
sp = S.groupby("id").t.agg(["min", "max"]); bal = sp.index[(sp["min"] <= T0) & (sp["max"] >= T1)]
S = S[S.id.isin(bal)]
unit = S.drop_duplicates("id").set_index("id")
tg = unit.g_clean_q.dropna(); tg = tg[(tg >= T0 + L) & (tg <= T1 - L)].astype(int)
donors_all = unit.index[unit.g_clean_q.isna()]
print(f"L={L}: balanced users {len(bal)}, donors {len(donors_all)}, adopters {len(tg)}", flush=True)
ts = np.arange(T0, T1 + 1)
cat = ["run_any", "fit_gear", "supp", "med", "pet", "book", "giftcard", "cable", "cleaning", "grocery"]
OUT = {"run_shoe_d": "Running shoe", "run_any_d": "Running-related (keyword)", "fit_gear_d": "Fitness gear", "supp_d": "Supplements",
       "med_d": "Medication", "pet_d": "PLACEBO: pet", "book_d": "PLACEBO: books", "grocery_d": "PLACEBO: grocery/food",
       "ln_n": "General: ln(1+#purchases)"}
piv = lambda v: S.pivot(index="id", columns="t", values=v).reindex(columns=ts)
W = {y: piv(y) for y in set(OUT) | {"ln_n", "n", "spend"} | set(cat)}
demo_cols = ["age", "inc", "hh", "female", "college", "white", "diab", "smoke", "alc", "svy_miss"]
DEMO = C.loc[bal, demo_cols]
col = lambda t: t - T0   # column position of quarter t

def block_cat(ids, g):
    """pre-window category shares + ln(1+spend) for users ids, window g-L..g-1."""
    c = slice(col(g - L), col(g))
    n = W["n"].loc[ids].values[:, c].sum(1).clip(min=1)
    X = np.column_stack([W[v].loc[ids].values[:, c].sum(1) / n for v in cat] + [np.log1p(W["spend"].loc[ids].values[:, c].sum(1))])
    return X

def predictors(ids, g, y):
    """Return (matrix of blocks list, outcome-path columns)."""
    c = slice(col(g - L), col(g))
    B = [W[y].loc[ids].values[:, c], W["ln_n"].loc[ids].values[:, c] if y != "ln_n" else np.empty((len(ids), 0)),
         block_cat(ids, g), DEMO.loc[ids].values]
    return B

BW = [2.0, 1.0, 1.0, 1.0]
def stack(Bd, Bi, bw=BW):
    """standardize by donor SD, scale blocks; returns donor matrix, adopter vector."""
    Xd, xi = [], []
    for b, bd, bi in zip(bw, Bd, Bi):
        if bd.shape[1] == 0: continue
        sd = bd.std(0); sd[sd < 1e-8] = 1
        s = np.sqrt(b / bd.shape[1]) / sd
        Xd.append(bd * s); xi.append(bi * s)
    return np.hstack(Xd), np.concatenate(xi)

def sc_weights(X, x):
    n = X.shape[0]
    f = lambda w: np.sum((x - w @ X) ** 2); g = lambda w: 2 * X @ (w @ X - x)
    r = minimize(f, np.full(n, 1 / n), jac=g, bounds=[(0, 1)] * n, constraints={"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(n)},
                 method="SLSQP", options={"maxiter": 200})
    return r.x

def run_unit(i, g, y, pool):
    cols = slice(col(g - L), col(g + L) + 1)
    Bd = predictors(pool, g, y); Bi = [b[0] for b in predictors([i], g, y)]
    Xd, xi = stack(Bd, Bi)
    near = np.argsort(((Xd - xi) ** 2).sum(1))[:K]
    w = sc_weights(Xd[near], xi)
    ids = pool[near]
    gap = W[y].loc[i].values[cols] - w @ W[y].loc[ids].values[:, cols]
    # covariate balance: adopter vs synthetic vs donor-pool mean on unscaled predictors (mix + demographics + ln n pre-mean)
    Bn = [b[near] for b in Bd]
    bal_ = np.concatenate([Bi[2], Bi[3]]); syn_ = np.concatenate([w @ Bn[2], w @ Bn[3]]); raw_ = np.concatenate([Bd[2].mean(0), Bd[3].mean(0)])
    return gap, np.sqrt(np.mean(gap[:L] ** 2)), np.sqrt(np.mean(W[y].loc[i].values[cols][:L] ** 2)), bal_, syn_, raw_

def estimate(units_g, y, pool):
    G, rm, bl = [], [], []
    for i, g in units_g.items():
        r = run_unit(i, int(g), y, pool); G.append(r[0]); rm.append(r[1:3]); bl.append(r[3:])
    G = np.array(G); n = len(G); m = G.mean(0); se = G.std(0, ddof=1) / np.sqrt(n)
    post = G[:, L + 1:].mean(1)
    bl = np.array(bl)   # n x 3 x p
    return m, se, post.mean(), post.std(ddof=1) / np.sqrt(n), n, np.mean([a for a, _ in rm]), np.mean([b for _, b in rm]), bl.mean(0)

rng = np.random.default_rng(1)
pidx = rng.choice(donors_all, size=len(tg), replace=False)
ph = pd.Series(rng.choice(tg.values, size=len(tg)), index=pidx)
rows, es, balrows = [], [], []
names = [f"share: {v}" for v in cat] + ["ln spend (pre)"] + demo_cols
for y, name in OUT.items():
    for kind, ug in [("adopters", tg), ("placebo", ph)]:
        pool = donors_all if kind == "adopters" else donors_all.difference(ph.index)
        m, se, pa, pse, n, prmse, plev, bl = estimate(ug, y, pool)
        rows.append(dict(L=L, kind=kind, outcome=y, name=name, post_att=pa, post_se=pse, n_units=n, pre_rmse=prmse, pre_rms_level=plev))
        for k, e in enumerate(range(-L, L + 1)): es.append(dict(L=L, kind=kind, outcome=y, name=name, e=e, att=m[k], se=se[k]))
        if kind == "adopters" and y == "run_any_d":
            for k, nm in enumerate(names): balrows.append(dict(L=L, var=nm, adopters=bl[0, k], synthetic=bl[1, k], donor_pool=bl[2, k]))
        print(L, kind, y, f"post={pa:.4f} ({pse:.4f}) n={n} preRMSE={prmse:.3f}/{plev:.3f}", flush=True)
pd.DataFrame(rows).to_csv(O + f"synth_bal_summary_L{L}.csv", index=False); pd.DataFrame(es).to_csv(O + f"synth_bal_eventstudy_L{L}.csv", index=False)
pd.DataFrame(balrows).to_csv(O + f"synth_bal_covbalance_L{L}.csv", index=False)
