# Randomization (placebo-permutation) p-values for the balanced synthetic control (issue #9). Exploratory.
# Run in research-container from /home/repo-intro:  python scripts/synth_control_perm.py [L] [NDON] [R]
# Same sample, predictors, block weights and weight estimator as synth_control_balanced.py (see that header).
# Test statistic: pooled post ATT (mean over units of the mean gap over e=1..L). Under the sharp null of no effect and exchangeability
# of adopters with donors, a random set of N donors given real adoption quarters has the same distribution. Every sampled donor j is run
# as pseudo-adopter for each adoption quarter g in the real cohort set (pool = all other donors); R random draws of N (donor, g)
# pairs (g drawn from the adopters' empirical cohort distribution) give the permutation distribution.
# p = (1 + #{|ATT_perm| >= |ATT_obs|}) / (R + 1): a Monte Carlo approximation of the exact permutation p-value
# (full enumeration of C(2392, N) subsets is infeasible), two-sided; also reports the one-sided (ATT_perm >= ATT_obs) p-value.
import sys, numpy as np, pandas as pd
from multiprocessing import Pool
from scipy.optimize import minimize

O = "analysis/outputs/"
L = int(sys.argv[1]) if len(sys.argv) > 1 else 8; NDON = int(sys.argv[2]) if len(sys.argv) > 2 else 500; R = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
K = 150; T0, T1 = 8073, 8092
P = pd.read_csv("build/interm/design_panel_q.csv"); C = pd.read_csv("build/interm/design_covariates.csv").set_index("id")
S = P[P.s_g_clean == 1]
sp = S.groupby("id").t.agg(["min", "max"]); bal = sp.index[(sp["min"] <= T0) & (sp["max"] >= T1)]
S = S[S.id.isin(bal)]
unit = S.drop_duplicates("id").set_index("id")
tg = unit.g_clean_q.dropna(); tg = tg[(tg >= T0 + L) & (tg <= T1 - L)].astype(int)
don = unit.index[unit.g_clean_q.isna()].values
ts = np.arange(T0, T1 + 1)
cat = ["run_any", "fit_gear", "supp", "med", "pet", "book", "giftcard", "cable", "cleaning", "grocery"]
OUT = {"run_shoe_d": "Running shoe", "run_any_d": "Running-related (keyword)", "fit_gear_d": "Fitness gear", "supp_d": "Supplements",
       "med_d": "Medication", "pet_d": "PLACEBO: pet", "book_d": "PLACEBO: books", "grocery_d": "PLACEBO: grocery/food",
       "ln_n": "General: ln(1+#purchases)"}
ids_all = np.concatenate([tg.index.values, don]); nA = len(tg)          # rows: adopters first, then donors
W = {v: S.pivot(index="id", columns="t", values=v).reindex(index=ids_all, columns=ts).values for v in set(OUT) | {"ln_n", "n", "spend"} | set(cat)}
DEMO = C.loc[ids_all, ["age", "inc", "hh", "female", "college", "white", "diab", "smoke", "alc", "svy_miss"]].values
BW = [2.0, 1.0, 1.0, 1.0]
c = lambda t: t - T0

def blocks(g, y):
    s = slice(c(g - L), c(g)); n = W["n"][:, s].sum(1).clip(min=1)
    mix = np.column_stack([W[v][:, s].sum(1) / n for v in cat] + [np.log1p(W["spend"][:, s].sum(1))])
    return [W[y][:, s], W["ln_n"][:, s] if y != "ln_n" else np.empty((len(ids_all), 0)), mix, DEMO]

def design(g, y):
    """standardized predictor matrix for all rows (SD from the donor rows), blocks scaled as in synth_control_balanced.py."""
    X = []
    for b, B in zip(BW, blocks(g, y)):
        if B.shape[1] == 0: continue
        sd = B[nA:].std(0); sd[sd < 1e-8] = 1
        X.append(B * (np.sqrt(b / B.shape[1]) / sd))
    return np.hstack(X)

def sc_weights(X, x):
    n = X.shape[0]
    f = lambda w: np.sum((x - w @ X) ** 2); g = lambda w: 2 * X @ (w @ X - x)
    return minimize(f, np.full(n, 1 / n), jac=g, bounds=[(0, 1)] * n, constraints={"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(n)},
                    method="SLSQP", options={"maxiter": 200}).x

def post_gap(row, g, y, X, drop_self):
    d = ((X[nA:] - X[row]) ** 2).sum(1)
    if drop_self: d[row - nA] = np.inf
    near = np.argsort(d)[:K]; w = sc_weights(X[nA:][near], X[row])
    cols = slice(c(g + 1), c(g + L) + 1)
    return float(W[y][row, cols].mean() - w @ W[y][nA:][near][:, cols].mean(1))

def task(a):
    y, g, rows, drop_self = a
    X = design(g, y)
    return [post_gap(r, g, y, X, drop_self) for r in rows]

if __name__ == "__main__":
    rng = np.random.default_rng(7)
    gs = sorted(tg.unique()); samp = rng.choice(len(don), size=min(NDON, len(don)), replace=False) + nA
    obs_rows = {g: list(np.where(tg.values == g)[0]) for g in gs}
    print(f"L={L}: adopters {nA}, donors {len(don)}, sampled placebo donors {len(samp)}, cohorts {gs}, R={R}", flush=True)
    tasks = [(y, g, obs_rows[g], False) for y in OUT for g in gs] + [(y, g, list(samp), True) for y in OUT for g in gs]
    with Pool(12) as pool: out = pool.map(task, tasks, chunksize=1)
    res = {(t[0], t[1], t[3]): o for t, o in zip(tasks, out)}
    rows = []
    for y, name in OUT.items():
        obs = np.concatenate([res[(y, g, False)] for g in gs]); att = obs.mean()
        T = np.array([res[(y, g, True)] for g in gs])  # cohorts x donors
        gdraw = rng.choice(len(gs), size=(R, nA), p=tg.value_counts(normalize=True).reindex(gs).values)
        jdraw = np.array([rng.choice(len(samp), size=nA, replace=False) for _ in range(R)])
        perm = T[gdraw, jdraw].mean(1)
        rows.append(dict(L=L, outcome=y, name=name, att=att, perm_mean=perm.mean(), perm_sd=perm.std(),
                         p_two_sided=(1 + (np.abs(perm) >= abs(att)).sum()) / (R + 1), p_one_sided=(1 + (perm >= att).sum()) / (R + 1)))
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(O + f"synth_perm_L{L}.csv", index=False)
