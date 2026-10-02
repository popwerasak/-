//+------------------------------------------------------------------+
//|                                              RSI_MA_Cross_EA.mq5 |
//|  Simple EA: RSI crosses its own Moving Average (MA on RSI)       |
//|  Buy  : RSI crosses above MA on RSI  -> close Sell, open Buy     |
//|  Sell : RSI crosses below MA on RSI  -> close Buy,  open Sell    |
//+------------------------------------------------------------------+
#property copyright "RSI MA Cross EA"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//--- input parameters
input ulong              MagicNumber            = 123456;      // Magic Number
input double             LotSize                = 0.01;        // Lot size
input int                Inp_RSI_ma_period      = 14;          // RSI: period
input ENUM_APPLIED_PRICE Inp_RSI_applied_price  = PRICE_CLOSE; // RSI: applied price
input int                Inp_MA_ma_period       = 14;          // MA on RSI: period
input ENUM_MA_METHOD     Inp_MA_ma_method       = MODE_EMA;    // MA on RSI: method
input ENUM_APPLIED_PRICE Inp_MA_applied_price   = PRICE_CLOSE; // MA on RSI: applied price (ignored when MA is built on RSI handle)

//--- globals
CTrade         m_trade;
CPositionInfo  m_position;

int      handle_iRSI       = INVALID_HANDLE;
int      handle_iMA_on_RSI = INVALID_HANDLE;
double   RSIBuffer[];
double   MAonRSIBuffer[];
int      m_bar_current     = 1;   // 1 = use last closed bar (no repaint)
datetime m_last_bar_time   = 0;

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
   m_trade.SetExpertMagicNumber(MagicNumber);
   m_trade.SetTypeFillingBySymbol(_Symbol);
   m_trade.SetDeviationInPoints(10);

   //--- RSI
   handle_iRSI = iRSI(_Symbol, _Period, Inp_RSI_ma_period, Inp_RSI_applied_price);
   if(handle_iRSI == INVALID_HANDLE)
     {
      PrintFormat("Failed to create iRSI handle, error %d", GetLastError());
      return(INIT_FAILED);
     }

   //--- MA calculated on RSI values (pass RSI handle as applied price)
   handle_iMA_on_RSI = iMA(_Symbol, _Period, Inp_MA_ma_period, 0, Inp_MA_ma_method, handle_iRSI);
   if(handle_iMA_on_RSI == INVALID_HANDLE)
     {
      PrintFormat("Failed to create iMA-on-RSI handle, error %d", GetLastError());
      return(INIT_FAILED);
     }

   ArraySetAsSeries(RSIBuffer, true);
   ArraySetAsSeries(MAonRSIBuffer, true);

   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(handle_iMA_on_RSI != INVALID_HANDLE) IndicatorRelease(handle_iMA_on_RSI);
   if(handle_iRSI != INVALID_HANDLE)       IndicatorRelease(handle_iRSI);
  }

//+------------------------------------------------------------------+
//| Expert tick                                                      |
//+------------------------------------------------------------------+
void OnTick()
  {
   //--- work only once per new bar
   datetime bar_time = iTime(_Symbol, _Period, 0);
   if(bar_time == m_last_bar_time)
      return;

   int need = m_bar_current + 2;
   if(CopyBuffer(handle_iRSI, 0, 0, need, RSIBuffer) < need)
      return;
   if(CopyBuffer(handle_iMA_on_RSI, 0, 0, need, MAonRSIBuffer) < need)
      return;

   m_last_bar_time = bar_time;

   //--- signals
   bool buy_signal  = (RSIBuffer[m_bar_current + 1] < MAonRSIBuffer[m_bar_current + 1] &&
                       RSIBuffer[m_bar_current]     > MAonRSIBuffer[m_bar_current]);

   bool sell_signal = (RSIBuffer[m_bar_current + 1] > MAonRSIBuffer[m_bar_current + 1] &&
                       RSIBuffer[m_bar_current]     < MAonRSIBuffer[m_bar_current]);

   if(buy_signal)
     {
      ClosePositions(POSITION_TYPE_SELL);           // Close Sell = Buy signal
      if(CountPositions(POSITION_TYPE_BUY) == 0)
         m_trade.Buy(LotSize, _Symbol, 0.0, 0.0, 0.0, "RSI x MA Buy");
     }
   else if(sell_signal)
     {
      ClosePositions(POSITION_TYPE_BUY);            // Close Buy = Sell signal
      if(CountPositions(POSITION_TYPE_SELL) == 0)
         m_trade.Sell(LotSize, _Symbol, 0.0, 0.0, 0.0, "RSI x MA Sell");
     }
  }

//+------------------------------------------------------------------+
//| Close all positions of given type (this symbol + magic)          |
//+------------------------------------------------------------------+
void ClosePositions(const ENUM_POSITION_TYPE type)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(!m_position.SelectByIndex(i))
         continue;
      if(m_position.Symbol() == _Symbol &&
         m_position.Magic() == MagicNumber &&
         m_position.PositionType() == type)
         m_trade.PositionClose(m_position.Ticket());
     }
  }

//+------------------------------------------------------------------+
//| Count positions of given type (this symbol + magic)              |
//+------------------------------------------------------------------+
int CountPositions(const ENUM_POSITION_TYPE type)
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(!m_position.SelectByIndex(i))
         continue;
      if(m_position.Symbol() == _Symbol &&
         m_position.Magic() == MagicNumber &&
         m_position.PositionType() == type)
         count++;
     }
   return(count);
  }
//+------------------------------------------------------------------+
