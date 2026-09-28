"""Find each strategy's lookback and entry offset from real price data.

For every pending order of the original EA, compare its price with the
highest high (buy stop) / lowest low (sell stop) of the last N completed
bars before the order was placed. The N whose ratio price/level is most
stable across orders is the lookback; the median ratio is the offset.

Usage: python3 tools/fit_levels.py data/XAUUSD_H1.csv data/original_orders.csv
"""
import sys
import numpy as np
import pandas as pd

H1 = sys.argv[1] if len(sys.argv) > 1 else "data/XAUUSD_H1.csv"
ORD = sys.argv[2] if len(sys.argv) > 2 else "data/original_orders.csv"

h = pd.read_csv(H1, sep="\t")
h.columns = [c.strip("<>").lower() for c in h.columns]
h["t"] = pd.to_datetime(h.date + " " + h.time, format="%Y.%m.%d %H:%M:%S")
h = h.set_index("t")[["open", "high", "low", "close"]]
# Broker D1 bars: the session starts at 00:00 server time.
d1 = h.resample("D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()

o = pd.read_csv(ORD)
o["t"] = pd.to_datetime(o.open, format="%Y.%m.%d %H:%M:%S")
o["strat"] = o.comment.astype(str).str[-1]
o["isbuy"] = o.type.str.startswith("buy")
o = o[o.t >= h.index[0] + pd.Timedelta(days=45)]   # need history for the lookback


def levels(bars, t, n, isbuy, bar_len):
    done = bars[bars.index + bar_len <= t]           # bars fully closed at t
    if len(done) < n:
        return np.nan
    win = done.iloc[-n:]
    return win.high.max() if isbuy else win.low.min()


def fit(bars, bar_len, grid, label):
    print(f"\n=== {label} ===")
    best = {}
    for (s, isbuy), g in o.groupby(["strat", "isbuy"]):
        g = g.drop_duplicates(["price"])             # one row per distinct level
        rows = []
        for n in grid:
            lv = np.array([levels(bars, t, n, isbuy, bar_len) for t in g.t])
            off = (g.price.values / lv - 1) * 100 * (1 if isbuy else -1)
            ok = ~np.isnan(off)
            if ok.sum() < 5:
                continue
            # share of orders explained within +-0.05% of the median offset
            med = np.median(off[ok])
            hit = np.mean(np.abs(off[ok] - med) < 0.05)
            rows.append((n, hit, med, np.std(off[ok]), ok.sum()))
        r = pd.DataFrame(rows, columns=["n", "hit", "offset_med", "offset_std", "orders"])
        top = r.sort_values(["hit", "offset_std"], ascending=[False, True]).head(3)
        print(f"strat {s} {'buy ' if isbuy else 'sell'}:")
        print(top.round(4).to_string(index=False))
        best[(s, isbuy)] = top.iloc[0]
    return best


fit(d1, pd.Timedelta(days=1), range(2, 41), "D1 bars")
fit(h, pd.Timedelta(hours=1), list(range(12, 120, 4)) + list(range(120, 1000, 20)), "H1 bars")
