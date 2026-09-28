"""Overlay balance curves of the original EA and a rebuild test.

Usage: python3 tools/compare_backtests.py original.csv rebuild.csv out.png "Rebuild label"
"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def load(path):
    d = pd.read_csv(path, sep="\t")
    d.columns = ["date", "balance", "equity", "load"]
    d["date"] = pd.to_datetime(d["date"], format="%Y.%m.%d %H:%M")
    chg = d["balance"].diff()
    deals = chg[chg.abs() > 0.3]
    return d, len(deals), (deals > 0).mean() * 100, (deals < -10).sum()


orig, rebuild, out = sys.argv[1:4]
label = sys.argv[4] if len(sys.argv) > 4 else "Rebuild"
fig, ax = plt.subplots(figsize=(11, 4.2), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
for path, name, color in ((orig, "Original EA", "#2a78d6"), (rebuild, label, "#eb6834")):
    d, n, win, big = load(path)
    ax.plot(d.date, d.balance, drawstyle="steps-post", lw=2, color=color,
            label=f"{name}: {n} deals, {win:.0f}% win, {big} losses < -$10")
ax.set_title("Balance: original vs rebuild", loc="left", fontweight="bold")
ax.set_ylabel("USD")
ax.grid(color="#e6e5e0", lw=0.6)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.legend(frameon=False, loc="upper left")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
fig.tight_layout(); fig.savefig(out, dpi=130)
