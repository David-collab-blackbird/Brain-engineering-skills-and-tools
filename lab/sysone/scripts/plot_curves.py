"""Label-count curves ('self-learning'): accuracy and ECE vs number of labels, per job, for the linear-head arm
(and temperature-only reference). Static PNG for the report: results/curves.png (light) + curves_dark.png.
Palette: dataviz reference categorical slots (validated with validate_palette.js); <=5 series per panel with legend +
direct end labels; one y-axis per panel.
  python3 -I plot_curves.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze import JOBS
from common import RES

A = json.load(open(f"{RES}/analysis.json"))
SHORT = {"laya": "Laya", "julia": "Julia-1", "jeff": "Jeff", "jeff_ground": "Jeff+ground", "qwen06": "Qwen3-0.6B",
         "bge_rr": "bge-reranker", "nli_xs": "NLI-xsmall"}
THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e7e6e2",
                  series=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", grid="#33322f",
                 series=["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9"]),
}
ORDER = ["nli_xs", "bge_rr", "julia", "laya", "qwen06", "jeff", "jeff_ground"]


def draw(theme):
    T = THEMES[theme]
    jobs = [j for j in ["J1", "J2", "J3t", "J3a", "J4"] if j in A]
    fig, axes = plt.subplots(2, len(jobs), figsize=(4.2 * len(jobs), 7), facecolor=T["surface"])
    for c, job in enumerate(jobs):
        models = [m for m in ORDER if m in A[job] and A[job][m].get("curve")]
        for r, metric in enumerate(["acc", "ece"]):
            ax = axes[r][c]
            ax.set_facecolor(T["surface"])
            for s in ax.spines.values():
                s.set_color(T["grid"])
            ax.tick_params(colors=T["ink2"], labelsize=8)
            ax.grid(color=T["grid"], linewidth=1)
            ax.set_axisbelow(True)
            for k, m in enumerate(models):
                col = T["series"][ORDER.index(m) % len(T["series"])]
                cv = A[job][m]["curve"]
                Ns = sorted(cv, key=int)
                x0 = [1] + [int(n) for n in Ns]
                z = A[job][m]["zero_shot_raw"][metric]
                y = [z] + [cv[n]["linear_head"][metric][0] for n in Ns if "linear_head" in cv[n]]
                x = x0[: len(y)]
                ax.plot(x, y, color=col, linewidth=2, solid_capstyle="round", label=SHORT[m])
                ax.scatter(x, y, s=36, color=col, edgecolors=T["surface"], linewidths=2, zorder=3)
                ax.annotate(SHORT[m], (x[-1], y[-1]), xytext=(4, 0), textcoords="offset points", fontsize=7,
                            color=T["ink2"], va="center")
            ax.set_xscale("log")
            ax.set_xticks([1, 50, 200, 1000])
            ax.set_xticklabels(["0", "50", "200", "1k"])
            ax.set_xlim(0.8, 3000)
            if r == 0:
                ax.set_title(JOBS[job], color=T["ink"], fontsize=10, loc="left")
            if c == 0:
                ax.set_ylabel("accuracy (test, world s2)" if metric == "acc" else "ECE (lower is better)", color=T["ink2"], fontsize=9)
            if r == 1:
                ax.set_xlabel("labels from the brain's own pool (0 = zero-shot)", color=T["ink2"], fontsize=8)
    h, l = axes[0][0].get_legend_handles_labels()
    leg = fig.legend(h, l, loc="upper center", ncol=len(l), frameon=False, fontsize=9, bbox_to_anchor=(0.5, 1.0))
    for t in leg.get_texts():
        t.set_color(T["ink"])
    fig.suptitle("Self-learning curve: linear head on frozen features + zero-shot logits (mean of 5 resamples)",
                 color=T["ink"], fontsize=11, y=1.04)
    fig.tight_layout()
    out = f"{RES}/curves{'' if theme == 'light' else '_dark'}.png"
    fig.savefig(out, dpi=130, facecolor=T["surface"], bbox_inches="tight")
    print(out)


if __name__ == "__main__":
    draw("light")
    draw("dark")
