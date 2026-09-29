//+------------------------------------------------------------------+
//|                                            GoldBreakoutMulti.mq5 |
//|  Multi-strategy breakout EA for XAUUSD (M15 levels, H1 refresh).  |
//|                                                                  |
//|  Base: the user's best version (backtest 2025.01-2026.09:         |
//|  +1,596.62 USD, 81% win, PF 1.65). Defaults below are the inputs  |
//|  of that run.                                                     |
//|   - 2 active sub-strategies (C off), each places BUY STOP at the  |
//|     highest high and SELL STOP at the lowest low of its lookback. |
//|   - SL / TP are a percentage of price (not fixed points).         |
//|       A : SL 0.50%  TP 2.05%  (TP = 4.1  x SL)                    |
//|       B : SL 0.35%  TP 1.65%  (TP = 4.7  x SL)                    |
//|       C : SL 3.00%  TP 0.72%  (TP = 0.24 x SL, buy only, off)     |
//|   - Orders refreshed once per H1 bar, only on levels that are at  |
//|     least N bars old, max 1 fill per strategy and side per day.   |
//|   - Break-even, then trailing SL on high/low of lower-TF bars.    |
//|   - Spread, fake-breakout, Friday and NFP filters.                |
//|  v2.00: parabolic filter - no breakout orders in the direction of |
//|  an over-stretched, high-volatility move (Oct-Nov 2025 losses).   |
//|  v2.10: break-even, lock, trail start and trail length scale with |
//|  H1 ATR, so doubled 2026 volatility no longer knocks 78% of wins  |
//|  out at the +0.02% break-even lock.                               |
//+------------------------------------------------------------------+
#property copyright "GoldBreakoutMulti"
#property version   "2.10"

#include <Trade\Trade.mqh>

//--- enums
enum ENUM_LOT_MODE
  {
   LOT_FIXED   = 0, // Fixed lot
   LOT_RISK    = 1  // Risk % of balance per strategy
  };

enum ENUM_FAKE_FILTER
  {
   FAKE_OFF    = 0, // Off
   FAKE_LOW    = 1, // Low
   FAKE_MEDIUM = 2, // Medium
   FAKE_HIGH   = 3  // High
  };

enum ENUM_STRAT_DIR
  {
   DIR_BOTH = 0, // Buy & Sell
   DIR_BUY  = 1, // Buy only
   DIR_SELL = 2  // Sell only
  };

//--- inputs
input group "=== General ==="
input long             InpMagicBase       = 8000;           // Base magic number
input string           InpComment         = "GoldBreakout"; // Order comment
input bool             InpAllowBuy        = true;           // Allow buy trades
input bool             InpAllowSell       = true;           // Allow sell trades
input ENUM_TIMEFRAMES  InpSignalTF        = PERIOD_M15;     // Signal timeframe (levels)
input ENUM_TIMEFRAMES  InpRefreshTF       = PERIOD_H1;      // Place/move orders once per bar of this TF
input int              InpMinLevelAge     = 24;             // Level must be >= N signal bars old
input int              InpMaxTradesDay    = 1;              // Max fills per strategy & side per day
input int              InpMaxSpreadPts    = 500;            // Max allowed spread (points)

input group "=== Lot size ==="
input ENUM_LOT_MODE    InpLotMode         = LOT_RISK;       // Lot calculation method
input double           InpFixedLot        = 0.01;           // Fixed lot / minimum lot
input double           InpRiskPercent     = 2.5;            // Risk % per strategy (LOT_RISK)
input double           InpMaxTotalDDPct   = 20.0;           // Stop new trades at total DD % (0=off)
input bool             InpCheckMargin     = true;           // Check free margin before placing

input group "=== Filters ==="
input ENUM_FAKE_FILTER InpFakeFilter      = FAKE_LOW;       // Fake breakout filter
input int              InpFridayStopHour  = 25;             // Friday stop hour (broker, 25=off)
input bool             InpFridayClosePend = true;           // Friday: delete pending orders
input bool             InpFridayCloseOpen = true;           // Friday: close open trades

input group "=== Parabolic filter (v2.00) ==="
input bool             InpParaEnable      = true;           // Block breakouts into a stretched, volatile move
input double           InpParaAtrPct      = 0.48;           // H1 ATR(14) above this % of price ...
input double           InpParaStretchPct  = 3.0;            // ... and D1 close this % beyond EMA(20) in trade direction
input int              InpParaAtrPeriod   = 14;             // ATR period (H1)
input int              InpParaEmaPeriod   = 20;             // EMA period (D1)

input group "=== NFP filter ==="
input bool             InpNfpEnable       = true;           // Enable NFP filter
input bool             InpNfpUseCalendar  = true;           // Use MQL5 calendar (live only)
input int              InpNfpBrokerHour   = 15;             // Fallback NFP hour (broker time)
input int              InpNfpBrokerMinute = 30;             // Fallback NFP minute (broker time)
input int              InpNfpMinBefore    = 100;            // Minutes before NFP
input int              InpNfpMinAfter     = 60;             // Minutes after NFP
input bool             InpNfpCloseOpen    = true;           // Close open trades before NFP
input bool             InpNfpClosePending = true;           // Delete pending orders before NFP

input group "=== Volatility-scaled stops (v2.10) ==="
input bool             InpVolScaleEnable  = true;           // Scale BE / trailing with H1 ATR
input double           InpVolRefAtrPct    = 0.25;           // H1 ATR % the BE / trail settings were tuned for
input double           InpVolMaxScale     = 2.5;            // Max scale factor (min is 1 = unchanged)

input group "=== Break-even & trailing stop (High/Low) ==="
input double           InpBEPct           = 0.15;           // Move SL to break-even at profit (% price, 0=off)
input double           InpBELockPct       = 0.02;           // Profit locked at break-even (% price)
input bool             InpUseHLTrail      = true;           // Use High/Low trailing SL
input ENUM_TIMEFRAMES  InpTrailTF         = PERIOD_M5;      // Trailing timeframe
input int              InpTrailBars       = 3;              // Trail on low/high of last N bars

input group "=== Strategy A (breakout, TP 4.1 x SL) ==="
input bool             InpA_Enable        = true;           // Enable
input ENUM_STRAT_DIR   InpA_Dir           = DIR_BOTH;       // Direction
input int              InpA_Lookback      = 600;            // Lookback bars (signal TF)
input double           InpA_EntryOffset   = -0.065;         // Entry offset from level (% price)
input double           InpA_SLPct         = 0.50;           // Stop loss (% price)
input double           InpA_TPPct         = 2.05;           // Take profit (% price)
input double           InpA_TrailStart    = 0.20;           // Start trailing at profit (% price)

input group "=== Strategy B (breakout, TP 4.7 x SL) ==="
input bool             InpB_Enable        = true;           // Enable
input ENUM_STRAT_DIR   InpB_Dir           = DIR_BOTH;       // Direction
input int              InpB_Lookback      = 340;            // Lookback bars (signal TF)
input double           InpB_EntryOffset   = -0.050;         // Entry offset from level (% price)
input double           InpB_SLPct         = 0.35;           // Stop loss (% price)
input double           InpB_TPPct         = 1.65;           // Take profit (% price)
input double           InpB_TrailStart    = 0.20;           // Start trailing at profit (% price)

input group "=== Strategy C (wide SL, small TP) ==="
input bool             InpC_Enable        = false;          // Enable
input ENUM_STRAT_DIR   InpC_Dir           = DIR_BUY;        // Direction
input int              InpC_Lookback      = 900;            // Lookback bars (signal TF)
input double           InpC_EntryOffset   = -0.110;         // Entry offset from level (% price)
input double           InpC_SLPct         = 3.00;           // Stop loss (% price)
input double           InpC_TPPct         = 0.72;           // Take profit (% price)
input double           InpC_TrailStart    = 0.15;           // Start trailing at profit (% price)

//--- strategy table
struct StratCfg
  {
   bool              enable;
   ENUM_STRAT_DIR    dir;
   int               lookback;
   double            entryOffset;
   double            slPct;
   double            tpPct;
   double            trailStart;
   long              magic;
   string            name;
  };

#define STRAT_COUNT 3
StratCfg  g_strat[STRAT_COUNT];
CTrade    g_trade;
datetime  g_lastRefreshBar = 0;
string    g_peakVar;
ulong     g_nfpEventId    = 0;
int       g_atrHandle     = INVALID_HANDLE;
int       g_emaHandle     = INVALID_HANDLE;

//+------------------------------------------------------------------+
void SetStrat(int i, bool en, ENUM_STRAT_DIR dir, int lb, double off,
              double sl, double tp, double ts, string name)
  {
   g_strat[i].enable      = en;
   g_strat[i].dir         = dir;
   g_strat[i].lookback    = MathMax(lb, 2);
   g_strat[i].entryOffset = off;
   g_strat[i].slPct       = sl;
   g_strat[i].tpPct       = tp;
   g_strat[i].trailStart  = ts;
   g_strat[i].magic       = InpMagicBase + i + 1;
   g_strat[i].name        = name;
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   SetStrat(0, InpA_Enable, InpA_Dir, InpA_Lookback, InpA_EntryOffset,
            InpA_SLPct, InpA_TPPct, InpA_TrailStart, "A");
   SetStrat(1, InpB_Enable, InpB_Dir, InpB_Lookback, InpB_EntryOffset,
            InpB_SLPct, InpB_TPPct, InpB_TrailStart, "B");
   SetStrat(2, InpC_Enable, InpC_Dir, InpC_Lookback, InpC_EntryOffset,
            InpC_SLPct, InpC_TPPct, InpC_TrailStart, "C");

   g_trade.SetDeviationInPoints(50);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   g_peakVar = "GBM_peak_" + _Symbol + "_" + IntegerToString(InpMagicBase);
   if(!GlobalVariableCheck(g_peakVar))
      GlobalVariableSet(g_peakVar, AccountInfoDouble(ACCOUNT_BALANCE));

   if(InpNfpEnable && InpNfpUseCalendar && !MQLInfoInteger(MQL_TESTER))
      g_nfpEventId = FindNfpEventId();

   if(InpParaEnable || InpVolScaleEnable)
     {
      g_atrHandle = iATR(_Symbol, PERIOD_H1, InpParaAtrPeriod);
      if(g_atrHandle == INVALID_HANDLE)
         return(INIT_FAILED);
     }
   if(InpParaEnable)
     {
      g_emaHandle = iMA(_Symbol, PERIOD_D1, InpParaEmaPeriod, 0, MODE_EMA, PRICE_CLOSE);
      if(g_emaHandle == INVALID_HANDLE)
         return(INIT_FAILED);
     }

   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(g_atrHandle != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
   if(g_emaHandle != INVALID_HANDLE) IndicatorRelease(g_emaHandle);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   UpdatePeak();

   bool blockNew = false;

   //--- Friday close
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   if(now.day_of_week == 5 && now.hour >= InpFridayStopHour)
     {
      if(InpFridayClosePend) DeleteAllPending();
      if(InpFridayCloseOpen) CloseAllPositions();
      blockNew = true;
     }

   //--- NFP window
   if(InpNfpEnable && InNfpWindow(TimeCurrent()))
     {
      if(InpNfpClosePending) DeleteAllPending();
      if(InpNfpCloseOpen)    CloseAllPositions();
      blockNew = true;
     }

   //--- total drawdown guard
   if(InpMaxTotalDDPct > 0.0)
     {
      double peak = GlobalVariableGet(g_peakVar);
      if(peak > 0.0 && AccountInfoDouble(ACCOUNT_EQUITY) < peak * (1.0 - InpMaxTotalDDPct / 100.0))
        {
         DeleteAllPending();
         blockNew = true;
        }
     }

   //--- spread: pull pending orders while spread is too wide
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpreadPts)
     {
      DeleteAllPending();
      blockNew = true;
     }

   //--- parabolic filter: pull pending orders on a blocked side at once
   bool paraBuy  = ParabolicBlock(true);
   bool paraSell = ParabolicBlock(false);
   for(int i = 0; i < STRAT_COUNT; i++)
     {
      if(paraBuy)  DeletePending(g_strat[i].magic, ORDER_TYPE_BUY_STOP);
      if(paraSell) DeletePending(g_strat[i].magic, ORDER_TYPE_SELL_STOP);
     }

   ManageStops();

   //--- refresh orders once per refresh bar, or immediately after a block lifts
   datetime bar = iTime(_Symbol, InpRefreshTF, 0);
   if(blockNew)
     {
      g_lastRefreshBar = 0;
      return;
     }
   if(bar == g_lastRefreshBar)
      return;
   g_lastRefreshBar = bar;

   for(int i = 0; i < STRAT_COUNT; i++)
     {
      if(!g_strat[i].enable)
        {
         DeletePending(g_strat[i].magic, ORDER_TYPE_BUY_STOP);
         DeletePending(g_strat[i].magic, ORDER_TYPE_SELL_STOP);
         continue;
        }
      bool buyOk  = InpAllowBuy  && g_strat[i].dir != DIR_SELL && !paraBuy;
      bool sellOk = InpAllowSell && g_strat[i].dir != DIR_BUY  && !paraSell;
      RefreshOrder(i, true,  buyOk);
      RefreshOrder(i, false, sellOk);
     }
  }

//+------------------------------------------------------------------+
//| True when a breakout in this direction would chase a parabolic   |
//| move: H1 ATR is high AND the last D1 close is stretched beyond    |
//| its EMA in the same direction. Uses closed bars only.             |
//+------------------------------------------------------------------+
bool ParabolicBlock(bool isBuy)
  {
   if(!InpParaEnable || g_atrHandle == INVALID_HANDLE || g_emaHandle == INVALID_HANDLE)
      return(false);

   double ema[1];
   if(CopyBuffer(g_emaHandle, 0, 1, 1, ema) != 1)
      return(false);
   double d1Close = iClose(_Symbol, PERIOD_D1, 1);
   double atrPct  = AtrPct();
   if(atrPct <= 0.0 || d1Close <= 0.0 || ema[0] <= 0.0)
      return(false);

   double stretch = (d1Close / ema[0] - 1.0) * 100.0;
   if(!isBuy) stretch = -stretch;
   return(atrPct > InpParaAtrPct && stretch > InpParaStretchPct);
  }

//+------------------------------------------------------------------+
//| H1 ATR of the last closed bar as % of price (0 when unavailable) |
//+------------------------------------------------------------------+
double AtrPct()
  {
   if(g_atrHandle == INVALID_HANDLE) return(0.0);
   double atr[1];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, atr) != 1) return(0.0);
   double c = iClose(_Symbol, PERIOD_H1, 1);
   return(c > 0.0 ? atr[0] / c * 100.0 : 0.0);
  }

//+------------------------------------------------------------------+
//| Factor for BE / trailing distances: 1 in calm markets, grows with |
//| volatility up to InpVolMaxScale.                                  |
//+------------------------------------------------------------------+
double VolScale()
  {
   if(!InpVolScaleEnable || InpVolRefAtrPct <= 0.0) return(1.0);
   double a = AtrPct();
   if(a <= 0.0) return(1.0);
   return(MathMax(1.0, MathMin(InpVolMaxScale, a / InpVolRefAtrPct)));
  }

//+------------------------------------------------------------------+
//| Place, move or delete one strategy's pending stop order          |
//+------------------------------------------------------------------+
void RefreshOrder(int i, bool isBuy, bool allowed)
  {
   long             magic = g_strat[i].magic;
   ENUM_ORDER_TYPE  type  = isBuy ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP;
   ulong            ticket = FindPending(magic, type);

   //--- one trade per strategy and side at a time, limited fills per day
   if(!allowed || HasPosition(magic, isBuy ? POSITION_TYPE_BUY : POSITION_TYPE_SELL) ||
      (InpMaxTradesDay > 0 && FillsToday(magic, isBuy) >= InpMaxTradesDay))
     {
      if(ticket > 0) g_trade.OrderDelete(ticket);
      return;
     }

   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double stops  = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;

   //--- channel level of the closed bars
   int    lb = g_strat[i].lookback;
   double level;
   if(isBuy)
     {
      int idx = iHighest(_Symbol, InpSignalTF, MODE_HIGH, lb, 1);
      if(idx < 0) return;
      if(idx < InpMinLevelAge)
        {
         if(ticket > 0) g_trade.OrderDelete(ticket);
         return;
        }
      level = iHigh(_Symbol, InpSignalTF, idx);
     }
   else
     {
      int idx = iLowest(_Symbol, InpSignalTF, MODE_LOW, lb, 1);
      if(idx < 0) return;
      if(idx < InpMinLevelAge)
        {
         if(ticket > 0) g_trade.OrderDelete(ticket);
         return;
        }
      level = iLow(_Symbol, InpSignalTF, idx);
     }
   if(level <= 0.0) return;

   // Positive offset = further out, negative = just inside the level.
   double off   = level * g_strat[i].entryOffset / 100.0;
   double price = NormalizeDouble(isBuy ? level + off : level - off, digits);
   double slD   = price * g_strat[i].slPct / 100.0;
   double tpD   = price * g_strat[i].tpPct / 100.0;
   double sl    = NormalizeDouble(isBuy ? price - slD : price + slD, digits);
   double tp    = NormalizeDouble(isBuy ? price + tpD : price - tpD, digits);

   //--- don't chase: the stop must still be beyond market + fake-breakout distance
   double minDist = MathMax(stops, price * FakeFilterPct() / 100.0);
   bool   valid   = isBuy ? (price - ask > minDist) : (bid - price > minDist);
   if(!valid)
     {
      if(ticket > 0) g_trade.OrderDelete(ticket);
      return;
     }

   //--- modify existing order only when the level moved
   if(ticket > 0)
     {
      if(!OrderSelect(ticket)) return;
      double cur = OrderGetDouble(ORDER_PRICE_OPEN);
      if(MathAbs(cur - price) >= point)
         g_trade.OrderModify(ticket, price, sl, tp, ORDER_TIME_GTC, 0);
      return;
     }

   double lots = CalcLots(price, sl);
   if(lots <= 0.0) return;

   if(InpCheckMargin)
     {
      double margin = 0.0;
      ENUM_ORDER_TYPE mType = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      if(!OrderCalcMargin(mType, _Symbol, lots, price, margin) ||
         margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE))
         return;
     }

   g_trade.SetExpertMagicNumber(magic);
   string cmt = InpComment + " " + g_strat[i].name;
   if(isBuy)
      g_trade.BuyStop(lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, cmt);
   else
      g_trade.SellStop(lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, cmt);
  }

//+------------------------------------------------------------------+
double FakeFilterPct()
  {
   switch(InpFakeFilter)
     {
      case FAKE_LOW:    return(0.05);
      case FAKE_MEDIUM: return(0.15);
      case FAKE_HIGH:   return(0.30);
     }
   return(0.0);
  }

//+------------------------------------------------------------------+
double CalcLots(double price, double sl)
  {
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double lots    = InpFixedLot;

   if(InpLotMode == LOT_RISK)
     {
      double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
      if(tickValue <= 0.0) tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double lossPerLot = MathAbs(price - sl) / tickSize * tickValue;
      if(lossPerLot > 0.0)
         lots = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0 / lossPerLot;
      lots = MathMax(lots, InpFixedLot);
     }

   lots = MathFloor(lots / step) * step;
   lots = MathMax(minLot, MathMin(maxLot, lots));
   return(NormalizeDouble(lots, 2));
  }

//+------------------------------------------------------------------+
//| Break-even, then trail SL to the low (buy) / high (sell) of the  |
//| last N bars                                                      |
//+------------------------------------------------------------------+
void ManageStops()
  {
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double stops  = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double scale  = VolScale();
   int    tBars  = (int)MathMax(1, MathRound(InpTrailBars * scale));

   for(int p = PositionsTotal() - 1; p >= 0; p--)
     {
      ulong ticket = PositionGetTicket(p);
      if(ticket == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      int i = StratIndex(PositionGetInteger(POSITION_MAGIC));
      if(i < 0) continue;

      bool   isBuy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      double open  = PositionGetDouble(POSITION_PRICE_OPEN);
      double curSL = PositionGetDouble(POSITION_SL);
      double curTP = PositionGetDouble(POSITION_TP);
      double gain  = isBuy ? bid - open : open - ask;

      //--- break-even
      if(InpBEPct > 0.0 && gain >= open * InpBEPct * scale / 100.0)
        {
         double lock = open * InpBELockPct * scale / 100.0;
         double be   = NormalizeDouble(isBuy ? open + lock : open - lock, digits);
         bool   need = isBuy ? (curSL < be - point && be < bid - stops)
                             : ((curSL == 0.0 || curSL > be + point) && be > ask + stops);
         if(need && g_trade.PositionModify(ticket, be, curTP))
            curSL = be;
        }

      if(!InpUseHLTrail || gain < open * g_strat[i].trailStart * scale / 100.0) continue;

      double newSL;
      if(isBuy)
        {
         int idx = iLowest(_Symbol, InpTrailTF, MODE_LOW, tBars, 1);
         if(idx < 0) continue;
         newSL = NormalizeDouble(iLow(_Symbol, InpTrailTF, idx), digits);
         if(newSL <= curSL + point || newSL >= bid - stops) continue;
        }
      else
        {
         int idx = iHighest(_Symbol, InpTrailTF, MODE_HIGH, tBars, 1);
         if(idx < 0) continue;
         newSL = NormalizeDouble(iHigh(_Symbol, InpTrailTF, idx), digits);
         if((curSL > 0.0 && newSL >= curSL - point) || newSL <= ask + stops) continue;
        }
      g_trade.PositionModify(ticket, newSL, curTP);
     }
  }

//+------------------------------------------------------------------+
//| NFP: calendar when live, else first Friday at broker HH:MM       |
//+------------------------------------------------------------------+
ulong FindNfpEventId()
  {
   MqlCalendarEvent events[];
   int n = CalendarEventByCountry("US", events);
   for(int k = 0; k < n; k++)
      if(events[k].event_code == "nonfarm-payrolls")
         return(events[k].id);
   return(0);
  }

bool InNfpWindow(datetime t)
  {
   datetime from = t - InpNfpMinAfter * 60;
   datetime to   = t + InpNfpMinBefore * 60;

   if(g_nfpEventId > 0)
     {
      MqlCalendarValue values[];
      if(CalendarValueHistoryByEvent(g_nfpEventId, values, from, to) > 0)
         return(true);
      return(false);
     }

   //--- fallback: first Friday of the month (also used in the tester)
   MqlDateTime d;
   TimeToStruct(t, d);
   d.day = 1; d.hour = InpNfpBrokerHour; d.min = InpNfpBrokerMinute; d.sec = 0;
   datetime first = StructToTime(d);
   MqlDateTime f;
   TimeToStruct(first, f);
   int add = (5 - f.day_of_week + 7) % 7;
   datetime nfp = first + add * 86400;
   return(nfp >= from && nfp <= to);
  }

//+------------------------------------------------------------------+
void UpdatePeak()
  {
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   if(bal > GlobalVariableGet(g_peakVar))
      GlobalVariableSet(g_peakVar, bal);
  }

int StratIndex(long magic)
  {
   for(int i = 0; i < STRAT_COUNT; i++)
      if(g_strat[i].magic == magic) return(i);
   return(-1);
  }

bool IsOurMagic(long magic) { return(StratIndex(magic) >= 0); }

ulong FindPending(long magic, ENUM_ORDER_TYPE type)
  {
   for(int k = OrdersTotal() - 1; k >= 0; k--)
     {
      ulong t = OrderGetTicket(k);
      if(t == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) == _Symbol &&
         OrderGetInteger(ORDER_MAGIC) == magic &&
         (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE) == type)
         return(t);
     }
   return(0);
  }

int FillsToday(long magic, bool isBuy)
  {
   MqlDateTime d;
   TimeToStruct(TimeCurrent(), d);
   d.hour = 0; d.min = 0; d.sec = 0;
   if(!HistorySelect(StructToTime(d), TimeCurrent() + 60))
      return(0);
   int n = 0;
   for(int k = HistoryDealsTotal() - 1; k >= 0; k--)
     {
      ulong t = HistoryDealGetTicket(k);
      if(t == 0) continue;
      if(HistoryDealGetString(t, DEAL_SYMBOL) == _Symbol &&
         HistoryDealGetInteger(t, DEAL_MAGIC) == magic &&
         HistoryDealGetInteger(t, DEAL_ENTRY) == DEAL_ENTRY_IN &&
         (HistoryDealGetInteger(t, DEAL_TYPE) == DEAL_TYPE_BUY) == isBuy)
         n++;
     }
   return(n);
  }

bool HasPosition(long magic, ENUM_POSITION_TYPE type)
  {
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong t = PositionGetTicket(k);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == magic &&
         (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == type)
         return(true);
     }
   return(false);
  }

void DeletePending(long magic, ENUM_ORDER_TYPE type)
  {
   ulong t = FindPending(magic, type);
   if(t > 0) g_trade.OrderDelete(t);
  }

void DeleteAllPending()
  {
   for(int k = OrdersTotal() - 1; k >= 0; k--)
     {
      ulong t = OrderGetTicket(k);
      if(t == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) == _Symbol && IsOurMagic(OrderGetInteger(ORDER_MAGIC)))
         g_trade.OrderDelete(t);
     }
  }

void CloseAllPositions()
  {
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong t = PositionGetTicket(k);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && IsOurMagic(PositionGetInteger(POSITION_MAGIC)))
         g_trade.PositionClose(t);
     }
  }
//+------------------------------------------------------------------+
