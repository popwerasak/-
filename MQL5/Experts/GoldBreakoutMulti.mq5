//+------------------------------------------------------------------+
//|                                            GoldBreakoutMulti.mq5 |
//|  Multi-strategy breakout EA for XAUUSD (H1).                      |
//|                                                                  |
//|  Rebuilt from the original's full Strategy Tester report          |
//|  (156 trades, 880 orders, 2025.01 - 2026.09), see README:         |
//|   - 3 sub-strategies place a BUY STOP just under the highest high |
//|     and a SELL STOP just above the lowest low of the last N D1    |
//|     bars. SL / TP are a % of the current price:                   |
//|       A : SL 0.48%  TP 1.98%  lookback 16 days                    |
//|       B : SL 0.34%  TP 1.62%  lookback 15 days                    |
//|       C : SL 3.00%  TP 0.72%  lookback 21 days (never trailed)    |
//|   - Orders refreshed daily and re-armed right after a close.      |
//|   - Fake-out exit: close a fresh breakout when an M1 bar closes   |
//|     back through the entry (original never took C's 3% SL).       |
//|   - Break-even lock per strategy (A +0.05%, B 0%, C +0.06%), then |
//|     H1 high/low trailing for A and B.                             |
//|   - Weighted lots: balance x MaxTotalDD% / sum of SLs, C half.    |
//|   - Spread, Friday and NFP filters.                               |
//+------------------------------------------------------------------+
#property copyright "GoldBreakoutMulti"
#property version   "1.40"

#include <Trade\Trade.mqh>

//--- enums
enum ENUM_LOT_MODE
  {
   LOT_FIXED    = 0, // Fixed lot
   LOT_RISK     = 1, // Risk % of balance per strategy
   LOT_TOTAL_DD = 2  // Max allowed total drawdown (all SLs hit)
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
input ENUM_TIMEFRAMES  InpSignalTF        = PERIOD_D1;      // Signal timeframe (levels)
input ENUM_TIMEFRAMES  InpRefreshTF       = PERIOD_D1;      // Place/move orders once per bar of this TF
input int              InpMinLevelAge     = 0;              // Level must be >= N signal bars old
input int              InpMaxTradesDay    = 10;             // Max fills per strategy & side per day
input int              InpMaxLossesDay    = 1;              // Stop strategy & side for the day after N SL losses
input int              InpMaxSpreadPts    = 500;            // Max allowed spread (points)

input group "=== Lot size ==="
input ENUM_LOT_MODE    InpLotMode         = LOT_TOTAL_DD;     // Lot calculation method
input double           InpFixedLot        = 0.01;           // Fixed lot / minimum lot
input double           InpRiskPercent     = 1.0;            // Risk % per strategy (LOT_RISK)
input double           InpMaxTotalDDPct   = 25.0;           // Max total DD %: lot sizing & stop new trades
input bool             InpCheckMargin     = true;           // Check free margin before placing
input double           InpA_LotWeight     = 1.0;            // Lot weight strategy A (LOT_TOTAL_DD)
input double           InpB_LotWeight     = 1.0;            // Lot weight strategy B (LOT_TOTAL_DD)
input double           InpC_LotWeight     = 0.5;            // Lot weight strategy C (LOT_TOTAL_DD)

input group "=== Filters ==="
input ENUM_FAKE_FILTER InpFakeFilter      = FAKE_MEDIUM;    // Fake-out exit (M1 close back through entry)
input int              InpFakeMaxMinutes  = 180;            // Fake-out exit only in first N minutes
input int              InpFridayStopHour  = 25;             // Friday stop hour (broker, 25=off)
input bool             InpFridayClosePend = true;           // Friday: delete pending orders
input bool             InpFridayCloseOpen = true;           // Friday: close open trades

input group "=== NFP filter ==="
input bool             InpNfpEnable       = true;           // Enable NFP filter
input bool             InpNfpUseCalendar  = true;           // Use MQL5 calendar (live only)
input int              InpNfpBrokerHour   = 15;             // Fallback NFP hour (broker time)
input int              InpNfpBrokerMinute = 30;             // Fallback NFP minute (broker time)
input int              InpNfpMinBefore    = 100;            // Minutes before NFP
input int              InpNfpMinAfter     = 60;             // Minutes after NFP
input bool             InpNfpCloseOpen    = true;           // Close open trades before NFP
input bool             InpNfpClosePending = true;           // Delete pending orders before NFP

input group "=== Break-even & trailing stop (High/Low) ==="
input double           InpBEPct           = 0.25;           // Move SL to break-even at profit (% price, 0=off)
input bool             InpUseHLTrail      = true;           // Use High/Low trailing SL
input ENUM_TIMEFRAMES  InpTrailTF         = PERIOD_H1;      // Trailing timeframe
input int              InpTrailBars       = 5;              // Trail on low/high of last N bars

input group "=== Strategy A (breakout, TP 4.1 x SL) ==="
input bool             InpA_Enable        = true;           // Enable
input ENUM_STRAT_DIR   InpA_Dir           = DIR_BOTH;       // Direction
input int              InpA_Lookback      = 16;             // Lookback bars (signal TF)
input double           InpA_EntryOffset   = -0.08;          // Entry offset from level (% price)
input double           InpA_SLPct         = 0.48;           // Stop loss (% price)
input double           InpA_TPPct         = 1.98;           // Take profit (% price)
input double           InpA_BELockPct     = 0.05;           // Break-even lock (% price)
input double           InpA_TrailStart    = 0.25;           // Start trailing at profit (% price, <0 = off)

input group "=== Strategy B (breakout, TP 4.7 x SL) ==="
input bool             InpB_Enable        = true;           // Enable
input ENUM_STRAT_DIR   InpB_Dir           = DIR_BOTH;       // Direction
input int              InpB_Lookback      = 15;             // Lookback bars (signal TF)
input double           InpB_EntryOffset   = -0.06;          // Entry offset from level (% price)
input double           InpB_SLPct         = 0.34;           // Stop loss (% price)
input double           InpB_TPPct         = 1.62;           // Take profit (% price)
input double           InpB_BELockPct     = 0.00;           // Break-even lock (% price)
input double           InpB_TrailStart    = 0.25;           // Start trailing at profit (% price, <0 = off)

input group "=== Strategy C (wide SL, small TP) ==="
input bool             InpC_Enable        = true;           // Enable
input ENUM_STRAT_DIR   InpC_Dir           = DIR_BOTH;       // Direction
input int              InpC_Lookback      = 21;             // Lookback bars (signal TF)
input double           InpC_EntryOffset   = -0.12;          // Entry offset from level (% price)
input double           InpC_SLPct         = 3.00;           // Stop loss (% price)
input double           InpC_TPPct         = 0.72;           // Take profit (% price)
input double           InpC_BELockPct     = 0.06;           // Break-even lock (% price)
input double           InpC_TrailStart    = -1.0;           // Start trailing at profit (% price, <0 = off)

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
   double            beLock;
   double            lotWeight;
   long              magic;
   string            name;
  };

#define STRAT_COUNT 3
StratCfg  g_strat[STRAT_COUNT];
CTrade    g_trade;
datetime  g_lastRefreshBar = 0;
string    g_peakVar;
ulong     g_nfpEventId    = 0;

//+------------------------------------------------------------------+
void SetStrat(int i, bool en, ENUM_STRAT_DIR dir, int lb, double off,
              double sl, double tp, double ts, double be, double w, string name)
  {
   g_strat[i].enable      = en;
   g_strat[i].dir         = dir;
   g_strat[i].lookback    = MathMax(lb, 2);
   g_strat[i].entryOffset = off;
   g_strat[i].slPct       = sl;
   g_strat[i].tpPct       = tp;
   g_strat[i].trailStart  = ts;
   g_strat[i].beLock      = be;
   g_strat[i].lotWeight   = w;
   g_strat[i].magic       = InpMagicBase + i + 1;
   g_strat[i].name        = name;
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   SetStrat(0, InpA_Enable, InpA_Dir, InpA_Lookback, InpA_EntryOffset,
            InpA_SLPct, InpA_TPPct, InpA_TrailStart, InpA_BELockPct, InpA_LotWeight, "A");
   SetStrat(1, InpB_Enable, InpB_Dir, InpB_Lookback, InpB_EntryOffset,
            InpB_SLPct, InpB_TPPct, InpB_TrailStart, InpB_BELockPct, InpB_LotWeight, "B");
   SetStrat(2, InpC_Enable, InpC_Dir, InpC_Lookback, InpC_EntryOffset,
            InpC_SLPct, InpC_TPPct, InpC_TrailStart, InpC_BELockPct, InpC_LotWeight, "C");

   g_trade.SetDeviationInPoints(50);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   g_peakVar = "GBM_peak_" + _Symbol + "_" + IntegerToString(InpMagicBase);
   if(!GlobalVariableCheck(g_peakVar))
      GlobalVariableSet(g_peakVar, AccountInfoDouble(ACCOUNT_BALANCE));

   if(InpNfpEnable && InpNfpUseCalendar && !MQLInfoInteger(MQL_TESTER))
      g_nfpEventId = FindNfpEventId();

   return(INIT_SUCCEEDED);
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

   ManageStops();

   //--- a position just closed: re-arm its strategy now instead of waiting a day
   static int lastOpen = 0;
   int openNow = CountOurPositions();
   if(openNow < lastOpen)
      g_lastRefreshBar = 0;
   lastOpen = openNow;

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
      bool buyOk  = InpAllowBuy  && g_strat[i].dir != DIR_SELL;
      bool sellOk = InpAllowSell && g_strat[i].dir != DIR_BUY;
      RefreshOrder(i, true,  buyOk);
      RefreshOrder(i, false, sellOk);
     }
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
      DayLimitReached(magic, isBuy))
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
   // The original sizes SL/TP from the current price, so the buy and the
   // sell stop of one strategy get the same distance in dollars.
   double mid   = (ask + bid) / 2.0;
   double slD   = mid * g_strat[i].slPct / 100.0;
   double tpD   = mid * g_strat[i].tpPct / 100.0;
   double sl    = NormalizeDouble(isBuy ? price - slD : price + slD, digits);
   double tp    = NormalizeDouble(isBuy ? price + tpD : price - tpD, digits);

   //--- don't chase: the stop must still be beyond the market
   bool   valid   = isBuy ? (price - ask > stops) : (bid - price > stops);
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

   double lots = CalcLots(i, price, sl);
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
      case FAKE_LOW:    return(0.06);
      case FAKE_MEDIUM: return(0.03);
      case FAKE_HIGH:   return(0.015);
     }
   return(0.0);
  }

//+------------------------------------------------------------------+
double CalcLots(int strat, double price, double sl)
  {
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double lots    = InpFixedLot;

   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tickValue <= 0.0) tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);

   if(InpLotMode == LOT_RISK && tickSize > 0.0)
     {
      double lossPerLot = MathAbs(price - sl) / tickSize * tickValue;
      if(lossPerLot > 0.0)
         lots = balance * InpRiskPercent / 100.0 / lossPerLot;
      lots = MathMax(lots, InpFixedLot);
     }
   else if(InpLotMode == LOT_TOTAL_DD && tickSize > 0.0 && InpMaxTotalDDPct > 0.0)
     {
      // Same lot for every strategy, sized so that all enabled strategies
      // hitting their full SL together lose MaxTotalDD% of the balance.
      double sumLoss = 0.0;
      for(int i = 0; i < STRAT_COUNT; i++)
         if(g_strat[i].enable)
            sumLoss += price * g_strat[i].slPct / 100.0 / tickSize * tickValue;
      if(sumLoss > 0.0)
         lots = balance * InpMaxTotalDDPct / 100.0 / sumLoss * g_strat[strat].lotWeight;
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

   static datetime lastM1 = 0;
   datetime m1   = iTime(_Symbol, PERIOD_M1, 0);
   bool   newM1  = (m1 != lastM1);
   lastM1 = m1;

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
      if(InpBEPct > 0.0 && gain >= open * InpBEPct / 100.0)
        {
         double lock = open * g_strat[i].beLock / 100.0;
         double be   = NormalizeDouble(isBuy ? open + lock : open - lock, digits);
         bool   need = isBuy ? (curSL < be - point && be < bid - stops)
                             : ((curSL == 0.0 || curSL > be + point) && be > ask + stops);
         if(need && g_trade.PositionModify(ticket, be, curTP))
            curSL = be;
        }

      //--- fake-out exit: fresh breakout whose M1 bar closed back through the entry
      if(newM1 && FakeFilterPct() > 0.0 &&
         TimeCurrent() - (datetime)PositionGetInteger(POSITION_TIME) <= InpFakeMaxMinutes * 60)
        {
         bool   atRisk = isBuy ? (curSL < open) : (curSL == 0.0 || curSL > open);
         double c1     = iClose(_Symbol, PERIOD_M1, 1);
         double back   = open * FakeFilterPct() / 100.0;
         if(atRisk && c1 > 0.0 && (isBuy ? c1 < open - back : c1 > open + back))
           {
            g_trade.PositionClose(ticket);
            continue;
           }
        }

      if(!InpUseHLTrail || g_strat[i].trailStart < 0.0 ||
         (g_strat[i].trailStart > 0.0 && gain < open * g_strat[i].trailStart / 100.0)) continue;

      double newSL;
      if(isBuy)
        {
         int idx = iLowest(_Symbol, InpTrailTF, MODE_LOW, InpTrailBars, 1);
         if(idx < 0) continue;
         newSL = NormalizeDouble(iLow(_Symbol, InpTrailTF, idx), digits);
         if(newSL <= curSL + point || newSL >= bid - stops) continue;
        }
      else
        {
         int idx = iHighest(_Symbol, InpTrailTF, MODE_HIGH, InpTrailBars, 1);
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

//+------------------------------------------------------------------+
//| Today's fills and losing exits for one strategy & side            |
//+------------------------------------------------------------------+
bool DayLimitReached(long magic, bool isBuy)
  {
   if(InpMaxTradesDay <= 0 && InpMaxLossesDay <= 0)
      return(false);
   MqlDateTime d;
   TimeToStruct(TimeCurrent(), d);
   d.hour = 0; d.min = 0; d.sec = 0;
   if(!HistorySelect(StructToTime(d), TimeCurrent() + 60))
      return(false);
   int fills = 0, losses = 0;
   for(int k = HistoryDealsTotal() - 1; k >= 0; k--)
     {
      ulong t = HistoryDealGetTicket(k);
      if(t == 0) continue;
      if(HistoryDealGetString(t, DEAL_SYMBOL) != _Symbol ||
         HistoryDealGetInteger(t, DEAL_MAGIC) != magic)
         continue;
      bool buyDeal = HistoryDealGetInteger(t, DEAL_TYPE) == DEAL_TYPE_BUY;
      long entry   = HistoryDealGetInteger(t, DEAL_ENTRY);
      // A buy position is opened by a buy deal and closed by a sell deal.
      if(entry == DEAL_ENTRY_IN && buyDeal == isBuy)
         fills++;
      else if(entry == DEAL_ENTRY_OUT && buyDeal != isBuy &&
              HistoryDealGetInteger(t, DEAL_REASON) == DEAL_REASON_SL &&
              HistoryDealGetDouble(t, DEAL_PROFIT) < 0.0)
         losses++;
     }
   return((InpMaxTradesDay > 0 && fills >= InpMaxTradesDay) ||
          (InpMaxLossesDay > 0 && losses >= InpMaxLossesDay));
  }

int CountOurPositions()
  {
   int n = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong t = PositionGetTicket(k);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && IsOurMagic(PositionGetInteger(POSITION_MAGIC)))
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
