// APEX_SMC_EA.mq4 — Advanced Smart Money Concepts Expert Advisor
// Full confluence strategy: Kill Zones + H4 Bias + Power of 3 + Liquidity Sweep +
//   CHoCH + BOS + Order Block + Fair Value Gap + OTE Fibonacci + Premium/Discount
//
// Entry requires ALL of the following to align:
//   1. London or New York kill zone active
//   2. H4 EMA50 confirms bias direction
//   3. Price in discount (buy) or premium (sell) zone
//   4. CHoCH detected (trend reversal signal)
//   5. BOS confirmed (new trend confirmation)
//   6. Order Block found in impulse direction
//   7. FVG found overlapping with Order Block
//   8. Price retraces into OTE zone (62-79% Fibonacci)
//
// Exit: Structural SL (large, beyond swing) | TP1 2:1 | TP2 4:1 | TP3 trailing
// Pair: EURUSD | Timeframe: H1

#property strict
#property description "APEX SMC EA — Full Confluence Smart Money Strategy"

//============================================================
//  SESSION INPUTS
//============================================================
extern int    GMT_Offset     = 2;     // Broker GMT offset (check bottom-right clock in MT4)
extern bool   Trade_London   = true;  // London Kill Zone: 7-10 AM GMT
extern bool   Trade_NewYork  = true;  // New York Kill Zone: 12-3 PM GMT
extern int    London_Start   = 7;
extern int    London_End     = 10;
extern int    NY_Start       = 12;
extern int    NY_End         = 15;

//============================================================
//  STRUCTURE INPUTS
//============================================================
extern int    SwingStrength  = 5;    // Bars each side to confirm a swing point
extern int    FVG_Lookback   = 40;   // Bars back to scan for FVG
extern int    OB_Lookback    = 60;   // Bars back to scan for Order Block
extern int    EqPips         = 3;    // Pip tolerance for equal highs/lows detection

//============================================================
//  OTE FIBONACCI ZONE
//============================================================
extern double OTE_Min        = 0.62; // Entry zone start (62% retrace)
extern double OTE_Max        = 0.79; // Entry zone end  (79% retrace — algorithmic midpoint)

//============================================================
//  RISK & TRADE MANAGEMENT
//============================================================
extern double RiskPercent    = 2.0;  // % of account risked per trade
extern bool   UseStructuralSL = true;// SL beyond swing (true) or ATR-based (false)
extern int    ATR_Period     = 14;
extern double ATR_SL_Mult    = 3.0;  // ATR multiplier for SL (large = breathes more)
extern double SL_Buffer_Pips = 8.0;  // Extra pips beyond swing for structural SL
extern double TP1_RR         = 2.0;  // TP1 close 1/3 at 2:1
extern double TP2_RR         = 4.0;  // TP2 close 1/3 at 4:1
extern double Trail_ATR      = 2.0;  // Trailing stop multiplier for final 1/3
extern bool   ShowLabels     = true;
extern int    MagicNumber    = 777888;

//============================================================
//  STATE MACHINE
//============================================================
#define STAGE_WAIT   0
#define STAGE_CHOCH  1
#define STAGE_BOS    2
#define STAGE_ENTRY  3

int    stage     = STAGE_WAIT;
int    bias      = 0;        // 1 = bullish, -1 = bearish
double impStart  = 0;        // swing point that began the impulse
double impEnd    = 0;        // level broken (=CHoCH level)
double chochLvl  = 0;
double bosLvl    = 0;

// Order Block
double obHi = 0, obLo = 0;
bool   obOK = false;

// Fair Value Gap
double fvgHi = 0, fvgLo = 0;
bool   fvgOK = false;

// OTE zone
double oteHi = 0, oteLo = 0;

// Structural SL level
double structSL = 0;

// Three-ticket scaling system
int ticket1 = -1, ticket2 = -1, ticket3 = -1;
bool tp1Done = false, tp2Done = false;
double trailSL = 0;

// Liquidity sweep
bool   sweepBull = false;
bool   sweepBear = false;
double sweepLvl  = 0;

//============================================================
int OnInit() {
   ResetState();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   ObjectsDeleteAll(0, "APEX_");
}

//============================================================
void OnTick() {
   static datetime lastBar = 0;
   if (Time[0] == lastBar) return;
   lastBar = Time[0];

   if (!IsTradeAllowed()) return;
   if (AccountFreeMargin() < 100) return;

   // Always manage open trades regardless of stage
   ManageTrades();

   // Don't open new trades if we already have open positions from this EA
   if (CountOrders() > 0) return;

   // Reset three-ticket state if all orders closed
   if (ticket1 == -1 && ticket2 == -1 && ticket3 == -1) {
      tp1Done = false;
      tp2Done = false;
   }

   switch (stage) {
      case STAGE_WAIT:  CheckForCHoCH(); break;
      case STAGE_CHOCH: CheckForBOS();   break;
      case STAGE_BOS:   CheckForBOS();   break;  // keep watching until BOS confirmed
      case STAGE_ENTRY: CheckForEntry(); break;
   }
}

//============================================================
//  STAGE 1 — CHoCH (Change of Character)
//  Prior downtrend (LH+LL) → price breaks above swing high = bullish CHoCH
//  Prior uptrend   (HH+HL) → price breaks below swing low  = bearish CHoCH
//============================================================
void CheckForCHoCH() {
   if (!IsInKillZone()) return;

   int h4bias = GetH4Bias();
   if (h4bias == 0) return;

   double sh1 = GetSwingHigh(1), sh2 = GetSwingHigh(2);
   double sl1 = GetSwingLow(1),  sl2 = GetSwingLow(2);
   if (sh1 == 0 || sh2 == 0 || sl1 == 0 || sl2 == 0) return;

   bool priorBull = (sh1 > sh2) && (sl1 > sl2);
   bool priorBear = (sh1 < sh2) && (sl1 < sl2);

   double c = Close[1];

   // Bullish CHoCH: was bearish, now broke swing high. H4 must agree.
   if (priorBear && c > sh1 && h4bias == 1) {
      // Price must be in discount zone (below 50% of recent range)
      if (!IsInDiscountZone(sl2, sh2)) return;

      // Bonus: was there a liquidity sweep below equal lows before this?
      DetectLiquiditySweep();

      bias     = 1;
      chochLvl = sh1;
      impStart = sl1;  // the swing low that was the bottom
      impEnd   = sh1;
      bosLvl   = sh2;  // must break previous swing high for BOS
      stage    = STAGE_CHOCH;

      if (ShowLabels) Label("CHoCH_Bull_"+TimeToStr(Time[1]), Time[1], Low[1]-30*_Point*10, "CHoCH↑", clrDodgerBlue);
   }

   // Bearish CHoCH: was bullish, now broke swing low. H4 must agree.
   if (priorBull && c < sl1 && h4bias == -1) {
      if (!IsInPremiumZone(sl2, sh2)) return;

      DetectLiquiditySweep();

      bias     = -1;
      chochLvl = sl1;
      impStart = sh1;
      impEnd   = sl1;
      bosLvl   = sl2;
      stage    = STAGE_CHOCH;

      if (ShowLabels) Label("CHoCH_Bear_"+TimeToStr(Time[1]), Time[1], High[1]+30*_Point*10, "CHoCH↓", clrOrangeRed);
   }
}

//============================================================
//  STAGE 2 — BOS (Break of Structure)
//  After CHoCH, price must make a HH (bull) or LL (bear) to confirm trend
//============================================================
void CheckForBOS() {
   double c = Close[1];
   double atr = iATR(NULL, 0, ATR_Period, 1);

   // Invalidate if price reverses too far against CHoCH direction
   if (bias ==  1 && c < impStart - atr * 1.5) { ResetState(); return; }
   if (bias == -1 && c > impStart + atr * 1.5) { ResetState(); return; }

   bool bosConfirmed = false;
   if (bias ==  1 && c > bosLvl) bosConfirmed = true;
   if (bias == -1 && c < bosLvl) bosConfirmed = true;

   if (!bosConfirmed) return;

   // BOS confirmed — find Order Block and FVG from the impulse
   obOK  = FindOrderBlock();
   fvgOK = FindFVG();
   CalcOTE();

   if (!fvgOK && !obOK) {
      // Need at least FVG or OB for a valid setup
      ResetState();
      return;
   }

   stage = STAGE_ENTRY;

   if (ShowLabels) Label("BOS_"+TimeToStr(Time[1]), Time[1],
      (bias == 1 ? Low[1]-40*_Point*10 : High[1]+40*_Point*10),
      "BOS"+(bias==1?"↑":"↓"), (bias==1 ? clrLime : clrRed));
}

//============================================================
//  STAGE 3 — Entry
//  Price must retrace into the OTE zone (62-79%) AND into FVG/OB zone
//  Both must overlap for highest confluence
//============================================================
void CheckForEntry() {
   if (!IsInKillZone()) return;
   if (CountOrders() > 0)  return;

   double atr = iATR(NULL, 0, ATR_Period, 1);

   // Recalculate OTE in case we need it
   CalcOTE();

   // --- Bullish Entry ---
   if (bias == 1) {
      double entryZoneHi = MathMin(oteHi, fvgOK ? fvgHi : oteHi);
      double entryZoneLo = MathMax(oteLo, fvgOK ? fvgLo : oteLo);

      // Check if OB overlaps with entry zone too (adds confluence)
      if (obOK) {
         entryZoneHi = MathMin(entryZoneHi, obHi);
         entryZoneLo = MathMax(entryZoneLo, obLo);
      }

      if (entryZoneHi <= entryZoneLo) {
         // No overlap — use FVG alone if OTE is close enough
         entryZoneHi = fvgOK ? fvgHi : oteHi;
         entryZoneLo = fvgOK ? fvgLo : oteLo;
      }

      if (Ask >= entryZoneLo && Ask <= entryZoneHi) {
         // Structural SL: below most recent swing low + buffer
         double swLow = GetSwingLow(1);
         if (UseStructuralSL && swLow > 0)
            structSL = swLow - SL_Buffer_Pips * Point * 10;
         else
            structSL = Ask - atr * ATR_SL_Mult;

         double slDist = Ask - structSL;
         if (slDist < atr * 0.5) structSL = Ask - atr * ATR_SL_Mult;
         slDist = Ask - structSL;

         double lots = CalcLots(slDist);
         if (lots <= 0) return;

         double lotsEach = MathMax(MarketInfo(Symbol(), MODE_MINLOT),
                           MathFloor(lots/3 / MarketInfo(Symbol(), MODE_LOTSTEP))
                           * MarketInfo(Symbol(), MODE_LOTSTEP));

         double tp1 = Ask + slDist * TP1_RR;
         double tp2 = Ask + slDist * TP2_RR;

         ticket1 = OrderSend(Symbol(), OP_BUY, lotsEach, Ask, 5, structSL, tp1, "APEX_TP1", MagicNumber, 0, clrGreen);
         ticket2 = OrderSend(Symbol(), OP_BUY, lotsEach, Ask, 5, structSL, tp2, "APEX_TP2", MagicNumber, 0, clrGreen);
         ticket3 = OrderSend(Symbol(), OP_BUY, lotsEach, Ask, 5, structSL, 0,   "APEX_TP3", MagicNumber, 0, clrGreen);
         trailSL = structSL;

         if (ticket1 > 0 || ticket2 > 0 || ticket3 > 0) {
            if (ShowLabels) Label("Entry_Bull_"+TimeToStr(Time[0]), Time[0], Low[0]-50*_Point*10,
               StringFormat("BUY SL:%.5f TP1:%.5f TP2:%.5f", structSL, tp1, tp2), clrGreen);
            ResetState();
         }
      }
   }

   // --- Bearish Entry ---
   if (bias == -1) {
      double entryZoneHi = MathMin(oteHi, fvgOK ? fvgHi : oteHi);
      double entryZoneLo = MathMax(oteLo, fvgOK ? fvgLo : oteLo);

      if (obOK) {
         entryZoneHi = MathMin(entryZoneHi, obHi);
         entryZoneLo = MathMax(entryZoneLo, obLo);
      }

      if (entryZoneHi <= entryZoneLo) {
         entryZoneHi = fvgOK ? fvgHi : oteHi;
         entryZoneLo = fvgOK ? fvgLo : oteLo;
      }

      if (Bid >= entryZoneLo && Bid <= entryZoneHi) {
         double swHigh = GetSwingHigh(1);
         if (UseStructuralSL && swHigh > 0)
            structSL = swHigh + SL_Buffer_Pips * Point * 10;
         else
            structSL = Bid + atr * ATR_SL_Mult;

         double slDist = structSL - Bid;
         if (slDist < atr * 0.5) structSL = Bid + atr * ATR_SL_Mult;
         slDist = structSL - Bid;

         double lots = CalcLots(slDist);
         if (lots <= 0) return;

         double lotsEach = MathMax(MarketInfo(Symbol(), MODE_MINLOT),
                           MathFloor(lots/3 / MarketInfo(Symbol(), MODE_LOTSTEP))
                           * MarketInfo(Symbol(), MODE_LOTSTEP));

         double tp1 = Bid - slDist * TP1_RR;
         double tp2 = Bid - slDist * TP2_RR;

         ticket1 = OrderSend(Symbol(), OP_SELL, lotsEach, Bid, 5, structSL, tp1, "APEX_TP1", MagicNumber, 0, clrRed);
         ticket2 = OrderSend(Symbol(), OP_SELL, lotsEach, Bid, 5, structSL, tp2, "APEX_TP2", MagicNumber, 0, clrRed);
         ticket3 = OrderSend(Symbol(), OP_SELL, lotsEach, Bid, 5, structSL, 0,   "APEX_TP3", MagicNumber, 0, clrRed);
         trailSL = structSL;

         if (ticket1 > 0 || ticket2 > 0 || ticket3 > 0) {
            if (ShowLabels) Label("Entry_Bear_"+TimeToStr(Time[0]), Time[0], High[0]+50*_Point*10,
               StringFormat("SELL SL:%.5f TP1:%.5f TP2:%.5f", structSL, tp1, tp2), clrRed);
            ResetState();
         }
      }
   }

   // Invalidate if price has moved completely past all zones
   double atrFade = atr * 3;
   if (bias ==  1 && Bid > impEnd + atrFade) ResetState();
   if (bias == -1 && Ask < impEnd - atrFade) ResetState();
}

//============================================================
//  TRADE MANAGEMENT: Move SL to BE after TP1, trail after TP2
//============================================================
void ManageTrades() {
   double atr = iATR(NULL, 0, ATR_Period, 1);

   // Check ticket3 (the trailing position)
   if (ticket3 > 0 && OrderSelect(ticket3, SELECT_BY_TICKET)) {
      if (OrderCloseTime() > 0) { ticket3 = -1; return; }

      int    type    = OrderType();
      double openPx  = OrderOpenPrice();
      double slNow   = OrderStopLoss();
      double newSL   = slNow;

      if (type == OP_BUY) {
         // Move SL to breakeven after TP1 hit
         if (!tp1Done && Bid > openPx + atr * TP1_RR) {
            newSL  = openPx + 5 * Point * 10;
            tp1Done = true;
         }
         // Trail after TP2 distance
         if (tp1Done) {
            double candidate = Bid - atr * Trail_ATR;
            if (candidate > newSL) newSL = candidate;
         }
      }

      if (type == OP_SELL) {
         if (!tp1Done && Ask < openPx - atr * TP1_RR) {
            newSL  = openPx - 5 * Point * 10;
            tp1Done = true;
         }
         if (tp1Done) {
            double candidate = Ask + atr * Trail_ATR;
            if (candidate < newSL) newSL = candidate;
         }
      }

      if (newSL != slNow && newSL > 0)
         OrderModify(ticket3, openPx, NormalizeDouble(newSL, Digits), OrderTakeProfit(), 0);
   } else if (ticket3 > 0) {
      ticket3 = -1;
   }

   // Clear closed tickets
   if (ticket1 > 0 && OrderSelect(ticket1, SELECT_BY_TICKET) && OrderCloseTime() > 0) ticket1 = -1;
   if (ticket2 > 0 && OrderSelect(ticket2, SELECT_BY_TICKET) && OrderCloseTime() > 0) ticket2 = -1;
}

//============================================================
//  H4 BIAS: Uses H4 EMA50. Price above = bullish, below = bearish.
//  Also requires H4 to have made HH (bull) or LL (bear) recently.
//============================================================
int GetH4Bias() {
   double h4ema   = iMA(NULL, PERIOD_H4, 50, 0, MODE_EMA, PRICE_CLOSE, 1);
   double h4close = iClose(NULL, PERIOD_H4, 1);
   if (h4ema == 0) return 0;
   if (h4close > h4ema) return  1;
   if (h4close < h4ema) return -1;
   return 0;
}

//============================================================
//  KILL ZONE CHECK: London or New York window active
//============================================================
bool IsInKillZone() {
   datetime gmtTime = TimeCurrent() - GMT_Offset * 3600;
   int h = TimeHour(gmtTime);

   if (Trade_London   && h >= London_Start && h < London_End) return true;
   if (Trade_NewYork  && h >= NY_Start     && h < NY_End)     return true;
   return false;
}

//============================================================
//  PREMIUM / DISCOUNT ZONE
//  Uses the last clear swing range to determine 50% equilibrium
//============================================================
bool IsInDiscountZone(double rangeLow, double rangeHigh) {
   if (rangeHigh <= rangeLow) return true;
   double mid = (rangeHigh + rangeLow) / 2.0;
   return Ask < mid;   // discount = below 50%
}

bool IsInPremiumZone(double rangeLow, double rangeHigh) {
   if (rangeHigh <= rangeLow) return true;
   double mid = (rangeHigh + rangeLow) / 2.0;
   return Bid > mid;   // premium = above 50%
}

//============================================================
//  FIND ORDER BLOCK
//  Bullish OB: last bearish candle before the bullish impulse
//  Bearish OB: last bullish candle before the bearish impulse
//============================================================
bool FindOrderBlock() {
   for (int i = 1; i < OB_Lookback; i++) {
      double bodyHi = MathMax(Open[i], Close[i]);
      double bodyLo = MathMin(Open[i], Close[i]);

      if (bias == 1 && Close[i] < Open[i]) {
         // Bearish candle — check if followed by strong bullish move
         if (Close[i-1] > High[i]) {
            obHi = High[i];
            obLo = Low[i];
            return true;
         }
      }
      if (bias == -1 && Close[i] > Open[i]) {
         // Bullish candle — check if followed by strong bearish move
         if (Close[i-1] < Low[i]) {
            obHi = High[i];
            obLo = Low[i];
            return true;
         }
      }
   }
   return false;
}

//============================================================
//  FIND FAIR VALUE GAP (FVG)
//  Bullish FVG: High[i+1] < Low[i-1] — imbalance between candle 1 and 3
//  Bearish FVG: Low[i+1]  > High[i-1]
//  Quality filter: no wick overlap allowed
//============================================================
bool FindFVG() {
   for (int i = 1; i < FVG_Lookback - 1; i++) {
      if (bias == 1 && High[i+1] < Low[i-1]) {
         // Verify no wick overlap (high quality FVG)
         if (Low[i] > High[i+1] && High[i] < Low[i-1]) {
            fvgLo = High[i+1];
            fvgHi = Low[i-1];
            if (fvgHi > fvgLo) return true;
         }
      }
      if (bias == -1 && Low[i+1] > High[i-1]) {
         if (High[i] < Low[i+1] && Low[i] > High[i-1]) {
            fvgLo = High[i-1];
            fvgHi = Low[i+1];
            if (fvgHi > fvgLo) return true;
         }
      }
   }
   // Allow slightly lower quality FVG if no high-quality found
   for (int i = 1; i < FVG_Lookback - 1; i++) {
      if (bias == 1 && High[i+1] < Low[i-1]) {
         fvgLo = High[i+1];
         fvgHi = Low[i-1];
         if (fvgHi > fvgLo) return true;
      }
      if (bias == -1 && Low[i+1] > High[i-1]) {
         fvgLo = High[i-1];
         fvgHi = Low[i+1];
         if (fvgHi > fvgLo) return true;
      }
   }
   return false;
}

//============================================================
//  OTE FIBONACCI ZONE (62% - 79% retracement of impulse)
//  Impulse: from impStart to impEnd (the move that caused CHoCH/BOS)
//============================================================
void CalcOTE() {
   if (impStart == 0 || impEnd == 0) return;
   double range = MathAbs(impEnd - impStart);
   if (range == 0) return;

   if (bias == 1) {
      // Bullish impulse went UP from impStart to impEnd
      // OTE retracement = 62-79% back DOWN from impEnd
      oteHi = impEnd - range * OTE_Min;
      oteLo = impEnd - range * OTE_Max;
   } else {
      // Bearish impulse went DOWN from impStart to impEnd
      // OTE retracement = 62-79% back UP from impEnd
      oteLo = impEnd + range * OTE_Min;
      oteHi = impEnd + range * OTE_Max;
   }
}

//============================================================
//  LIQUIDITY SWEEP DETECTION
//  Equal lows swept (bullish) or equal highs swept (bearish)
//============================================================
void DetectLiquiditySweep() {
   double eqTol = EqPips * Point * 10;
   sweepBull = false;
   sweepBear = false;

   // Find two equal lows (potential buy-side liquidity)
   for (int i = 3; i < 50; i++) {
      for (int j = i+1; j < 50; j++) {
         // Equal lows within tolerance
         if (MathAbs(Low[i] - Low[j]) < eqTol) {
            double eqLevel = (Low[i] + Low[j]) / 2.0;
            // Check if price swept below then recovered
            bool swept = false;
            for (int k = 1; k < i; k++) {
               if (Low[k] < eqLevel - eqTol) { swept = true; break; }
            }
            if (swept && Close[1] > eqLevel) {
               sweepBull = true;
               sweepLvl  = eqLevel;
               if (ShowLabels) Label("Sweep_Bull_"+TimeToStr(Time[i]), Time[i], Low[i]-20*_Point*10, "Sweep↑", clrAqua);
               return;
            }
         }
         // Equal highs
         if (MathAbs(High[i] - High[j]) < eqTol) {
            double eqLevel = (High[i] + High[j]) / 2.0;
            bool swept = false;
            for (int k = 1; k < i; k++) {
               if (High[k] > eqLevel + eqTol) { swept = true; break; }
            }
            if (swept && Close[1] < eqLevel) {
               sweepBear = true;
               sweepLvl  = eqLevel;
               if (ShowLabels) Label("Sweep_Bear_"+TimeToStr(Time[i]), Time[i], High[i]+20*_Point*10, "Sweep↓", clrMagenta);
               return;
            }
         }
      }
   }
}

//============================================================
//  SWING POINT DETECTION
//============================================================
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

double GetSwingHigh(int n) {
   int count = 0;
   for (int i = SwingStrength + 1; i < 400; i++) {
      if (IsSwingHigh(i)) { count++; if (count == n) return High[i]; }
   }
   return 0;
}

double GetSwingLow(int n) {
   int count = 0;
   for (int i = SwingStrength + 1; i < 400; i++) {
      if (IsSwingLow(i)) { count++; if (count == n) return Low[i]; }
   }
   return 0;
}

//============================================================
//  POSITION SIZING: Risk RiskPercent% of balance
//============================================================
double CalcLots(double slDistance) {
   if (slDistance <= 0) return MarketInfo(Symbol(), MODE_MINLOT);
   double tickValue  = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSize   = MarketInfo(Symbol(), MODE_TICKSIZE);
   double riskAmount = AccountBalance() * RiskPercent / 100.0;
   double slTicks    = slDistance / tickSize;
   double lotSize    = riskAmount / (slTicks * tickValue);
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
   impStart = 0;
   impEnd   = 0;
   chochLvl = 0;
   bosLvl   = 0;
   obOK     = false;
   fvgOK    = false;
   oteHi    = 0;
   oteLo    = 0;
   structSL = 0;
}

void Label(string name, datetime t, double price, string txt, color clr) {
   string n = "APEX_" + name;
   if (ObjectFind(n) >= 0) ObjectDelete(n);
   ObjectCreate(n, OBJ_TEXT, 0, t, price);
   ObjectSetString(0, n, OBJPROP_TEXT, txt);
   ObjectSet(n, OBJPROP_COLOR, clr);
   ObjectSet(n, OBJPROP_FONTSIZE, 7);
}
