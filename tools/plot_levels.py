"""Plot strategy B's most-recent-D1-fractal buy level against the original's orders.

Usage: python3 tools/plot_levels.py data/XAUUSD_H1.csv data/original_orders.csv docs/images
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

H1, ORD, OUT = (sys.argv[1:4] + ["data/XAUUSD_H1.csv", "data/original_orders.csv", "docs/images"][len(sys.argv) - 1:])[:3]
h = pd.read_csv(H1, sep="\t")
h.columns = [c.strip("<>").lower() for c in h.columns]
h["t"] = pd.to_datetime(h.date + " " + h.time, format="%Y.%m.%d %H:%M:%S")
h = h.set_index("t")
d = h.resample("D").agg({"high": "max", "low": "min"}).dropna()

# most recent up fractal (2 bars each side) known at the start of each day
hi = d.high.values
up = [False] * len(d)
for i in range(2, len(d) - 2):
    up[i] = hi[i] >= hi[i - 2:i].max() and hi[i] > hi[i + 1:i + 3].max()
lvl = []
for pos in range(len(d)):
    last = pos - 3                       # newest bar with 2 closed bars after it
    idx = [j for j in range(max(0, last - 60), last + 1) if up[j]]
    lvl.append(hi[idx[-1]] * (1 - 0.00064) if idx else np.nan)
level = pd.Series(lvl, index=d.index)

o = pd.read_csv(ORD)
o = o[(o.comment.str.endswith("_3")) & o.type.str.startswith("buy")]
o["t"] = pd.to_datetime(o.open, format="%Y.%m.%d %H:%M:%S")

a, b = "2025-03-01", "2025-10-01"
fig, ax = plt.subplots(figsize=(11, 4.4), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
ax.plot(h.loc[a:b].index, h.loc[a:b].close, color="#b5b4ad", lw=0.8, label="XAUUSD H1 close")
ax.step(level.loc[a:b].index, level.loc[a:b], where="post", color="#2a78d6", lw=1.6,
        label="EA v1.50: latest D1 fractal high - 0.064%")
oo = o[(o.t >= a) & (o.t < b)]
ax.scatter(oo.t, oo.price, s=46, color="#eb6834", edgecolor="#fcfcfb", lw=1.5, zorder=4,
           label="Original EA: strategy B buy stop placed")
ax.set_title("Strategy B entry level: rebuilt rule vs original orders", loc="left", fontweight="bold")
ax.grid(color="#e6e5e0", lw=0.6)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(f"{OUT}/10_level_match_B.png", dpi=130)
