// SMC_EA.mq4 — Smart Money Concepts Expert Advisor
// Strategy: Trade only when FVG + BOS + CHoCH all align
// Recommended: EURUSD H1 / H4
// Logic:
//   1. Detect prior trend from swing structure (HH/HL or LH/LL)
//   2. CHoCH: price breaks structure against prior trend (reversal signal)
//   3. BOS:   price then breaks structure IN new direction (confirmation)
//   4. FVG:   find imbalance candle formed during the impulse move
//   5. Entry: price retraces back into FVG zone → trade with SL/TP

#property strict

//--- Inputs
extern int    SwingStrength  = 5;     // bars each side to confirm swing point
extern int    FVG_Lookback   = 40;    // how many bars back to scan for FVG
extern int    ATR_Period     = 14;
extern double ATR_SL_Mult    = 1.5;   // SL = ATR * this (below/above FVG)
extern double ATR_TP_Mult    = 3.0;   // TP = ATR * this (2:1 minimum RR)
extern double RiskPercent    = 1.0;   // % of balance risked per trade
extern bool   ShowLabels     = true;  // show structure labels on chart
extern int    MagicNumber    = 334455;

//--- State machine stages
#define STAGE_WAIT   0   // looking for CHoCH
#define STAGE_CHOCH  1   // CHoCH confirmed, waiting for BOS
#define STAGE_TRADE  2   // BOS confirmed, waiting for FVG entry

int    stage       = STAGE_WAIT;
int    bias        = 0;    // 1=bullish, -1=bearish (direction after CHoCH)
double chochPrice  = 0;    // level broken for CHoCH
double bosTarget   = 0;    // level that must break to confirm BOS
double fvgTop      = 0;    // FVG upper boundary
double fvgBot      = 0;    // FVG lower boundary
bool   fvgFound    = false;

//================================================================
int OnInit() {
   stage    = STAGE_WAIT;
   bias     = 0;
   fvgFound = false;
   return INIT_SUCCEEDED;
}

//================================================================
void OnTick() {
   static datetime lastBar = 0;
   if (Time[0] == lastBar) return;
   lastBar = Time[0];

   if (!IsTradeAllowed())              return;
   if (AccountFreeMargin() < 50)       return;
   if (CountOrders() > 0)              return;

   // Step through the state machine each new bar
   switch (stage) {
      case STAGE_WAIT:  CheckForCHoCH(); break;
      case STAGE_CHOCH: CheckForBOS();   break;
      case STAGE_TRADE: CheckForEntry(); break;
   }
}

//================================================================
// STAGE 1 — Detect Change of Character (CHoCH)
// Requires: prior trend established, price breaks against it
//================================================================
void CheckForCHoCH() {
   // Gather last 4 swing points to determine prior trend
   double sh1 = GetSwingHigh(1);  // most recent swing high
   double sh2 = GetSwingHigh(2);  // second most recent
   double sl1 = GetSwingLow(1);
   double sl2 = GetSwingLow(2);

   if (sh1 == 0 || sh2 == 0 || sl1 == 0 || sl2 == 0) return;

   bool priorBull = (sh1 > sh2) && (sl1 > sl2);  // HH + HL = uptrend
   bool priorBear = (sh1 < sh2) && (sl1 < sl2);  // LH + LL = downtrend

   double c = Close[1];  // last closed bar

   // Bearish CHoCH: was uptrend, price breaks below most recent swing low
   if (priorBull && c < sl1) {
      bias       = -1;
      chochPrice = sl1;
      bosTarget  = sl2;   // must break prev swing low to confirm BOS
      stage      = STAGE_CHOCH;
      if (ShowLabels) DrawLabel("CHoCH_Bear", Time[1], High[1] + 20*Point, "CHoCH↓", clrOrange);
      return;
   }

   // Bullish CHoCH: was downtrend, price breaks above most recent swing high
   if (priorBear && c > sh1) {
      bias       = 1;
      chochPrice = sh1;
      bosTarget  = sh2;   // must break prev swing high to confirm BOS
      stage      = STAGE_CHOCH;
      if (ShowLabels) DrawLabel("CHoCH_Bull", Time[1], Low[1] - 20*Point, "CHoCH↑", clrDodgerBlue);
      return;
   }
}

//================================================================
// STAGE 2 — Detect Break of Structure (BOS)
// Requires: price continues in CHoCH direction and breaks bosTarget
//================================================================
void CheckForBOS() {
   double c = Close[1];

   bool bosConfirmed = false;

   if (bias == 1  && c > bosTarget) bosConfirmed = true;   // bullish BOS
   if (bias == -1 && c < bosTarget) bosConfirmed = true;   // bearish BOS

   if (!bosConfirmed) {
      // Invalidate if price reverses past CHoCH in wrong direction
      if (bias ==  1 && c < chochPrice - iATR(NULL,0,ATR_Period,1)) { stage = STAGE_WAIT; return; }
      if (bias == -1 && c > chochPrice + iATR(NULL,0,ATR_Period,1)) { stage = STAGE_WAIT; return; }
      return;
   }

   // BOS confirmed — now look for FVG formed during the impulse
   fvgFound = FindFVG();

   if (fvgFound) {
      stage = STAGE_TRADE;
      if (ShowLabels) DrawLabel("BOS", Time[1], (bias==1 ? Low[1]-30*Point : High[1]+30*Point),
                                "BOS"+(bias==1?"↑":"↓"), (bias==1 ? clrLime : clrRed));
   } else {
      // BOS confirmed but no FVG yet — wait one more stage check
      stage = STAGE_TRADE;
   }
}

//================================================================
// STAGE 3 — Find FVG and enter when price retraces into it
//================================================================
void CheckForEntry() {
   // Keep scanning for FVG if not found yet
   if (!fvgFound) fvgFound = FindFVG();
   if (!fvgFound) return;

   double atr = iATR(NULL, 0, ATR_Period, 1);

   // Bullish entry: price retraces down into bullish FVG
   if (bias == 1 && Ask >= fvgBot && Ask <= fvgTop) {
      double sl   = fvgBot - atr * ATR_SL_Mult;
      double tp   = Ask   + atr * ATR_TP_Mult;
      double lots = CalcLots(Ask - sl);
      if (lots <= 0) return;

      int ticket = OrderSend(Symbol(), OP_BUY, lots, Ask, 3, sl, tp, "SMC_BUY", MagicNumber, 0, clrGreen);
      if (ticket > 0) {
         if (ShowLabels) DrawLabel("Entry_Bull", Time[0], Low[0]-40*Point, "FVG Entry↑", clrGreen);
         ResetState();
      }
   }

   // Bearish entry: price retraces up into bearish FVG
   if (bias == -1 && Bid <= fvgTop && Bid >= fvgBot) {
      double sl   = fvgTop + atr * ATR_SL_Mult;
      double tp   = Bid   - atr * ATR_TP_Mult;
      double lots = CalcLots(sl - Bid);
      if (lots <= 0) return;

      int ticket = OrderSend(Symbol(), OP_SELL, lots, Bid, 3, sl, tp, "SMC_SELL", MagicNumber, 0, clrRed);
      if (ticket > 0) {
         if (ShowLabels) DrawLabel("Entry_Bear", Time[0], High[0]+40*Point, "FVG Entry↓", clrRed);
         ResetState();
      }
   }

   // Invalidate if price has moved too far away from FVG (missed it)
   if (bias ==  1 && Ask > fvgTop * 1.002) { stage = STAGE_WAIT; fvgFound = false; }
   if (bias == -1 && Bid < fvgBot * 0.998) { stage = STAGE_WAIT; fvgFound = false; }
}

//================================================================
// Scan recent bars for a Fair Value Gap (3-candle imbalance)
// Bullish FVG: High[i+1] < Low[i-1]  — gap between candle 1 and candle 3
// Bearish FVG: Low[i+1]  > High[i-1] — gap between candle 1 and candle 3
//================================================================
bool FindFVG() {
   for (int i = 1; i < FVG_Lookback - 1; i++) {
      if (bias == 1) {
         // Bullish FVG: middle candle is impulsive up, gap left below it
         if (High[i+1] < Low[i-1]) {
            fvgBot = High[i+1];
            fvgTop = Low[i-1];
            if (fvgTop > fvgBot) return true;
         }
      }
      if (bias == -1) {
         // Bearish FVG: middle candle is impulsive down, gap left above it
         if (Low[i+1] > High[i-1]) {
            fvgBot = High[i-1];
            fvgTop = Low[i+1];
            if (fvgTop > fvgBot) return true;
         }
      }
   }
   return false;
}

//================================================================
// Find the Nth most recent confirmed swing high
//================================================================
double GetSwingHigh(int n) {
   int count = 0;
   for (int i = SwingStrength + 1; i < 300; i++) {
      if (IsSwingHigh(i)) {
         count++;
         if (count == n) return High[i];
      }
   }
   return 0;
}

double GetSwingLow(int n) {
   int count = 0;
   for (int i = SwingStrength + 1; i < 300; i++) {
      if (IsSwingLow(i)) {
         count++;
         if (count == n) return Low[i];
      }
   }
   return 0;
}

bool IsSwingHigh(int i) {
   if (i <= SwingStrength || i + SwingStrength >= Bars) return false;
   for (int j = 1; j <= SwingStrength; j++)
      if (High[i-j] >= High[i] || High[i+j] >= High[i]) return false;
   return true;
}

bool IsSwingLow(int i) {
   if (i <= SwingStrength || i + SwingStrength >= Bars) return false;
   for (int j = 1; j <= SwingStrength; j++)
      if (Low[i-j] <= Low[i] || Low[i+j] <= Low[i]) return false;
   return true;
}

//================================================================
double CalcLots(double slDistance) {
   if (slDistance <= 0) return MarketInfo(Symbol(), MODE_MINLOT);
   double tickValue  = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSize   = MarketInfo(Symbol(), MODE_TICKSIZE);
   double riskAmount = AccountBalance() * RiskPercent / 100.0;
   double slPips     = slDistance / tickSize;
   double lotSize    = riskAmount / (slPips * tickValue);
   double minLot     = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot     = MarketInfo(Symbol(), MODE_MAXLOT);
   double lotStep    = MarketInfo(Symbol(), MODE_LOTSTEP);
   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   return MathMax(minLot, MathMin(maxLot, lotSize));
}

int CountOrders() {
   int count = 0;
   for (int i = OrdersTotal() - 1; i >= 0; i--)
      if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         if (OrderMagicNumber() == MagicNumber && OrderSymbol() == Symbol())
            count++;
   return count;
}

void ResetState() {
   stage    = STAGE_WAIT;
   bias     = 0;
   fvgFound = false;
   fvgTop   = 0;
   fvgBot   = 0;
}

void DrawLabel(string name, datetime t, double price, string txt, color clr) {
   if (ObjectFind(name) >= 0) ObjectDelete(name);
   ObjectCreate(name, OBJ_TEXT, 0, t, price);
   ObjectSetString(0, name, OBJPROP_TEXT, txt);
   ObjectSet(name, OBJPROP_COLOR, clr);
   ObjectSet(name, OBJPROP_FONTSIZE, 8);
}
