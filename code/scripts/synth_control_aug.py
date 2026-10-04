# Augmented synthetic control (ridge bias correction, Ben-Michael, Feller & Rothstein 2021) with randomization inference (issue #9). Exploratory.
# Run in research-container from /home/repo-intro:  python scripts/synth_control_aug.py [L] [NDON] [R]
# Same balanced sample, predictors (4 weighted blocks), convex SC weights (K=150 nearest donors) as synth_control_balanced.py / _perm.py.
# Augmentation: a ridge model m(x) of every event-time outcome (e=-L..L) on the standardized predictors is fit on ALL donors (centered, intercept);
#   y_hat_i(0) = sum_j w_j y_j + (m(x_i) - sum_j w_j m(x_j)),  gap_aug = gap_SC - (x_i - sum_j w_j x_j)' beta.
# Lets the synthetic twin extrapolate where the adopter lies outside the donors' convex hull (e.g. the e=-1 jump in purchasing).
# Ridge penalty: chosen per (outcome, cohort) by leave-one-donor-out error (closed form) of the mean post outcome over a grid.
# Placebo/pseudo-adopters: leave-one-out (the donor itself is removed from the SC shortlist AND the ridge fit via rank-one downdate; centering means kept).
# Inference: as in synth_control_perm.py (random draws of pseudo-adopters with real adoption quarters; Monte Carlo two-sided p).
import sys, numpy as np, pandas as pd
from multiprocessing import Pool
from scipy.optimize import minimize

O = "analysis/outputs/"
L = int(sys.argv[1]) if len(sys.argv) > 1 else 8; NDON = int(sys.argv[2]) if len(sys.argv) > 2 else 500; R = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
K = 150; T0, T1 = 8073, 8092; LAMS = 10.0 ** np.arange(-1, 4.1, 0.5)
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
ids_all = np.concatenate([tg.index.values, don]); nA = len(tg)
W = {v: S.pivot(index="id", columns="t", values=v).reindex(index=ids_all, columns=ts).values for v in set(OUT) | {"ln_n", "n", "spend"} | set(cat)}
DEMO = C.loc[ids_all, ["age", "inc", "hh", "female", "college", "white", "diab", "smoke", "alc", "svy_miss"]].values
BW = [2.0, 1.0, 1.0, 1.0]; NT = 2 * L + 1
c = lambda t: t - T0

def design(g, y):
    s = slice(c(g - L), c(g)); n = W["n"][:, s].sum(1).clip(min=1)
    mix = np.column_stack([W[v][:, s].sum(1) / n for v in cat] + [np.log1p(W["spend"][:, s].sum(1))])
    Bs = [W[y][:, s], W["ln_n"][:, s] if y != "ln_n" else np.empty((len(ids_all), 0)), mix, DEMO]
    X = []
    for b, B in zip(BW, Bs):
        if B.shape[1] == 0: continue
        sd = B[nA:].std(0); sd[sd < 1e-8] = 1
        X.append(B * (np.sqrt(b / B.shape[1]) / sd))
    return np.hstack(X)

def sc_weights(X, x):
    n = X.shape[0]
    f = lambda w: np.sum((x - w @ X) ** 2); g = lambda w: 2 * X @ (w @ X - x)
    return minimize(f, np.full(n, 1 / n), jac=g, bounds=[(0, 1)] * n, constraints={"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(n)},
                    method="SLSQP", options={"maxiter": 200}).x

def task(a):
    """returns (lambda, array rows x 2 x NT): SC gap path and augmented gap path for each unit row."""
    y, g, rows, drop_self = a
    X = design(g, y); cols = slice(c(g - L), c(g + L) + 1); Y = W[y][:, cols]
    Xd, Yd = X[nA:], Y[nA:]; mx, my = Xd.mean(0), Yd.mean(0); Xc, Yc = Xd - mx, Yd - my
    U, sv, Vt = np.linalg.svd(Xc, full_matrices=False); post = Yc[:, L + 1:].mean(1)
    uy = U.T @ post; best = (np.inf, None)
    for lam in LAMS:                       # leave-one-donor-out error of the mean post outcome, closed form
        sh = sv ** 2 / (sv ** 2 + lam); h = (U ** 2 * sh).sum(1); fit = U @ (sh * uy)
        err = np.mean(((post - fit) / (1 - h)) ** 2)
        if err < best[0]: best = (err, lam)
    lam = best[1]; XtX = Xc.T @ Xc; XtY = Xc.T @ Yc; I = np.eye(X.shape[1]); out = np.zeros((len(rows), 2, NT))
    for k, r in enumerate(rows):
        d = ((Xd - X[r]) ** 2).sum(1)
        if drop_self: d[r - nA] = np.inf
        near = np.argsort(d)[:K]; w = sc_weights(Xd[near], X[r])
        sc = Y[r] - w @ Yd[near]
        A, B = XtX, XtY
        if drop_self:
            xr = Xc[r - nA]; A = XtX - np.outer(xr, xr); B = XtY - np.outer(xr, Yc[r - nA])
        beta = np.linalg.solve(A + lam * I, B)
        out[k, 0] = sc; out[k, 1] = sc - (X[r] - w @ Xd[near]) @ beta
    return lam, out

if __name__ == "__main__":
    rng = np.random.default_rng(7)
    gs = sorted(tg.unique()); samp = rng.choice(len(don), size=min(NDON, len(don)), replace=False) + nA
    obs_rows = {g: list(np.where(tg.values == g)[0]) for g in gs}
    print(f"L={L}: adopters {nA}, donors {len(don)}, sampled placebo donors {len(samp)}, cohorts {gs}, R={R}", flush=True)
    tasks = [(y, g, obs_rows[g], False) for y in OUT for g in gs] + [(y, g, list(samp), True) for y in OUT for g in gs]
    with Pool(12) as pool: out = pool.map(task, tasks, chunksize=1)
    res = {(t[0], t[1], t[3]): o for t, o in zip(tasks, out)}
    share = tg.value_counts(normalize=True).reindex(gs).values
    rows, es = [], []
    for y, name in OUT.items():
        obs = np.concatenate([res[(y, g, False)][1] for g in gs])           # nA x 2 x NT
        lams = {g: res[(y, g, False)][0] for g in gs}
        T = np.stack([res[(y, g, True)][1] for g in gs])                     # cohorts x donors x 2 x NT
        pm = lambda a: a[..., L + 1:].mean(-1)
        gdraw = rng.choice(len(gs), size=(R, nA), p=share); jdraw = np.array([rng.choice(len(samp), size=nA, replace=False) for _ in range(R)])
        rec = dict(L=L, outcome=y, name=name, lam=np.mean(list(lams.values())))
        for m, lab in [(0, "sc"), (1, "aug")]:
            att = pm(obs[:, m]).mean(); se = pm(obs[:, m]).std(ddof=1) / np.sqrt(nA)
            perm = pm(T[:, :, m])[gdraw, jdraw].mean(1)
            rec.update({f"att_{lab}": att, f"se_{lab}": se, f"perm_sd_{lab}": perm.std(),
                        f"p_{lab}": (1 + (np.abs(perm) >= abs(att)).sum()) / (R + 1)})
            for k, e in enumerate(range(-L, L + 1)):
                es.append(dict(L=L, method=lab, kind="adopters", outcome=y, name=name, e=e, att=obs[:, m, k].mean(), se=obs[:, m, k].std(ddof=1) / np.sqrt(nA)))
                pl = T[:, :, m, k]                                          # cohorts x donors
                es.append(dict(L=L, method=lab, kind="placebo", outcome=y, name=name, e=e, att=float((pl.mean(1) * share).sum()), se=float(pl.std() / np.sqrt(nA))))
        rec.update(pre_rmse_sc=np.sqrt((obs[:, 0, :L] ** 2).mean()), pre_rmse_aug=np.sqrt((obs[:, 1, :L] ** 2).mean()),
                   e_m1_sc=obs[:, 0, L - 1].mean(), e_m1_aug=obs[:, 1, L - 1].mean())
        rows.append(rec); print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()}, flush=True)
    pd.DataFrame(rows).to_csv(O + f"synth_aug_summary_L{L}.csv", index=False); pd.DataFrame(es).to_csv(O + f"synth_aug_eventstudy_L{L}.csv", index=False)
