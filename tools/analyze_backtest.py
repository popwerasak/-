"""Analyze an MT5 tester-graph CSV export and draw report charts.

Usage: python3 tools/analyze_backtest.py data/backtest_equity_2026.csv docs/images
"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/backtest_equity_2026.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "docs/images"

BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "axes.titlelocation": "left",
})

df = pd.read_csv(SRC, sep="\t")
df.columns = ["date", "balance", "equity", "load"]
df["date"] = pd.to_datetime(df["date"], format="%Y.%m.%d %H:%M")

# Every balance change is a closed deal or an entry commission.
chg = df["balance"].diff().fillna(0)
events = df.loc[chg.abs() > 0.001, ["date"]].assign(pnl=chg[chg.abs() > 0.001])
commission = events[events.pnl.abs() <= 0.3]
trades = events[events.pnl.abs() > 0.3]
wins, losses = trades[trades.pnl > 0], trades[trades.pnl < 0]

peak = df["equity"].cummax()
dd_pct = (df["equity"] - peak) / peak * 100
start, end = df["balance"].iloc[0], df["balance"].iloc[-1]

stats = {
    "Initial deposit": f"{start:,.2f}",
    "Final balance": f"{end:,.2f}",
    "Net profit": f"{end - start:,.2f} ({(end / start - 1) * 100:.1f}%)",
    "Closed deals": len(trades),
    "Win / Loss": f"{len(wins)} / {len(losses)} ({len(wins) / len(trades) * 100:.0f}% win)",
    "Gross profit / loss": f"{wins.pnl.sum():.2f} / {losses.pnl.sum():.2f}",
    "Profit factor": f"{wins.pnl.sum() / -losses.pnl.sum():.2f}",
    "Avg win / avg loss": f"{wins.pnl.mean():.2f} / {losses.pnl.mean():.2f}",
    "Largest win / loss": f"{wins.pnl.max():.2f} / {losses.pnl.min():.2f}",
    "Max equity drawdown": f"{dd_pct.min():.2f}%",
    "Commission per 0.01 lot": f"{-commission.pnl.mode().iloc[0]:.2f}",
}
for k, v in stats.items():
    print(f"{k:26s} {v}")

# 1) equity + balance
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.plot(df.date, df.equity, color=AQUA, lw=1.2, label="Equity", drawstyle="steps-post")
ax.plot(df.date, df.balance, color=BLUE, lw=2, label="Balance", drawstyle="steps-post")
ax.set_title("Balance & equity - XAUUSD backtest 2026 (start $1,000)")
ax.set_ylabel("USD")
ax.legend(frameon=False, loc="upper left")
ax.annotate(f"${end:,.2f}", (df.date.iloc[-1], end), xytext=(-60, 8),
            textcoords="offset points", color=INK, fontweight="bold")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
fig.tight_layout(); fig.savefig(f"{OUT}/01_equity_curve.png", dpi=130); plt.close(fig)

# 2) drawdown
fig, ax = plt.subplots(figsize=(11, 2.8))
ax.fill_between(df.date, dd_pct, 0, step="post", color=RED, alpha=0.25, lw=0)
ax.plot(df.date, dd_pct, color=RED, lw=1.2, drawstyle="steps-post")
ax.set_title(f"Equity drawdown from peak (max {dd_pct.min():.2f}%)")
ax.set_ylabel("%")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
fig.tight_layout(); fig.savefig(f"{OUT}/02_drawdown.png", dpi=130); plt.close(fig)

# 3) monthly P/L
m = trades.set_index("date").pnl.resample("MS").sum()
m = m.add(commission.set_index("date").pnl.resample("MS").sum(), fill_value=0)
m = m.reindex(pd.date_range("2026-01-01", df.date.max(), freq="MS"), fill_value=0)
fig, ax = plt.subplots(figsize=(11, 3.4))
bars = ax.bar(m.index.strftime("%b"), m.values, width=0.6,
              color=[BLUE if v >= 0 else RED for v in m.values])
for b, v in zip(bars, m.values):
    ax.annotate(f"{v:+.0f}", (b.get_x() + b.get_width() / 2, v), ha="center",
                va="bottom" if v >= 0 else "top", xytext=(0, 3 if v >= 0 else -3),
                textcoords="offset points", color=INK2, fontsize=9)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_title("Net P/L per month (USD)")
ax.grid(axis="x", visible=False)
fig.tight_layout(); fig.savefig(f"{OUT}/03_monthly_pnl.png", dpi=130); plt.close(fig)

# 4) distribution of deal results
fig, ax = plt.subplots(figsize=(11, 3.4))
s = trades.reset_index(drop=True)
ax.bar(s.index + 1, s.pnl, width=0.7, color=[BLUE if v > 0 else RED for v in s.pnl])
ax.axhline(0, color=INK2, lw=0.8)
ax.set_title("Each closed deal (USD) - small losses, occasional large breakout wins")
ax.set_xlabel("Deal #")
ax.grid(axis="x", visible=False)
fig.tight_layout(); fig.savefig(f"{OUT}/04_deal_results.png", dpi=130); plt.close(fig)

# 5) hour of day of exits (broker time)
h = trades.date.dt.hour.value_counts().reindex(range(24), fill_value=0)
fig, ax = plt.subplots(figsize=(11, 3))
ax.bar(h.index, h.values, width=0.7, color=BLUE)
ax.set_xticks(range(24))
ax.set_title("Hour of deal close (broker time) - activity clusters around the daily open")
ax.grid(axis="x", visible=False)
fig.tight_layout(); fig.savefig(f"{OUT}/05_close_hour.png", dpi=130); plt.close(fig)
