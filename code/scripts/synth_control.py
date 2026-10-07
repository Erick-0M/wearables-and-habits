# Unit-level synthetic control, pooled across adopters (issue #9). Exploratory.
# Run in research-container from /home/repo-intro:  python scripts/synth_control.py
# For each treated adopter (clean sample, g_clean_q), weights on never-treated donors (w>=0, sum=1) are chosen to match the
# adopter's L pre-adoption quarters (e=-L..-1) of the outcome (spec "own") or outcome + ln(1+#purchases) (spec "own+ln_n").
# Gap_e = y_i,g+e - synthetic_i,g+e; ATT_e = mean of gaps over adopters. e=0 is the adoption quarter. Post = mean of e=1..8.
import sys, numpy as np, pandas as pd
from scipy.optimize import minimize

O = "analysis/outputs/"; L = 8; EMAX = 8; K = 150; TMIN, TMAX = 8073, 8093
FULL = len(sys.argv) > 1 and sys.argv[1] == "fulldonor"  # donors must be observed through the whole post window (no window-end attrition)
SFX = "_fulldonor" if FULL else ""
P = pd.read_csv("build/interm/design_panel_q.csv")
OUT = {"run_shoe_d": "Running shoe", "run_any_d": "Running-related (keyword)", "fit_gear_d": "Fitness gear", "supp_d": "Supplements",
       "med_d": "Medication", "pet_d": "PLACEBO: pet", "book_d": "PLACEBO: books", "grocery_d": "PLACEBO: grocery/food",
       "ln_n": "General: ln(1+#purchases)"}
ts = np.arange(TMIN, TMAX + 1)
S = P[P.s_g_clean == 1]
unit = S.drop_duplicates("id").set_index("id")
treated = unit.index[unit.g_clean_q.notna()]; donors_all = unit.index[unit.g_clean_q.isna()]
W = {y: S.pivot(index="id", columns="t", values=y).reindex(columns=ts) for y in OUT}  # NaN outside observed window

def sc_weights(X, x):
    """min ||x - X'w||^2 s.t. w>=0, sum w=1; X is donors x periods."""
    n = X.shape[0]
    f = lambda w: np.sum((x - w @ X) ** 2); g = lambda w: 2 * X @ (w @ X - x)
    r = minimize(f, np.full(n, 1 / n), jac=g, bounds=[(0, 1)] * n, constraints={"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(n)},
                 method="SLSQP", options={"maxiter": 200})
    return r.x

def run_unit(i, g, y, match, pool):
    """Gap path e=-L..EMAX (NaN where unobserved) and pre-RMSE for unit i adopting at quarter g."""
    cols = np.arange(g - L, min(g + EMAX, TMAX) + 1)
    pre = cols < g
    if g - L < TMIN: return None
    Yi = W[y].loc[i, cols].values
    if np.isnan(Yi[pre]).any(): return None
    D = W[y].loc[pool, cols]
    ok = ~(D if FULL else D.iloc[:, :L]).isna().any(axis=1)          # donors need full pre window; post gaps use donors observed that quarter
    mats = [(D[ok].iloc[:, :L].values, Yi[:L])]
    if match == "own+ln_n":
        Dn = W["ln_n"].loc[D.index[ok], cols[:L]]; xn = W["ln_n"].loc[i, cols[:L]].values
        if np.isnan(xn).any() or Dn.isna().any().any(): return None
        mats.append((Dn.values, xn))
    Dm = D[ok]; Xs = np.hstack([m[0] for m in mats]); xs = np.concatenate([m[1] for m in mats])
    near = np.argsort(((Xs - xs) ** 2).sum(1))[:K]  # restrict to K nearest donors for speed
    w = sc_weights(Xs[near], xs); Dk = Dm.iloc[near].values
    syn = np.array([np.nansum(w * Dk[:, c]) / w[~np.isnan(Dk[:, c])].sum() if (~np.isnan(Dk[:, c])).any() else np.nan for c in range(len(cols))])
    gap = Yi - syn
    full = np.full(L + EMAX + 1, np.nan); full[: len(cols)] = gap
    return full, np.sqrt(np.nanmean(gap[:L] ** 2)), np.sqrt(np.nanmean(Yi[:L] ** 2))

def estimate(units_g, y, match, pool):
    G = []; rm = []
    for i, g in units_g.items():
        r = run_unit(i, int(g), y, match, pool)
        if r is not None: G.append(r[0]); rm.append((r[1], r[2]))
    G = np.array(G)
    if len(G) == 0: return None
    n = (~np.isnan(G)).sum(0); m = np.nanmean(G, 0); se = np.nanstd(G, 0, ddof=1) / np.sqrt(n)
    post = np.nanmean(G[:, L + 1:], 1); keep = ~np.isnan(post)
    return m, se, post[keep].mean(), post[keep].std(ddof=1) / np.sqrt(keep.sum()), len(G), np.mean([a for a, _ in rm]), np.mean([b for _, b in rm])

tg = unit.loc[treated, "g_clean_q"]
rows, es = [], []
rng = np.random.default_rng(1)
# placebo: pseudo-adopters drawn from donors, assigned real adoption quarters, synthetic built from remaining donors
ph = pd.Series(rng.choice(tg.values, size=len(tg)), index=rng.choice(donors_all, size=len(tg), replace=False))
for match in ["own", "own+ln_n"]:
    for y, name in OUT.items():
        if match == "own+ln_n" and y == "ln_n": continue
        for kind, ug in [("adopters", tg), ("placebo", ph)]:
            pool = donors_all if kind == "adopters" else donors_all.difference(ph.index)
            r = estimate(ug, y, match, pool)
            if r is None: continue
            m, se, pa, pse, n, prmse, psd = r
            rows.append(dict(match=match, kind=kind, outcome=y, name=name, post_att=pa, post_se=pse, n_units=n, pre_rmse=prmse, pre_rms_level=psd))
            for k, e in enumerate(range(-L, EMAX + 1)): es.append(dict(match=match, kind=kind, outcome=y, name=name, e=e, att=m[k], se=se[k]))
            print(match, kind, y, f"post={pa:.4f} ({pse:.4f}) n={n} preRMSE={prmse:.3f}/{psd:.3f}", flush=True)
pd.DataFrame(rows).to_csv(O + f"synth_summary{SFX}.csv", index=False); pd.DataFrame(es).to_csv(O + f"synth_eventstudy{SFX}.csv", index=False)
