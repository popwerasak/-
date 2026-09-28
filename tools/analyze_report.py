"""Parse an MT5 Strategy Tester report (.xlsx) into orders, deals and trades.

Pairs every exit deal with its entry, then measures per strategy (comment
suffix _1/_2/_3): SL/TP % of the pending orders, how each trade exited,
break-even lock levels and lot sizes. Draws a P/L-by-exit chart.

Usage: python3 tools/analyze_report.py data/original_full_report.xlsx docs/images
"""
import sys
import warnings
import numpy as np
import openpyxl
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
SRC = sys.argv[1] if len(sys.argv) > 1 else "data/original_full_report.xlsx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "docs/images"
NAMES = {"1": "C (wide SL)", "2": "A (TP 4.1xSL)", "3": "B (TP 4.7xSL)"}

rows = [[v for v in r if v is not None]
        for r in openpyxl.load_workbook(SRC, read_only=True).worksheets[0].iter_rows(values_only=True)]
i_orders = next(i for i, r in enumerate(rows) if r == ["Orders"])
i_deals = next(i for i, r in enumerate(rows) if r == ["Deals"])

orders = pd.DataFrame([r for r in rows[i_orders + 2:i_deals] if len(r) == 11],
                      columns=["open", "order", "sym", "type", "vol", "price", "sl", "tp",
                               "time", "state", "comment"])
orders["strat"] = orders.comment.str[-1]

deals = []
for r in rows[i_deals + 2:]:
    if len(r) < 12:
        continue
    r = r + [""] * (13 - len(r))
    t, _, _, typ, dirn, vol, price, order, com, _, pl, bal, cm = r
    deals.append(dict(time=pd.to_datetime(t, format="%Y.%m.%d %H:%M:%S"), type=typ, dir=dirn,
                      vol=float(vol), price=price, order=order, com=com, pl=pl, bal=bal, cm=str(cm)))
deals = pd.DataFrame(deals).sort_values("time", kind="stable")

by_order = orders.set_index("order")
open_pos, trades = [], []
for _, d in deals.iterrows():
    if d.dir == "in":
        od = by_order.loc[d.order]
        open_pos.append(dict(t_in=d.time, side=d.type, vol=d.vol, entry=d.price, sl0=od.sl,
                             tp0=od.tp, strat=d.cm[-1], bal_in=d.bal - d.com))
        continue
    side = "buy" if d.type == "sell" else "sell"
    kind, _, lvl = d.cm.partition(" ")
    lvl = float(lvl) if lvl else np.nan
    cands = [p for p in open_pos if p["side"] == side and abs(p["vol"] - d.vol) < 1e-9]
    match = next((p for p in cands if (kind == "tp" and abs(p["tp0"] - lvl) < 0.02) or
                  (kind == "sl" and abs(p["sl0"] - lvl) < 0.02)), cands[0] if cands else None)
    if match is None:
        continue
    open_pos.remove(match)
    trades.append({**match, "t_out": d.time, "exit": d.price, "pl": d.pl, "kind": kind, "lvl": lvl})

T = pd.DataFrame(trades)
sgn = np.where(T.side == "buy", 1, -1)
T["move_pct"] = (T.exit - T.entry) * sgn / T.entry * 100
T["lock_pct"] = (T.lvl - T.entry) * sgn / T.entry * 100
T["hold_min"] = (T.t_out - T.t_in).dt.total_seconds() / 60
T["exit_type"] = np.select(
    [T.kind == "tp", (T.kind == "sl") & ((T.lvl - T.sl0).abs() < 0.02), T.kind == "sl"],
    ["TP", "Initial SL", "Moved SL (BE/trail)"], default="Closed by EA (fake-out)")

orders["sl_pct"] = (orders.price - orders.sl).abs() / orders.price * 100
orders["tp_pct"] = (orders.tp - orders.price).abs() / orders.price * 100
print("Pending orders per strategy (median % of entry):")
print(orders.groupby("strat").agg(n=("order", "size"), filled=("state", lambda s: (s == "filled").sum()),
                                  sl=("sl_pct", "median"), tp=("tp_pct", "median")).round(3).to_string())
print("\nTrades by exit type:")
print(T.groupby(["strat", "exit_type"]).agg(n=("pl", "size"), pl=("pl", "sum"),
      move=("move_pct", "median"), hold_min=("hold_min", "median")).round(3).to_string())
print("\nLots per strategy:")
print(T.groupby(["strat", "vol"]).size().to_string())

# Chart: P/L per strategy split by exit type
piv = T.pivot_table(index="strat", columns="exit_type", values="pl", aggfunc="sum", fill_value=0)
cols = ["TP", "Moved SL (BE/trail)", "Closed by EA (fake-out)", "Initial SL"]
colors = ["#2a78d6", "#1baf7a", "#eda100", "#e34948"]
piv = piv.reindex(columns=cols, fill_value=0)
fig, ax = plt.subplots(figsize=(11, 4), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
x = np.arange(len(piv))
w = 0.2
for k, (c, col) in enumerate(zip(cols, colors)):
    ax.bar(x + (k - 1.5) * w, piv[c], width=w * 0.9, color=col, label=c)
ax.set_xticks(x, [NAMES.get(s, s) for s in piv.index])
ax.axhline(0, color="#52514e", lw=0.8)
ax.set_ylabel("USD")
ax.set_title("Original EA: P/L by strategy and exit type (2025.01-2026.09)", loc="left", fontweight="bold")
ax.grid(axis="y", color="#e6e5e0", lw=0.6)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.legend(frameon=False, ncol=4, loc="upper right")
fig.tight_layout(); fig.savefig(f"{OUT}/09_original_exit_types.png", dpi=130)

orders.to_csv("data/original_orders.csv", index=False)
deals.to_csv("data/original_deals.csv", index=False)
T.to_csv("data/original_trades.csv", index=False)
