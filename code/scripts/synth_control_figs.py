"""Figures/tables from synth_eventstudy.csv / synth_summary.csv (issue #9). Run in container from /home/repo-intro."""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
O = "analysis/outputs/"
E = pd.read_csv(O + "synth_eventstudy.csv"); S = pd.read_csv(O + "synth_summary.csv")

def grid(match, outs, fn, ncol=3):
    nr = int(np.ceil(len(outs) / ncol)); fig, ax = plt.subplots(nr, ncol, figsize=(4.2 * ncol, 2.9 * nr), squeeze=False)
    for a, o in zip(ax.ravel(), outs):
        a.axhline(0, c="grey", lw=.6); a.axvline(-.5, c="grey", lw=.6, ls=":")
        for kind, c, off in [("adopters", "#1f4e79", -.1), ("placebo", "#c0392b", .1)]:
            x = E[(E.match == match) & (E.outcome == o) & (E.kind == kind)].sort_values("e")
            if x.empty: continue
            a.errorbar(x.e + off, x.att, yerr=1.96 * x.se.fillna(0), fmt="o", ms=3, lw=1, c=c, label=kind)
            a.set_title(x.name.iloc[0], fontsize=8)
        a.tick_params(labelsize=7)
    for a in ax.ravel()[len(outs):]: a.axis("off")
    ax[0, 0].legend(fontsize=7); fig.supxlabel("Quarters relative to adoption (0 = adoption quarter; gap = adopter minus synthetic)", fontsize=8)
    fig.tight_layout(); fig.savefig(O + fn, dpi=150); plt.close(fig)

main = ["run_shoe_d", "run_any_d", "fit_gear_d", "supp_d", "med_d"]; plac = ["pet_d", "book_d", "grocery_d", "ln_n"]
for m, tag in [("own", "own"), ("own+ln_n", "lnn")]:
    grid(m, main, f"synth_es_main_{tag}.png"); grid(m, plac, f"synth_es_placebo_{tag}.png")

def tab(match, fn):
    d = S[S.match == match]; a = d[d.kind == "adopters"].set_index("outcome"); p = d[d.kind == "placebo"].set_index("outcome")
    t = pd.DataFrame({"Outcome": a.name.str.replace("&", r"\&").str.replace("#", r"\#"),
                      "Post ATT (SE)": a.post_att.map("{:.3f}".format) + " (" + a.post_se.map("{:.3f}".format) + ")",
                      "Placebo (SE)": p.post_att.map("{:.3f}".format) + " (" + p.post_se.map("{:.3f}".format) + ")",
                      "N": a.n_units.astype(int), "Pre RMSE / level": a.pre_rmse.map("{:.3f}".format) + " / " + a.pre_rms_level.map("{:.3f}".format)})
    open(O + fn, "w").write(t.to_latex(index=False, escape=False, column_format="lrrrr"))
tab("own", "synth_tab_own.tex"); tab("own+ln_n", "synth_tab_lnn.tex")
