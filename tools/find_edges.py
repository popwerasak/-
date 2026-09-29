"""Find entry conditions that separate losing trades from winners.

Builds features known at entry time from XAUUSD H1 data, then scans every
feature/threshold as a "block the trade" rule. A rule is kept only if it
saves money in BOTH halves: 2025 (where it is found) and 2026 (a check on
data it was not tuned on).

Usage: python3 tools/find_edges.py data/XAUUSD_H1.csv data/v200_trades.csv
"""
import sys
import numpy as np
import pandas as pd

H1 = sys.argv[1] if len(sys.argv) > 1 else "data/XAUUSD_H1.csv"
TR = sys.argv[2] if len(sys.argv) > 2 else "data/v200_trades.csv"
SPLIT = "2026-01-01"

h = pd.read_csv(H1, sep="\t")
h.columns = [c.strip("<>").lower() for c in h.columns]
h["t"] = pd.to_datetime(h.date + " " + h.time, format="%Y.%m.%d %H:%M:%S")
h = h.set_index("t")[["open", "high", "low", "close"]]
tr = pd.concat([h.high - h.low, (h.high - h.close.shift()).abs(), (h.low - h.close.shift()).abs()], axis=1).max(axis=1)
h["atr"] = tr.rolling(14).mean()
h["atr_pct"] = h.atr / h.close * 100
h["ema50"] = h.close.ewm(span=50).mean()
h["ema200"] = h.close.ewm(span=200).mean()
h["mom3"] = (h.close / h.close.shift(3) - 1) * 100          # last 3 H1 bars move %
h["mom12"] = (h.close / h.close.shift(12) - 1) * 100
h["bar_rng_atr"] = (h.high - h.low) / h.atr                  # last bar range vs ATR
d = h.resample("D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
dtr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
d["atr_d1"] = dtr.rolling(14).mean() / d.close * 100
d["ema20"] = d.close.ewm(span=20).mean()
d["ext"] = (d.close / d.ema20 - 1) * 100
d["rng"] = (d.high - d.low) / d.close * 100
d["ret"] = (d.close / d.open - 1) * 100

T = pd.read_csv(TR, parse_dates=["t_in", "t_out"]).sort_values("t_in").reset_index(drop=True)
sgn = np.where(T.side == "buy", 1, -1)
hb = h.shift(1).reindex(T.t_in.dt.floor("h")).reset_index(drop=True)     # last closed H1
db = d.shift(1).reindex(T.t_in.dt.normalize()).reset_index(drop=True)   # last closed D1
today_open = d.open.reindex(T.t_in.dt.normalize()).values

F = pd.DataFrame({
    "hour": T.t_in.dt.hour,
    "weekday": T.t_in.dt.dayofweek,
    "atr_h1%": hb.atr_pct.values,
    "atr_d1%": db.atr_d1.values,
    "stretch_d1%": sgn * db.ext.values,                  # + = stretched in trade direction
    "yday_range%": db.rng.values,
    "yday_ret_dir%": sgn * db.ret.values,               # + = yesterday moved in trade direction
    "today_move_dir%": sgn * (T.entry.values / today_open - 1) * 100,
    "mom3_dir%": sgn * hb.mom3.values,
    "mom12_dir%": sgn * hb.mom12.values,
    "vs_ema50_dir%": sgn * (hb.close.values / hb.ema50.values - 1) * 100,
    "vs_ema200_dir%": sgn * (hb.close.values / hb.ema200.values - 1) * 100,
    "lastbar_rng/atr": hb.bar_rng_atr.values,
})
F["twin"] = [((T.t_in < r.t_in) & (T.t_in > r.t_in - pd.Timedelta(minutes=15)) & (T.side == r.side)).any()
             for _, r in T.iterrows()]
F["is_B"] = T.strat == "B"
F["is_sell"] = T.side == "sell"

train = (T.t_in < SPLIT).values
test = ~train
pl = T.pl.values
print(f"trades {len(T)}  P/L {pl.sum():.0f}  train {pl[train].sum():.0f}  test {pl[test].sum():.0f}")
print(f"losses < -10: {(pl < -10).sum()} = {pl[pl < -10].sum():.0f} USD\n")

rows = []
for col in F.columns:
    x = F[col].values.astype(float)
    if col in ("twin", "is_B", "is_sell"):
        rules = [(f"{col} == 1", x == 1), (f"{col} == 0", x == 0)]
    elif col in ("hour", "weekday"):
        rules = [(f"{col} == {v:.0f}", x == v) for v in np.unique(x[~np.isnan(x)])]
    else:
        qs = np.nanquantile(x, np.arange(0.1, 0.91, 0.05))
        rules = [(f"{col} > {q:.3f}", x > q) for q in qs] + [(f"{col} < {q:.3f}", x < q) for q in qs]
    for name, b in rules:
        b = b & ~np.isnan(x)
        if b.sum() < 8 or b.mean() > 0.35:
            continue
        s_tr, s_te = -pl[b & train].sum(), -pl[b & test].sum()
        rows.append((name, int(b.sum()), round(s_tr, 1), round(s_te, 1), round(s_tr + s_te, 1),
                     int((b & (pl < -10)).sum()), int((b & (pl > 0)).sum()), round((pl[b] > 0).mean() * 100)))
R = pd.DataFrame(rows, columns=["block if", "n", "saved_2025", "saved_2026", "saved_all",
                                "big_losses_cut", "wins_cut", "win%_of_blocked"])
good = R[(R.saved_2025 > 0) & (R.saved_2026 > 0)].sort_values("saved_all", ascending=False)
print("Rules that save money in BOTH 2025 and 2026:")
print(good.head(40).to_string(index=False))
pd.concat([T, F], axis=1).to_csv("data/v200_trades_features.csv", index=False)
