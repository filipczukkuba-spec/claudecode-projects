// TrendMomentumEA.mq4
// Strategy: EMA trend + RSI momentum confluence
// Timeframe: H1 recommended (works on H4, M30 too)

#property strict

// ---- Inputs ----
extern int    EMA_Fast       = 20;
extern int    EMA_Slow       = 50;
extern int    RSI_Period     = 14;
extern double RSI_Level      = 50.0;
extern int    ATR_Period     = 14;
extern double ATR_SL_Mult    = 1.5;   // stop loss = 1.5 * ATR
extern double ATR_TP_Mult    = 3.0;   // take profit = 3.0 * ATR (2:1 RR)
extern double RiskPercent    = 1.0;   // risk % of balance per trade
extern int    MagicNumber    = 112233;
extern string Comment_       = "TrendMomentumEA";

// ---- State ----
double prevRSI, currRSI;

// ----------------------------------------------------------------
int OnInit() {
   return INIT_SUCCEEDED;
}

// ----------------------------------------------------------------
void OnTick() {
   // Only act on a new bar
   static datetime lastBar = 0;
   if (Time[0] == lastBar) return;
   lastBar = Time[0];

   if (IsTradeAllowed() == false) return;
   if (AccountFreeMargin() < 50)  return;

   double emaFast = iMA(NULL, 0, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE, 1);
   double emaSlow = iMA(NULL, 0, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE, 1);
   double atr     = iATR(NULL, 0, ATR_Period, 1);

   currRSI = iRSI(NULL, 0, RSI_Period, PRICE_CLOSE, 1);
   prevRSI = iRSI(NULL, 0, RSI_Period, PRICE_CLOSE, 2);

   bool uptrend   = emaFast > emaSlow;
   bool downtrend = emaFast < emaSlow;

   // RSI crosses above 50 in uptrend
   bool buySignal  = uptrend   && prevRSI < RSI_Level && currRSI >= RSI_Level;
   // RSI crosses below 50 in downtrend
   bool sellSignal = downtrend && prevRSI > RSI_Level && currRSI <= RSI_Level;

   int openBuys  = CountOrders(OP_BUY);
   int openSells = CountOrders(OP_SELL);

   // Close opposite trades on signal flip
   if (buySignal  && openSells > 0) CloseOrders(OP_SELL);
   if (sellSignal && openBuys  > 0) CloseOrders(OP_BUY);

   double sl, tp, lots;

   if (buySignal && openBuys == 0) {
      sl   = Ask - atr * ATR_SL_Mult;
      tp   = Ask + atr * ATR_TP_Mult;
      lots = CalcLots(atr * ATR_SL_Mult);
      if (lots > 0)
         OrderSend(Symbol(), OP_BUY, lots, Ask, 3, sl, tp, Comment_, MagicNumber, 0, clrGreen);
   }

   if (sellSignal && openSells == 0) {
      sl   = Bid + atr * ATR_SL_Mult;
      tp   = Bid - atr * ATR_TP_Mult;
      lots = CalcLots(atr * ATR_SL_Mult);
      if (lots > 0)
         OrderSend(Symbol(), OP_SELL, lots, Bid, 3, sl, tp, Comment_, MagicNumber, 0, clrRed);
   }
}

// ----------------------------------------------------------------
double CalcLots(double slDistance) {
   if (slDistance <= 0) return 0.01;

   double tickValue  = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSize   = MarketInfo(Symbol(), MODE_TICKSIZE);
   double riskAmount = AccountBalance() * RiskPercent / 100.0;

   // pips at risk
   double slPips = slDistance / tickSize;
   double lotSize = riskAmount / (slPips * tickValue);

   double minLot  = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot  = MarketInfo(Symbol(), MODE_MAXLOT);
   double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);

   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   lotSize = MathMax(minLot, MathMin(maxLot, lotSize));

   return lotSize;
}

// ----------------------------------------------------------------
int CountOrders(int type) {
   int count = 0;
   for (int i = OrdersTotal() - 1; i >= 0; i--) {
      if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         if (OrderMagicNumber() == MagicNumber && OrderSymbol() == Symbol() && OrderType() == type)
            count++;
   }
   return count;
}

// ----------------------------------------------------------------
void CloseOrders(int type) {
   for (int i = OrdersTotal() - 1; i >= 0; i--) {
      if (!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if (OrderMagicNumber() != MagicNumber)           continue;
      if (OrderSymbol()      != Symbol())               continue;
      if (OrderType()        != type)                   continue;

      double price = (type == OP_BUY) ? Bid : Ask;
      OrderClose(OrderTicket(), OrderLots(), price, 3, clrYellow);
   }
}
