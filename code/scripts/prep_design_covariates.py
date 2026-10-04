"""Baseline 'lifestyle' covariates for the conditional DiD (issue #7). Exploratory.
Run in research-container from /home/repo-intro (after prep_design_panel.py):  python scripts/prep_design_covariates.py
Baseline = each user's first 4 observed quarters (same rule for adopters and controls). Purchase-profile variables are
compressed to 4 principal components; survey demographics are added with mean imputation + missing indicator.
Writes build/interm/design_covariates.csv (id, covariates, t0 = first observed quarter index).
"""
import numpy as np, pandas as pd
I = "build/interm/"; D = "build/input/public/open_ecommerce/"
P = pd.read_csv(I + "design_panel_q.csv"); M = pd.read_csv(I + "design_id_map.csv")
P["t0"] = P.groupby("id").t.transform("min")
B = P[P.t <= P.t0 + 3]
cnt = ["run_any", "fit_gear", "supp", "med", "pet", "book", "giftcard", "cable", "cleaning", "grocery"]
g = B.groupby("id")[cnt + ["n", "spend"]].sum()
X = pd.DataFrame(index=g.index)
X["ln_n_b"] = np.log1p(g.n); X["ln_spend_b"] = np.log1p(g.spend)
for c in cnt: X[c + "_sh"] = g[c] / g.n.clip(lower=1)
X["any_run_b"] = (g.run_any > 0).astype(float); X["any_fit_b"] = (g.fit_gear > 0).astype(float)
Z = (X - X.mean()) / X.std().replace(0, 1)
U, sv, Vt = np.linalg.svd(Z.values, full_matrices=False)
pcs = pd.DataFrame(U[:, :4] * sv[:4], index=X.index, columns=[f"pc{i}" for i in range(1, 5)])
print("explained variance of 4 PCs:", (sv[:4] ** 2 / (sv ** 2).sum()).round(3))

# survey (same coding as the data audit); missing -> sample mean + missing indicator
S = pd.read_csv(D + "survey.csv").rename(columns={"Survey ResponseID": "uid"})
S["age"] = S["Q-demos-age"].map({x: i for i, x in enumerate(sorted(S["Q-demos-age"].dropna().unique()))})
inc = ["Less than $25,000", "$25,000 - $49,999", "$50,000 - $74,999", "$75,000 - $99,999", "$100,000 - $149,999", "$150,000 or more"]
S["inc"] = S["Q-demos-income"].map({k: i for i, k in enumerate(inc)})
yn = lambda c, v="Yes": (S[c] == v).astype(float).where(S[c].notna() & (S[c] != "Prefer not to say"))
S["female"] = yn("Q-demos-gender", "Female")
S["college"] = S["Q-demos-education"].fillna("").str.contains("Bachelor|Graduate|graduate|degree").astype(float).where(S["Q-demos-education"].notna())
S["white"] = yn("Q-demos-race", "White or Caucasian")
S["hh"] = S["Q-amazon-use-hh-size"].replace({"4+": 4, "1 (just me!)": 1}).astype(float)
S["diab"] = yn("Q-personal-diabetes"); S["smoke"] = yn("Q-substance-use-cigarettes"); S["alc"] = yn("Q-substance-use-alcohol")
sv_cols = ["age", "inc", "hh", "female", "college", "white", "diab", "smoke", "alc"]
S = M.merge(S[["uid"] + sv_cols], on="uid", how="left").set_index("id")
print("users in map:", len(M), " matched to survey:", S[sv_cols].notna().any(axis=1).sum(), " missing by var:", S[sv_cols].isna().sum().to_dict())
S["svy_miss"] = S[sv_cols].isna().any(axis=1).astype(float)
S[sv_cols] = S[sv_cols].fillna(S[sv_cols].mean())
C = pcs.join(X[["ln_n_b"]]).join(S[sv_cols + ["svy_miss"]]); C["t0"] = P.groupby("id").t0.first()
assert len(C) == P.id.nunique() and C.drop(columns=[]).notna().all().all(), "N changed or NaN in covariates"
C.reset_index().to_csv(I + "design_covariates.csv", index=False); print(C.shape)
