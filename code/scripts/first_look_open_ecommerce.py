"""Crude first look at Open e-commerce (issue #3). Keyword flags are rough, NOT the audit classification."""
import pandas as pd
D = "build/input/public/open_ecommerce/"
a = pd.read_csv(D + "amazon-purchases.csv", parse_dates=["Order Date"])
s = pd.read_csv(D + "survey.csv")
u = "Survey ResponseID"
c = a["Category"].fillna("").str.lower(); t = a["Title"].fillna("").str.lower()
w = t.str.contains(r"fitbit|garmin|apple watch|smartwatch|fitness tracker|activity tracker|forerunner")
r = t.str.contains(r"running shoe|running shorts|running |runner") | c.str.contains("running")
wd = a[w].groupby(u)["Order Date"].min()
g = a.groupby(u)["Order Date"].agg(["min", "max"]).join(wd.rename("w"), how="inner")
pre = (g.w - g["min"]).dt.days >= 365; post = (g["max"] - g.w).dt.days >= 365
rows = [
    ("Purchase rows", f"{len(a):,}"),
    ("Users with purchases", f"{a[u].nunique():,}"),
    ("Survey respondents", f"{s[u].nunique():,}"),
    ("Order dates", f"{a['Order Date'].min():%Y-%m-%d} to {a['Order Date'].max():%Y-%m-%d}"),
    ("Median purchases per user", f"{a.groupby(u).size().median():.0f}"),
    ("Rows flagged wearable (title keywords)", f"{w.sum():,}"),
    ("Users with a flagged wearable (ever-treated)", f"{wd.shape[0]:,}"),
    ("  of which $\\geq$12 months pre-history", f"{pre.sum():,}"),
    ("  of which $\\geq$12 months pre and post", f"{(pre & post).sum():,}"),
    ("Rows flagged running-related", f"{r.sum():,}"),
    ("Users with a running-related purchase", f"{a[r][u].nunique():,}"),
]
out = "\\begin{tabular}{lr}\\toprule\nItem & Value \\\\\\midrule\n" + "\n".join(f"{k} & {v} \\\\" for k, v in rows) + "\n\\bottomrule\\end{tabular}\n"
open("analysis/outputs/first_look_summary.tex", "w").write(out)
yr = wd.dt.year.value_counts().sort_index()
open("analysis/outputs/first_look_cohorts.tex", "w").write(
    "\\begin{tabular}{" + "r" * len(yr) + "}\\toprule\n" + " & ".join(map(str, yr.index)) + " \\\\\\midrule\n"
    + " & ".join(map(str, yr.values)) + " \\\\\\bottomrule\\end{tabular}\n")
print(out, yr)
