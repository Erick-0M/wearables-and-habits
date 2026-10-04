"""LaTeX table of randomization p-values (issue #9). Run in container from /home/repo-intro after synth_control_perm.py (L=8 and L=6)."""
import pandas as pd
O = "analysis/outputs/"
a = pd.read_csv(O + "synth_perm_L8.csv").set_index("outcome"); b = pd.read_csv(O + "synth_perm_L6.csv").set_index("outcome")
f = lambda p: "<0.001" if p < 0.001 else f"{p:.3f}"
t = pd.DataFrame({"Outcome": a.name.str.replace("&", r"\&").str.replace("#", r"\#"),
                  "L=8 ATT": a.att.map("{:.3f}".format), "L=8 perm. SD": a.perm_sd.map("{:.3f}".format), "L=8 p": a.p_two_sided.map(f),
                  "L=6 ATT": b.att.map("{:.3f}".format), "L=6 perm. SD": b.perm_sd.map("{:.3f}".format), "L=6 p": b.p_two_sided.map(f)})
open(O + "synth_perm_tab.tex", "w").write(t.to_latex(index=False, escape=False, column_format="lrrrrrr"))
