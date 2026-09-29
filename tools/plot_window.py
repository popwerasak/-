"""Chart one date window: price, the EA's entries, and which ones a filter blocks.

Usage: python3 tools/plot_window.py data/XAUUSD_H1.csv data/base_ea_trades_features.csv docs/images
"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

H1, TR, OUT = (sys.argv[1:4] + ["data/XAUUSD_H1.csv", "data/base_ea_trades_features.csv", "docs/images"][len(sys.argv) - 1:])[:3]
A, B = "2025-10-01", "2025-11-10"
ATR, STRETCH = 0.48, 3.0

h = pd.read_csv(H1, sep="\t")
h.columns = [c.strip("<>").lower() for c in h.columns]
h["t"] = pd.to_datetime(h.date + " " + h.time, format="%Y.%m.%d %H:%M:%S")
h = h.set_index("t").loc[A:B]
T = pd.read_csv(TR, parse_dates=["t_in"])
T = T[(T.t_in >= A) & (T.t_in < B)]
T["blocked"] = (T.atr_h1 > ATR) & (T.ext_dir > STRETCH)

fig, ax = plt.subplots(figsize=(11, 4.6), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
ax.plot(h.index, h.close, color="#b5b4ad", lw=1, label="XAUUSD H1 close")
ax.axvspan(pd.Timestamp("2025-10-07"), pd.Timestamp("2025-11-08"), color="#2a78d6", alpha=0.05)
for (blk, win), g in T.groupby([T.blocked, T.pl > 0]):
    color = "#2a78d6" if win else "#e34948"
    label = ("blocked " if blk else "") + ("win" if win else "loss")
    ax.scatter(g.t_in, g.entry, s=90 if blk else 46, marker="X" if blk else "o", color=color,
               edgecolor="#0b0b0b" if blk else "#fcfcfb", lw=1.2, zorder=4, label=label)
saved = -T[T.blocked & (T.t_in >= "2025-10-07") & (T.t_in < "2025-11-08")].pl.sum()
ax.set_title(f"Oct 7 - Nov 7 2025: parabolic filter (H1 ATR > {ATR}% and > {STRETCH}% from D1 EMA20) "
             f"saves {saved:.0f} USD", loc="left", fontweight="bold", fontsize=11)
ax.grid(color="#e6e5e0", lw=0.6)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.legend(frameon=False, loc="upper left", fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/oct_nov_2025_filter.png", dpi=130)
print(T[["t_in", "strat", "side", "pl", "atr_h1", "ext_dir", "blocked"]].round(2).to_string())
