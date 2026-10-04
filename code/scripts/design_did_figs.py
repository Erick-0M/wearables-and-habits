"""Figures/tables from design_did_eventstudy.csv / design_did_summary.csv (issue #7). Run in container from /home/repo-intro."""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
O = "analysis/outputs/"
E = pd.read_csv(O + "design_did_eventstudy.csv"); S = pd.read_csv(O + "design_did_summary.csv")
E["se"] = E.se.fillna(0)

def grid(spec, grp, outs, fn, ncol=3):
    d = E[(E.spec == spec) & (E.grp == grp) & E.outcome.isin(outs)]
    nr = int(np.ceil(len(outs) / ncol)); fig, ax = plt.subplots(nr, ncol, figsize=(4.2 * ncol, 2.9 * nr), squeeze=False)
    for a, o in zip(ax.ravel(), outs):
        x = d[d.outcome == o].sort_values("e")
        if x.empty: a.axis("off"); continue
        a.axhline(0, c="grey", lw=.6); a.axvline(-1, c="grey", lw=.6, ls=":")
        a.errorbar(x.e, x.att, yerr=1.96 * x.se, fmt="o", ms=3, lw=1, c="#1f4e79")
        a.set_title(x.name.iloc[0], fontsize=8); a.tick_params(labelsize=7)
    for a in ax.ravel()[len(outs):]: a.axis("off")
    fig.supxlabel("Quarters relative to adoption (reference: $t=-1$)", fontsize=8); fig.tight_layout(); fig.savefig(O + fn, dpi=150); plt.close(fig)

main = ["run_shoe_d", "run_any_d", "fit_gear_d", "supp_d", "med_d"]
plac = ["pet_d", "book_d", "giftcard_d", "cable_d", "cleaning_d", "grocery_d", "ln_shoe_price", "ln_n", "ln_spend"]
grid("main_all", "all", main, "design_es_main.png"); grid("main_all", "all", plac, "design_es_placebo.png")
grid("shoe_all", "all", ["wear_d", "run_noshoe_d", "fit_gear_d", "supp_d", "run_shoe_d", "med_d"], "design_es_shoe_treat.png")
# bundlers vs non-bundlers overlay
fig, ax = plt.subplots(1, 3, figsize=(12, 3.2))
for a, o in zip(ax, ["run_shoe_x", "run_any_x", "fit_gear_d"]):
    for g, c, off in [("bundlers", "#c0392b", -.1), ("nonbundlers", "#1f4e79", .1)]:
        x = E[(E.spec == "bundle_g") & (E.grp == g) & (E.outcome == o)].sort_values("e")
        a.errorbar(x.e + off, x.att, yerr=1.96 * x.se, fmt="o", ms=3, lw=1, c=c, label=g)
    a.axhline(0, c="grey", lw=.6); a.axvline(-1, c="grey", lw=.6, ls=":"); a.set_title(x.name.iloc[0], fontsize=8); a.tick_params(labelsize=7)
ax[0].legend(fontsize=7); fig.supxlabel("Quarters relative to adoption (reference: $t=-1$)", fontsize=8); fig.tight_layout(); fig.savefig(O + "design_es_bundle.png", dpi=150); plt.close(fig)

# summary tables
def tab(df, fn):
    df = df.copy(); df["est"] = df.post_att.map("{:.3f}".format) + " (" + df.post_se.map("{:.3f}".format) + ")"
    df["Pre-test p"] = df.pre_p.map(lambda p: "n/a" if pd.isna(p) else f"{p:.3f}")
    t = df[["name", "est", "Pre-test p", "n_treated"]].rename(columns={"name": "Outcome", "est": "Post ATT (SE)", "n_treated": "N treated"})
    t["Outcome"] = t.Outcome.str.replace("&", r"\&").str.replace("_", r"\_").str.replace("#", r"\#")
    open(O + fn, "w").write(t.to_latex(index=False, escape=False, column_format="lrrr"))
tab(S[(S.spec == "main_all")], "design_tab_main_all.tex"); tab(S[(S.spec == "main_clean")], "design_tab_main_clean.tex")
# bundle: difference
b = S[S.spec == "bundle_g"].pivot(index=["outcome", "name"], columns="grp", values=["post_att", "post_se", "n_treated"])
b.columns = ["_".join(c) for c in b.columns]; b = b.reset_index()
b["diff"] = b.post_att_bundlers - b.post_att_nonbundlers; b["se"] = np.hypot(b.post_se_bundlers, b.post_se_nonbundlers)
f = lambda a, s: a.map("{:.3f}".format) + " (" + s.map("{:.3f}".format) + ")"
t = pd.DataFrame({"Outcome": b.name, "Bundlers (N=30)": f(b.post_att_bundlers, b.post_se_bundlers),
                  "Non-bundlers (N=540)": f(b.post_att_nonbundlers, b.post_se_nonbundlers), "Difference": f(b["diff"], b.se)})
open(O + "design_tab_bundle.tex", "w").write(t.to_latex(index=False, column_format="lrrr"))
tab(S[(S.spec == "shoe_all")], "design_tab_shoe_treat.tex"); tab(S[(S.spec == "shoe_noadopt")], "design_tab_shoe_noadopt.tex")
print(t)
