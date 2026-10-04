"""Figures/tables for the balanced-panel synthetic control (issue #9). Run in container from /home/repo-intro after synth_control_balanced.py."""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
O = "analysis/outputs/"
for L in [8, 6]:
    E = pd.read_csv(O + f"synth_bal_eventstudy_L{L}.csv"); S = pd.read_csv(O + f"synth_bal_summary_L{L}.csv")
    for outs, tag in [(["run_shoe_d", "run_any_d", "fit_gear_d", "supp_d", "med_d"], "main"), (["pet_d", "book_d", "grocery_d", "ln_n"], "placebo")]:
        nr = int(np.ceil(len(outs) / 3)); fig, ax = plt.subplots(nr, 3, figsize=(12.6, 2.9 * nr), squeeze=False)
        for a, o in zip(ax.ravel(), outs):
            a.axhline(0, c="grey", lw=.6); a.axvline(-.5, c="grey", lw=.6, ls=":")
            for kind, c, off in [("adopters", "#1f4e79", -.1), ("placebo", "#c0392b", .1)]:
                x = E[(E.outcome == o) & (E.kind == kind)].sort_values("e")
                a.errorbar(x.e + off, x.att, yerr=1.96 * x.se, fmt="o", ms=3, lw=1, c=c, label=kind); a.set_title(x.name.iloc[0], fontsize=8)
            a.tick_params(labelsize=7)
        for a in ax.ravel()[len(outs):]: a.axis("off")
        ax[0, 0].legend(fontsize=7); fig.supxlabel("Quarters relative to adoption (0 = adoption quarter; gap = adopter minus synthetic)", fontsize=8)
        fig.tight_layout(); fig.savefig(O + f"synth_bal_es_{tag}_L{L}.png", dpi=150); plt.close(fig)
    a = S[S.kind == "adopters"].set_index("outcome"); p = S[S.kind == "placebo"].set_index("outcome")
    t = pd.DataFrame({"Outcome": a.name.str.replace("&", r"\&").str.replace("#", r"\#"),
                      "Post ATT (SE)": a.post_att.map("{:.3f}".format) + " (" + a.post_se.map("{:.3f}".format) + ")",
                      "Placebo (SE)": p.post_att.map("{:.3f}".format) + " (" + p.post_se.map("{:.3f}".format) + ")",
                      "N": a.n_units.astype(int), "Pre RMSE / level": a.pre_rmse.map("{:.3f}".format) + " / " + a.pre_rms_level.map("{:.3f}".format)})
    open(O + f"synth_bal_tab_L{L}.tex", "w").write(t.to_latex(index=False, escape=False, column_format="lrrrr"))
    B = pd.read_csv(O + f"synth_bal_covbalance_L{L}.csv")
    B["var"] = B["var"].str.replace("_", r"\_"); 
    for c in ["adopters", "synthetic", "donor_pool"]: B[c] = B[c].map("{:.3f}".format)
    B = B.rename(columns={"var": "Variable", "adopters": "Adopters", "synthetic": "Synthetic", "donor_pool": "Donor pool"}).drop(columns="L")
    open(O + f"synth_bal_tab_balance_L{L}.tex", "w").write(B.to_latex(index=False, escape=False, column_format="lrrr"))
