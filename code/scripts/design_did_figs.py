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

# ---- balanced-panel robustness (design_did_balanced.R)
EB = pd.read_csv(O + "design_did_balanced_eventstudy.csv"); SB = pd.read_csv(O + "design_did_balanced_summary.csv"); EB["se"] = EB.se.fillna(0)
outs = ["run_shoe_d", "run_any_d", "fit_gear_d", "supp_d", "med_d", "pet_d", "book_d", "grocery_d", "ln_n"]
fig, ax = plt.subplots(3, 3, figsize=(12.6, 8.7))
for a, o in zip(ax.ravel(), outs):
    for p, c, off in [("balanced", "#c0392b", -.1), ("unbalanced", "#1f4e79", .1)]:
        x = EB[(EB.spec == "main_all") & (EB.outcome == o) & (EB.panel == p)].sort_values("e")
        a.errorbar(x.e + off, x.att, yerr=1.96 * x.se, fmt="o", ms=3, lw=1, c=c, label=p)
    a.axhline(0, c="grey", lw=.6); a.axvline(-1, c="grey", lw=.6, ls=":"); a.set_title(x.name.iloc[0], fontsize=8); a.tick_params(labelsize=7)
ax[0, 0].legend(fontsize=7); fig.supxlabel("Quarters relative to adoption (reference: $t=-1$)", fontsize=8); fig.tight_layout(); fig.savefig(O + "design_es_balanced.png", dpi=150); plt.close(fig)
f = lambda a, s: a.map("{:.3f}".format) + " (" + s.map("{:.3f}".format) + ")"
for sp in ["main_all", "main_clean"]:
    d = SB[SB.spec == sp].pivot(index=["outcome", "name"], columns="panel", values=["post_att", "post_se"]); d.columns = ["_".join(c) for c in d.columns]
    d = d.reset_index(); d = d.set_index("outcome").loc[[o for o in SB.outcome.unique()]].reset_index()
    t = pd.DataFrame({"Outcome": d.name.str.replace("&", r"\&").str.replace("#", r"\#"), "Balanced": f(d.post_att_balanced, d.post_se_balanced), "Unbalanced (same cohorts)": f(d.post_att_unbalanced, d.post_se_unbalanced)})
    open(O + f"design_tab_balanced_{sp}.tex", "w").write(t.to_latex(index=False, column_format="lrr"))

# ---- lifestyle-conditional (DR) vs unconditional (design_did_lifestyle.R)
EL = pd.read_csv(O + "design_did_lifestyle_eventstudy.csv"); SL = pd.read_csv(O + "design_did_lifestyle_summary.csv"); EL["se"] = EL.se.fillna(0)
for pn in ["balanced", "unbalanced"]:
    fig, ax = plt.subplots(3, 3, figsize=(12.6, 8.7))
    for a, o in zip(ax.ravel(), ["run_shoe_d", "run_any_d", "fit_gear_d", "supp_d", "med_d", "pet_d", "book_d", "grocery_d", "ln_n"]):
        for cd, c, off, lab in [(False, "#1f4e79", -.1, "unconditional"), (True, "#c0392b", .1, "DR + lifestyle")]:
            x = EL[(EL.spec == "main_all") & (EL.outcome == o) & (EL.panel == pn) & (EL.cond == cd)].sort_values("e")
            a.errorbar(x.e + off, x.att, yerr=1.96 * x.se, fmt="o", ms=3, lw=1, c=c, label=lab)
        a.axhline(0, c="grey", lw=.6); a.axvline(-1, c="grey", lw=.6, ls=":"); a.set_title(x.name.iloc[0], fontsize=8); a.tick_params(labelsize=7)
    ax[0, 0].legend(fontsize=7); fig.supxlabel("Quarters relative to adoption (reference: $t=-1$)", fontsize=8); fig.tight_layout()
    fig.savefig(O + f"design_es_lifestyle_{pn}.png", dpi=150); plt.close(fig)
for sp in ["main_all", "main_clean"]:
    for pn in ["balanced", "unbalanced"]:
        d = SL[(SL.spec == sp) & (SL.panel == pn)]
        w_ = d.pivot(index="outcome", columns="cond", values=["mean_pre", "post_att", "post_se"]).reindex(d.outcome.unique())
        nm = d.drop_duplicates("outcome").set_index("outcome").name.reindex(w_.index).str.replace("&", r"\&").str.replace("#", r"\#")
        t = pd.DataFrame({"Outcome": nm, "Pre gap, uncond.": w_[("mean_pre", False)].map("{:.3f}".format), "Pre gap, DR": w_[("mean_pre", True)].map("{:.3f}".format),
                          "Post ATT, uncond.": f(w_[("post_att", False)], w_[("post_se", False)]), "Post ATT, DR": f(w_[("post_att", True)], w_[("post_se", True)])})
        open(O + f"design_tab_lifestyle_{sp}_{pn}.tex", "w").write(t.to_latex(index=False, column_format="lrrrr"))
OVL = pd.read_csv(O + "design_did_lifestyle_overlap.csv"); print(OVL.round(3).to_string())
