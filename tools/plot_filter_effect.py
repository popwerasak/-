"""Monthly P/L of a report's trades with and without the v2.20 exhaustion filter.

Usage: python3 tools/plot_filter_effect.py data/v200_trades_features.csv docs/images
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TR = sys.argv[1] if len(sys.argv) > 1 else "data/v200_trades_features.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "docs/images"
T = pd.read_csv(TR, parse_dates=["t_in"])
blk = (T["yday_range%"] > 3.0) | (T["vs_ema50_dir%"] > 1.6)
m = T.assign(blk=blk).groupby(T.t_in.dt.to_period("M")).apply(
    lambda g: pd.Series({"v2.00 (tested)": g.pl.sum(), "v2.20 (estimated)": g[~g.blk].pl.sum()}))
lab = [p.strftime("%y-%m") for p in m.index]
x = np.arange(len(m))
fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), facecolor="#fcfcfb",
                         gridspec_kw={"height_ratios": [2, 1.3]})
for ax in axes:
    ax.set_facecolor("#fcfcfb")
    ax.grid(axis="y", color="#e6e5e0", lw=0.6)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
ax = axes[0]
ax.bar(x - 0.2, m.iloc[:, 0], width=0.38, color="#b5b4ad", label=m.columns[0])
ax.bar(x + 0.2, m.iloc[:, 1], width=0.38, color="#2a78d6", label=m.columns[1])
ax.axhline(0, color="#52514e", lw=0.8)
ax.set_xticks(x, lab, rotation=45, fontsize=8)
ax.set_title("Net P/L per month (USD): exhaustion filter removes the worst entries", loc="left", fontweight="bold")
ax.legend(frameon=False, loc="upper left")
ax = axes[1]
for name, sub, color in (("v2.00", T, "#b5b4ad"), ("v2.20", T[~blk], "#2a78d6")):
    ax.plot(sub.t_in, 1000 + sub.pl.cumsum(), drawstyle="steps-post", color=color, lw=2,
            label=f"{name}: {sub.pl.sum():+.0f} USD, {int((sub.pl < -10).sum())} big losses")
ax.set_title("Balance (same trades, filter applied)", loc="left", fontweight="bold")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(f"{OUT}/v220_filter_effect.png", dpi=130)
