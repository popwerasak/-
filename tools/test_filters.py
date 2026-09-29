"""Score candidate entry filters against a tester report's trades.

A filter blocks a trade when the condition at entry time is true. Removed
P/L = what the EA would give up (wins) or avoid (losses). A good filter has
positive "saved" over the full period, not just in one bad month.

Usage: python3 tools/test_filters.py data/XAUUSD_H1.csv data/base_ea_trades.csv
"""
import sys
import numpy as np
import pandas as pd

H1 = sys.argv[1] if len(sys.argv) > 1 else "data/XAUUSD_H1.csv"
TR = sys.argv[2] if len(sys.argv) > 2 else "data/base_ea_trades.csv"

h = pd.read_csv(H1, sep="\t")
h.columns = [c.strip("<>").lower() for c in h.columns]
h["t"] = pd.to_datetime(h.date + " " + h.time, format="%Y.%m.%d %H:%M:%S")
h = h.set_index("t")[["open", "high", "low", "close"]]
tr = pd.concat([h.high - h.low, (h.high - h.close.shift()).abs(), (h.low - h.close.shift()).abs()], axis=1).max(axis=1)
h["atr_h1"] = tr.rolling(14).mean() / h.close * 100                       # H1 ATR %
d = h.resample("D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
dtr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
d["atr_d1"] = dtr.rolling(14).mean() / d.close * 100                      # D1 ATR %
d["ema20"] = d.close.ewm(span=20).mean()
d["ext"] = (d.close / d.ema20 - 1) * 100                                    # stretch from D1 EMA20
d["rng_prev"] = (d.high - d.low) / d.close * 100                            # yesterday's range %
h["ema200"] = h.close.ewm(span=200).mean()

T = pd.read_csv(TR, parse_dates=["t_in", "t_out"])
T["buy"] = T.side == "buy"
# features known at entry: last closed H1 bar and last closed D1 bar
hb = h.shift(1).reindex(T.t_in.dt.floor("h")).reset_index(drop=True)
db = d.shift(1).reindex(T.t_in.dt.normalize()).reset_index(drop=True)
T["atr_h1"] = hb.atr_h1.values
T["atr_d1"] = db.atr_d1.values
T["ext_dir"] = np.where(T.buy, db.ext.values, -db.ext.values)             # + = stretched in trade direction
T["rng_prev"] = db.rng_prev.values
T["h1_vs_ema200"] = np.where(T.buy, 1, -1) * (hb.close.values / hb.ema200.values - 1) * 100

# prior loss cooldown: an SL loss in the same direction within N hours before entry
def recent_loss(hours):
    out = []
    for _, r in T.iterrows():
        prev = T[(T.t_out < r.t_in) & (T.t_out > r.t_in - pd.Timedelta(hours=hours)) &
                 (T.side == r.side) & (T.pl < -5)]
        out.append(len(prev) > 0)
    return np.array(out)

# second strategy entering the same breakout within 15 minutes
T = T.sort_values("t_in").reset_index(drop=True)
T["twin"] = [((T.t_in < r.t_in) & (T.t_in > r.t_in - pd.Timedelta(minutes=15)) & (T.side == r.side)).any()
             for _, r in T.iterrows()]

win = (T.t_in >= "2025-10-07") & (T.t_in < "2025-11-08")
base_pl, base_win = T.pl.sum(), T[win].pl.sum()
rows = []
def score(name, block):
    b = np.asarray(block) & ~pd.isna(block)
    rows.append((name, int(b.sum()), round(-T.pl[b].sum(), 1), round(-T.pl[b & win].sum(), 1),
                 int((b & (T.pl < -10)).sum()), int((b & (T.pl > 0)).sum())))

for x in [0.45, 0.5, 0.55, 0.6, 0.7, 0.8]:
    score(f"H1 ATR% > {x}", T.atr_h1 > x)
for x in [1.6, 1.8, 2.0, 2.2, 2.5]:
    score(f"D1 ATR% > {x}", T.atr_d1 > x)
for x in [3, 4, 5, 6, 8]:
    score(f"stretch from D1 EMA20 > {x}% (trade dir)", T.ext_dir > x)
for x in [2.5, 3, 4]:
    score(f"yesterday range > {x}%", T.rng_prev > x)
for hrs in [12, 24, 48, 72]:
    score(f"SL loss same side in last {hrs}h", recent_loss(hrs))
score("2nd strategy on same breakout (<15 min)", T.twin)

R = pd.DataFrame(rows, columns=["filter", "blocked", "saved_all$", "saved_Oct7-Nov7$", "big_losses_blocked", "wins_blocked"])
print(f"base: all {base_pl:.1f}  window {base_win:.1f}  trades {len(T)}")
print(R.sort_values("saved_all$", ascending=False).to_string(index=False))
T.to_csv("data/base_ea_trades_features.csv", index=False)
