"""Monthly P/L vs share of wins that exit at the break-even lock, with H1 ATR.

Usage: python3 tools/plot_be_exits.py data/v200_trades.csv data/XAUUSD_H1.csv docs/images
"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TR, H1, OUT = (sys.argv[1:4] + ["data/v200_trades.csv", "data/XAUUSD_H1.csv", "docs/images"][len(sys.argv) - 1:])[:3]
T = pd.read_csv(TR, parse_dates=["t_in"])
T["m"] = T.t_in.dt.to_period("M")
w = T[T.pl > 0]
be = (w["mv%"] < 0.04).groupby(w.m).mean() * 100
pl = T.groupby("m").pl.sum()

h = pd.read_csv(H1, sep="\t")
h.columns = [c.strip("<>").lower() for c in h.columns]
h["t"] = pd.to_datetime(h.date + " " + h.time, format="%Y.%m.%d %H:%M:%S")
h = h.set_index("t")
tr = pd.concat([h.high - h.low, (h.high - h.close.shift()).abs(), (h.low - h.close.shift()).abs()], axis=1).max(axis=1)
atr = (tr.rolling(14).mean() / h.close * 100).resample("MS").median()
atr.index = atr.index.to_period("M")

idx = pl.index
lab = [p.strftime("%y-%m") for p in idx]
fig, axes = plt.subplots(3, 1, figsize=(11, 7.5), sharex=True, facecolor="#fcfcfb")
for ax in axes:
    ax.set_facecolor("#fcfcfb")
    ax.grid(axis="y", color="#e6e5e0", lw=0.6)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
axes[0].bar(lab, pl.values, color=["#2a78d6" if v >= 0 else "#e34948" for v in pl.values], width=0.7)
axes[0].set_title("v2.00 net P/L per month (USD)", loc="left", fontweight="bold")
axes[1].bar(lab, be.reindex(idx).values, color="#eda100", width=0.7)
axes[1].set_title("Share of winning trades closed at the +0.02% break-even lock (%)", loc="left", fontweight="bold")
axes[2].plot(lab, atr.reindex(idx).values, color="#52514e", lw=2, marker="o", ms=4)
axes[2].axhline(0.25, color="#1baf7a", lw=1.2, ls="--")
axes[2].text(0, 0.27, "v2.10 reference ATR 0.25% (scale = 1 below this)", color="#1baf7a", fontsize=9)
axes[2].set_title("XAUUSD H1 ATR(14), monthly median (% of price)", loc="left", fontweight="bold")
axes[2].tick_params(axis="x", labelrotation=45, labelsize=8)
fig.tight_layout(); fig.savefig(f"{OUT}/2026_break_even_exits.png", dpi=130)
