"""Figures/tables for the augmented synthetic control (issue #9). Run in container from /home/repo-intro after synth_control_aug.py (L=8 and L=6)."""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
O = "analysis/outputs/"
f = lambda p: "<0.001" if p < 0.001 else f"{p:.3f}"
for L in [8, 6]:
    S = pd.read_csv(O + f"synth_aug_summary_L{L}.csv"); E = pd.read_csv(O + f"synth_aug_eventstudy_L{L}.csv")
    t = pd.DataFrame({"Outcome": S.name.str.replace("&", r"\&").str.replace("#", r"\#"),
                      "SC ATT": S.att_sc.map("{:.3f}".format), "SC p": S.p_sc.map(f),
                      "Aug. ATT (SE)": S.att_aug.map("{:.3f}".format) + " (" + S.se_aug.map("{:.3f}".format) + ")", "Aug. p": S.p_aug.map(f),
                      r"$e{=}{-}1$ SC": S.e_m1_sc.map("{:.3f}".format), r"$e{=}{-}1$ Aug.": S.e_m1_aug.map("{:.3f}".format),
                      "Pre RMSE SC": S.pre_rmse_sc.map("{:.3f}".format), "Pre RMSE Aug.": S.pre_rmse_aug.map("{:.3f}".format)})
    open(O + f"synth_aug_tab_L{L}.tex", "w").write(t.to_latex(index=False, escape=False, column_format="lrrrrrrrr"))
    for outs, tag in [(["run_shoe_d", "run_any_d", "fit_gear_d", "supp_d", "med_d"], "main"), (["pet_d", "book_d", "grocery_d", "ln_n"], "placebo")]:
        nr = int(np.ceil(len(outs) / 3)); fig, ax = plt.subplots(nr, 3, figsize=(12.6, 2.9 * nr), squeeze=False)
        for a, o in zip(ax.ravel(), outs):
            a.axhline(0, c="grey", lw=.6); a.axvline(-.5, c="grey", lw=.6, ls=":")
            for m, k, c, off, lab in [("sc", "adopters", "#9aa5b1", -.15, "adopters, SC"), ("aug", "adopters", "#1f4e79", 0, "adopters, augmented"), ("aug", "placebo", "#c0392b", .15, "placebo, augmented")]:
                x = E[(E.outcome == o) & (E.method == m) & (E.kind == k)].sort_values("e")
                a.errorbar(x.e + off, x.att, yerr=1.96 * x.se, fmt="o", ms=3, lw=1, c=c, label=lab); a.set_title(x.name.iloc[0], fontsize=8)
            a.tick_params(labelsize=7)
        for a in ax.ravel()[len(outs):]: a.axis("off")
        ax[0, 0].legend(fontsize=6); fig.supxlabel("Quarters relative to adoption (0 = adoption quarter; gap = adopter minus synthetic)", fontsize=8)
        fig.tight_layout(); fig.savefig(O + f"synth_aug_es_{tag}_L{L}.png", dpi=150); plt.close(fig)
