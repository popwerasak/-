"""Decode pending orders read off the tester screenshots into SL/TP ratios.

Shows that every order falls into one of three SL/TP 'strategies'.
Usage: python3 tools/decode_orders.py docs/images
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/images"
# ticket, placed, type, entry, sl, tp, approx market price when placed
ORDERS = [
    (3,  "2026-01-01 23:10", "buy stop",  4546.32, 4524.62, 4635.27, 4330),
    (4,  "2026-01-01 23:10", "sell stop", 3888.20, 3909.90, 3799.25, 4330),
    (5,  "2026-01-01 23:10", "buy stop",  4547.19, 4532.00, 4618.78, 4330),
    (6,  "2026-01-04 23:05", "sell stop", 4277.23, 4292.45, 4205.48, 4330),
    (9,  "2026-01-07 21:15", "buy stop",  4543.90, 4408.46, 4576.09, 4450),
    (22, "2026-01-29 17:00", "sell stop", 3888.49, 3914.35, 3782.46, 5400),
    (23, "2026-02-01 23:05", "buy stop",  5595.15, 5576.12, 5684.88, 4850),
    (25, "2026-02-02 00:05", "buy stop",  5594.59, 5570.45, 5693.57, 4700),
    (27, "2026-02-04 23:02", "buy stop",  5592.13, 5446.51, 5626.74, 4900),
    (28, "2026-02-05 00:05", "sell stop", 4405.95, 4423.27, 4324.32, 4900),
    (44, "2026-02-20 00:05", "sell stop", 4842.92, 4860.34, 4760.82, 5000),
    (49, "2026-02-25 21:15", "buy stop",  5591.49, 5431.81, 5629.45, 5180),
    (50, "2026-02-26 00:05", "buy stop",  5247.36, 5229.35, 5332.28, 5170),
    (52, "2026-02-26 17:00", "sell stop", 4404.78, 4430.51, 4299.27, 5170),
    (53, "2026-02-27 00:05", "buy stop",  5246.32, 5220.50, 5352.17, 5170),
]

def strat(ratio):
    if ratio < 1:
        return "C"
    return "A" if ratio < 4.4 else "B"

print("| Ticket | Placed | Type | Entry | SL pts | TP pts | TP/SL | SL % of price | Strat |")
print("|---|---|---|---|---|---|---|---|---|")
rows = []
for t, when, typ, e, sl, tp, mkt in ORDERS:
    slp, tpp = abs(e - sl) * 100, abs(tp - e) * 100
    r = tpp / slp
    s = strat(r)
    rows.append((s, slp / 100 / mkt * 100, tpp / 100 / mkt * 100, r))
    print(f"| {t} | {when} | {typ} | {e:.2f} | {slp:.0f} | {tpp:.0f} | {r:.2f} | {slp/100/mkt*100:.2f}% | {s} |")

for s in "ABC":
    x = np.array([r[1:] for r in rows if r[0] == s])
    print(f"Strategy {s}: n={len(x)} SL%={x[:,0].mean():.2f} TP%={x[:,1].mean():.2f} TP/SL={x[:,2].mean():.2f}")

# Scatter: SL distance vs TP distance, coloured by strategy.
colors = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a"}
labels = {"A": "A  breakout, TP = 4.1 x SL", "B": "B  breakout, TP = 4.7 x SL",
          "C": "C  wide SL, TP = 0.24 x SL"}
fig, ax = plt.subplots(figsize=(8, 4.6), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
for s in "ABC":
    pts = [(abs(o[3] - o[4]), abs(o[5] - o[3])) for o, r in zip(ORDERS, rows) if r[0] == s]
    xs, ys = zip(*pts)
    ax.scatter(xs, ys, s=70, color=colors[s], edgecolor="#fcfcfb", lw=2, label=labels[s], zorder=3)
ax.set_xscale("log"); ax.set_yscale("log")
for axis in (ax.xaxis, ax.yaxis):
    axis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    axis.set_minor_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}" if str(int(v))[0] in "25" else ""))
ax.set_xlabel("SL distance (USD)"); ax.set_ylabel("TP distance (USD)")
ax.set_title("Decoded pending orders fall into 3 SL/TP profiles", loc="left", fontweight="bold")
ax.grid(color="#e6e5e0", lw=0.6)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.legend(frameon=False, loc="upper right")
fig.tight_layout(); fig.savefig(f"{OUT}/06_decoded_orders.png", dpi=130); plt.close(fig)

# Schematic of how orders are placed around a price channel.
rng = np.random.default_rng(7)
n = 220
x = np.arange(n)
p = 4300 + 60 * np.sin(x / 18) + rng.normal(0, 7, n)
p[170:] = p[169] + np.cumsum(np.abs(rng.normal(4, 6, n - 170)))
hi, lo = p[:170].max(), p[:170].min()
fig, ax = plt.subplots(figsize=(11, 5), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
ax.plot(range(n), p, color="#52514e", lw=1.3)
ax.axhline(hi, color="#2a78d6", lw=1.5, ls="--")
ax.axhline(lo, color="#2a78d6", lw=1.5, ls="--")
ax.text(2, hi + 6, "Highest high of lookback -> BUY STOP (slightly below)", color="#0b0b0b")
ax.text(2, lo - 16, "Lowest low of lookback -> SELL STOP (slightly above)", color="#0b0b0b")
ax.axvspan(0, 170, color="#2a78d6", alpha=0.05)
ax.text(85, hi + 22, "lookback window", ha="center", color="#52514e")
entry = 170 + int(np.argmax(p[170:] > hi))
sl = p[entry] - 0.005 * p[entry]
ax.axhline(sl, xmin=entry / n, color="#e34948", lw=1.2)
ax.text(entry + 2, sl - 14, "SL = % of price", color="#e34948")
ax.scatter([entry], [p[entry]], s=80, color="#1baf7a", zorder=4, edgecolor="#fcfcfb", lw=2)
ax.annotate("breakout fills buy stop", (entry, p[entry]), xytext=(-190, 40),
            textcoords="offset points", arrowprops=dict(arrowstyle="->", color="#52514e"))
trail = [p[max(entry, i - 6):i + 1].min() for i in range(entry, n)]
ax.step(range(entry, n), np.maximum.accumulate(np.maximum(trail, sl)), where="post",
        color="#eb6834", lw=1.6)
ax.text(n - 45, 4480, "trailing SL = low of\nlast N bars (HL trail)", ha="right", color="#eb6834")
ax.set_title("How the EA places and manages orders", loc="left", fontweight="bold")
ax.set_xticks([]); ax.set_ylabel("price")
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/07_strategy_schematic.png", dpi=130); plt.close(fig)
