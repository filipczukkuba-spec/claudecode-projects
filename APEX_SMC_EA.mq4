// APEX_SMC_EA.mq4 v3 — Day Trading Edition
// Redesigned for M15: ~15-30 trades/month instead of 3/year
//
// TWO SETUP TYPES run simultaneously:
//   A) BOS CONTINUATION — trend continues, enter FVG pullback (most frequent)
//   B) CHoCH REVERSAL   — trend reverses, enter FVG after confirmation (less frequent)
//
// MINIMUM REQUIREMENTS (much looser than v2):
//   - In session window
//   - ADX > threshold (trending market only)
//   - BOS or CHoCH detected
//   - FVG or Order Block found
//   → That's it. No premium/discount, no strict H4 filter, no OTE requirement.
//
// OPTIONAL FILTERS (each can be turned on/off):
//   - H4 EMA50 bias confirmation
//   - OTE Fibonacci zone
//   - News blackout
//
// Exit: Structural SL | TP1 2:1 | TP2 4:1 | TP3 trailing
// Recommended: EURUSD M15

#property strict
#property description "APEX SMC Day Trading EA v3"

//============================================================
//  SESSION
//============================================================
extern int    GMT_Offset      = 2;     // Broker server GMT offset
extern int    Session_Start   = 7;     // GMT hour to start trading (London open)
extern int    Session_End     = 17;    // GMT hour to stop trading
extern bool   Trade_London    = true;  // Extra filter: only London+NY windows
extern int    London_Start    = 7;
extern int    London_End      = 11;
extern int    NY_Start        = 12;
extern int    NY_End          = 17;

//============================================================
//  STRUCTURE
//============================================================
extern int    SwingStrength   = 3;    // Lower = more swings detected (M15 default)
extern int    FVG_Lookback    = 20;   // Bars back to find FVG
extern int    OB_Lookback     = 30;   // Bars back to find Order Block
extern int    MaxBarsInSetup  = 50;   // Reset if no entry after this many bars
extern int    EqPips          = 3;

//============================================================
//  OPTIONAL FILTERS (turn off to get more trades)
//============================================================
extern bool   UseH4Bias       = true;  // Require H4 EMA50 agreement
extern bool   UseOTE          = false; // Require 62-79% retrace zone (reduces trades)
extern double OTE_Min         = 0.50;  // Relaxed to 50% (was 62%)
extern double OTE_Max         = 0.79;
extern bool   UseADXFilter    = true;  // Only trade when market is trending
extern int    ADX_Period      = 14;
extern double ADX_Min         = 18;    // Min ADX to consider trending

//============================================================
//  RISK
//============================================================
extern double RiskPercent     = 2.0;
extern bool   UseStructuralSL = true;
extern int    ATR_Period      = 14;
extern double ATR_SL_Mult     = 2.0;
extern double SL_Buffer_Pips  = 5.0;
extern double TP1_RR          = 2.0;
extern double TP2_RR          = 4.0;
extern double Trail_ATR       = 1.5;
extern int    MaxOpenTrades   = 1;     // Max simultaneous trades from this EA

//============================================================
//  VISUALS
//============================================================
extern bool   ShowZoneBoxes   = true;
extern bool   ShowLabels      = true;
extern int    BoxProjectBars  = 50;
extern color  FVG_Bull_Color  = C'0,80,0';
extern color  FVG_Bear_Color  = C'80,0,0';
extern color  OB_Bull_Color   = C'0,40,100';
extern color  OB_Bear_Color   = C'100,30,0';
extern color  OTE_Color       = C'70,50,0';
extern int    MagicNumber     = 777888;

//============================================================
//  NEWS FILTER
//============================================================
extern bool   UseNewsFilter   = true;
extern int    News_MinsBefore = 30;
extern int    News_MinsAfter  = 15;
extern int    News_TZ_Offset  = -5;
extern string News_URL        = "https://nfs.faireconomy.media/ff_calendar_thisweek.json";

//============================================================
//  SETUP A STATE — BOS Continuation
//============================================================
bool   bosSetupActive = false;
int    bosBias        = 0;     // 1=bull, -1=bear
double bosLevel       = 0;     // level that was broken
double bosImpStart    = 0;
double bosImpEnd      = 0;
double bosFvgHi       = 0, bosFvgLo = 0;
bool   bosFvgOK       = false;
double bosObHi        = 0, bosObLo  = 0;
bool   bosObOK        = false;
double bosOteHi       = 0, bosOteLo = 0;
double bosStructSL    = 0;
int    bosSetupBar    = 0;

//============================================================
//  SETUP B STATE — CHoCH Reversal
//============================================================
bool   chochSetupActive = false;
int    chochBias        = 0;
double chochLevel       = 0;
double chochBosTarget   = 0;
double chochImpStart    = 0;
double chochImpEnd      = 0;
double chochFvgHi       = 0, chochFvgLo = 0;
bool   chochFvgOK       = false;
double chochObHi        = 0, chochObLo  = 0;
bool   chochObOK        = false;
double chochOteHi       = 0, chochOteLo = 0;
double chochStructSL    = 0;
int    chochSetupBar    = 0;
bool   chochBOSDone     = false;

//============================================================
//  TRADE TICKETS
//============================================================
int    ticket1 = -1, ticket2 = -1, ticket3 = -1;
bool   tp1Done = false;

//============================================================
//  NEWS CACHE
//============================================================
datetime newsEventTimes[100];
int      newsCount     = 0;
datetime lastNewsFetch = 0;

//============================================================
int OnInit() {
   ResetBOS();
   ResetCHoCH();
   if (UseNewsFilter) FetchNews();
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
   if (AccountFreeMargin() < 50) return;

   if (UseNewsFilter && TimeCurrent() - lastNewsFetch > 3600)
      FetchNews();

   ManageTrades();

   // Both setups run independently — more chances each session
   RunBOSContinuation();
   RunCHoCHReversal();
}

//============================================================
//  SETUP A: BOS CONTINUATION
//  Trend → BOS occurs → FVG forms → price retraces → enter
//  This fires frequently because every swing break is checked
//============================================================
void RunBOSContinuation() {
   if (!IsInSession()) return;
   if (CountOrders() >= MaxOpenTrades) return;

   // Stage 1: look for a new BOS
   if (!bosSetupActive) {
      DetectBOSContinuation();
      return;
   }

   // Timeout: reset if no entry after MaxBarsInSetup bars
   if (Bars - bosSetupBar > MaxBarsInSetup) { ResetBOS(); return; }

   // Stage 2: wait for price to retrace into FVG/OB
   CheckBOSEntry();
}

void DetectBOSContinuation() {
   double sh1 = GetSwingHigh(1), sh2 = GetSwingHigh(2);
   double sl1 = GetSwingLow(1),  sl2 = GetSwingLow(2);
   if (sh1==0 || sh2==0 || sl1==0 || sl2==0) return;

   double c = Close[1];

   // Use ADX to confirm trending
   if (UseADXFilter && iADX(NULL,0,ADX_Period,PRICE_CLOSE,MODE_MAIN,1) < ADX_Min) return;

   // Bullish BOS: trending up (HH+HL) AND price breaks above latest SH
   bool bullTrend = (sh1 > sh2) && (sl1 > sl2);
   if (bullTrend && c > sh1) {
      if (UseH4Bias && GetH4Bias() != 1) return;
      bosBias     = 1;
      bosLevel    = sh1;
      bosImpStart = sl1;
      bosImpEnd   = sh1;
      bosFvgOK    = FindFVG(1, bosFvgHi, bosFvgLo);
      bosObOK     = FindOB(1, bosObHi, bosObLo);
      if (!bosFvgOK && !bosObOK) return;
      CalcOTEZone(sl1, sh1, 1, bosOteHi, bosOteLo);
      bosSetupActive = true;
      bosSetupBar    = Bars;
      DrawSetupBoxes("BOS", 1, bosFvgOK, bosFvgHi, bosFvgLo, bosObOK, bosObHi, bosObLo, bosOteHi, bosOteLo);
      if (ShowLabels) DrawHLine("APEX_BOS_LVL_A", bosLevel, clrLime, STYLE_SOLID);
      if (ShowLabels) Label("BOS_A_"+TimeToStr(Time[1]), Time[1], Low[1]-30*_Point*10, "BOS↑", clrLime);
   }

   // Bearish BOS: trending down (LH+LL) AND price breaks below latest SL
   bool bearTrend = (sh1 < sh2) && (sl1 < sl2);
   if (bearTrend && c < sl1) {
      if (UseH4Bias && GetH4Bias() != -1) return;
      bosBias     = -1;
      bosLevel    = sl1;
      bosImpStart = sh1;
      bosImpEnd   = sl1;
      bosFvgOK    = FindFVG(-1, bosFvgHi, bosFvgLo);
      bosObOK     = FindOB(-1, bosObHi, bosObLo);
      if (!bosFvgOK && !bosObOK) return;
      CalcOTEZone(sh1, sl1, -1, bosOteHi, bosOteLo);
      bosSetupActive = true;
      bosSetupBar    = Bars;
      DrawSetupBoxes("BOS", -1, bosFvgOK, bosFvgHi, bosFvgLo, bosObOK, bosObHi, bosObLo, bosOteHi, bosOteLo);
      if (ShowLabels) DrawHLine("APEX_BOS_LVL_A", bosLevel, clrRed, STYLE_SOLID);
      if (ShowLabels) Label("BOS_A_"+TimeToStr(Time[1]), Time[1], High[1]+30*_Point*10, "BOS↓", clrRed);
   }
}

void CheckBOSEntry() {
   if (IsNewsBlackout()) return;

   double entHi, entLo;
   BuildEntryZone(bosBias, bosFvgOK, bosFvgHi, bosFvgLo,
                  bosObOK, bosObHi, bosObLo,
                  bosOteHi, bosOteLo, entHi, entLo);

   if (bosBias == 1 && Ask >= entLo && Ask <= entHi) {
      double sl = CalcStructuralSL(1, bosImpStart);
      if (sl == 0) { ResetBOS(); return; }
      EnterTrade(OP_BUY, Ask, sl, "A");
      ResetBOS();
   }
   if (bosBias == -1 && Bid <= entHi && Bid >= entLo) {
      double sl = CalcStructuralSL(-1, bosImpStart);
      if (sl == 0) { ResetBOS(); return; }
      EnterTrade(OP_SELL, Bid, sl, "A");
      ResetBOS();
   }

   // Invalidate if price moved far past entry zone
   double atr = iATR(NULL, 0, ATR_Period, 1);
   if (bosBias ==  1 && Bid > bosImpEnd + atr * 2) ResetBOS();
   if (bosBias == -1 && Ask < bosImpEnd - atr * 2) ResetBOS();
}

//============================================================
//  SETUP B: CHoCH REVERSAL
//  Downtrend → CHoCH up → BOS confirms → FVG entry (or vice versa)
//============================================================
void RunCHoCHReversal() {
   if (!IsInSession()) return;
   if (CountOrders() >= MaxOpenTrades) return;

   if (!chochSetupActive) {
      DetectCHoCH();
      return;
   }

   if (Bars - chochSetupBar > MaxBarsInSetup) { ResetCHoCH(); return; }

   if (!chochBOSDone) {
      WaitForCHoCHBOS();
   } else {
      CheckCHoCHEntry();
   }
}

void DetectCHoCH() {
   double sh1 = GetSwingHigh(1), sh2 = GetSwingHigh(2);
   double sl1 = GetSwingLow(1),  sl2 = GetSwingLow(2);
   if (sh1==0 || sh2==0 || sl1==0 || sl2==0) return;

   if (UseADXFilter && iADX(NULL,0,ADX_Period,PRICE_CLOSE,MODE_MAIN,1) < ADX_Min) return;

   double c = Close[1];
   bool priorBull = (sh1 > sh2) && (sl1 > sl2);
   bool priorBear = (sh1 < sh2) && (sl1 < sl2);

   // Bullish CHoCH: was downtrend, now breaks swing high
   if (priorBear && c > sh1) {
      chochBias       = 1;
      chochLevel      = sh1;
      chochBosTarget  = sh2;
      chochImpStart   = sl1;
      chochImpEnd     = sh1;
      chochSetupActive = true;
      chochBOSDone    = false;
      chochSetupBar   = Bars;
      if (ShowLabels) {
         DrawHLine("APEX_CHOCH_LVL", chochLevel, clrDodgerBlue, STYLE_DASH);
         Label("CHoCH_B_"+TimeToStr(Time[1]), Time[1], Low[1]-25*_Point*10, "CHoCH↑", clrDodgerBlue);
      }
   }

   // Bearish CHoCH: was uptrend, now breaks swing low
   if (priorBull && c < sl1) {
      chochBias       = -1;
      chochLevel      = sl1;
      chochBosTarget  = sl2;
      chochImpStart   = sh1;
      chochImpEnd     = sl1;
      chochSetupActive = true;
      chochBOSDone    = false;
      chochSetupBar   = Bars;
      if (ShowLabels) {
         DrawHLine("APEX_CHOCH_LVL", chochLevel, clrOrangeRed, STYLE_DASH);
         Label("CHoCH_S_"+TimeToStr(Time[1]), Time[1], High[1]+25*_Point*10, "CHoCH↓", clrOrangeRed);
      }
   }
}

void WaitForCHoCHBOS() {
   double c   = Close[1];
   double atr = iATR(NULL, 0, ATR_Period, 1);

   // Invalidate if price reverses past CHoCH
   if (chochBias ==  1 && c < chochImpStart - atr) { ResetCHoCH(); return; }
   if (chochBias == -1 && c > chochImpStart + atr) { ResetCHoCH(); return; }

   bool bosOk = (chochBias == 1 && c > chochBosTarget) ||
                (chochBias == -1 && c < chochBosTarget);
   if (!bosOk) return;

   chochBOSDone = true;
   chochFvgOK   = FindFVG(chochBias, chochFvgHi, chochFvgLo);
   chochObOK    = FindOB(chochBias, chochObHi, chochObLo);
   if (!chochFvgOK && !chochObOK) { ResetCHoCH(); return; }
   CalcOTEZone(chochImpStart, chochImpEnd, chochBias, chochOteHi, chochOteLo);
   DrawSetupBoxes("CHOCH", chochBias, chochFvgOK, chochFvgHi, chochFvgLo,
                  chochObOK, chochObHi, chochObLo, chochOteHi, chochOteLo);
   if (ShowLabels) DrawHLine("APEX_BOS_LVL_B", chochBosTarget, (chochBias==1?clrLime:clrRed), STYLE_SOLID);
}

void CheckCHoCHEntry() {
   if (IsNewsBlackout()) return;

   double entHi, entLo;
   BuildEntryZone(chochBias, chochFvgOK, chochFvgHi, chochFvgLo,
                  chochObOK, chochObHi, chochObLo,
                  chochOteHi, chochOteLo, entHi, entLo);

   if (chochBias == 1 && Ask >= entLo && Ask <= entHi) {
      double sl = CalcStructuralSL(1, chochImpStart);
      if (sl == 0) { ResetCHoCH(); return; }
      EnterTrade(OP_BUY, Ask, sl, "B");
      ResetCHoCH();
   }
   if (chochBias == -1 && Bid <= entHi && Bid >= entLo) {
      double sl = CalcStructuralSL(-1, chochImpStart);
      if (sl == 0) { ResetCHoCH(); return; }
      EnterTrade(OP_SELL, Bid, sl, "B");
      ResetCHoCH();
   }

   double atr = iATR(NULL, 0, ATR_Period, 1);
   if (chochBias ==  1 && Bid > chochImpEnd + atr * 2) ResetCHoCH();
   if (chochBias == -1 && Ask < chochImpEnd - atr * 2) ResetCHoCH();
}

//============================================================
//  ENTRY ZONE: Intersect FVG + OB + OTE (or use whatever is available)
//============================================================
void BuildEntryZone(int dir, bool fvgOK, double fHi, double fLo,
                    bool obOK, double oHi, double oLo,
                    double oteH, double oteL,
                    double &eHi, double &eLo) {
   // Start with FVG zone (primary), fall back to OB, then OTE
   if (fvgOK)      { eHi = fHi; eLo = fLo; }
   else if (obOK)  { eHi = oHi; eLo = oLo; }
   else            { eHi = oteH; eLo = oteL; }

   // Intersect with OB if both available
   if (fvgOK && obOK) {
      eHi = MathMin(eHi, oHi);
      eLo = MathMax(eLo, oLo);
      if (eHi <= eLo) { eHi = fHi; eLo = fLo; } // fallback if no overlap
   }

   // Intersect with OTE if enabled
   if (UseOTE && oteH > 0 && oteL > 0) {
      eHi = MathMin(eHi, oteH);
      eLo = MathMax(eLo, oteL);
      if (eHi <= eLo) { eHi = fvgOK?fHi:oteH; eLo = fvgOK?fLo:oteL; }
   }
}

//============================================================
//  PLACE THREE ORDERS (1/3 each: TP1, TP2, trailing)
//============================================================
void EnterTrade(int type, double price, double sl, string tag) {
   if (sl <= 0) return;
   double slDist = (type==OP_BUY) ? price - sl : sl - price;
   if (slDist <= 0) return;

   double lots    = CalcLots(slDist);
   double step    = MarketInfo(Symbol(), MODE_LOTSTEP);
   double minLot  = MarketInfo(Symbol(), MODE_MINLOT);
   double each    = MathMax(minLot, MathFloor(lots/3.0/step)*step);

   double tp1 = (type==OP_BUY) ? price + slDist*TP1_RR : price - slDist*TP1_RR;
   double tp2 = (type==OP_BUY) ? price + slDist*TP2_RR : price - slDist*TP2_RR;
   color  clr = (type==OP_BUY) ? clrGreen : clrRed;

   ticket1 = OrderSend(Symbol(), type, each, price, 5, sl, tp1, "APEX_"+tag+"_T1", MagicNumber, 0, clr);
   ticket2 = OrderSend(Symbol(), type, each, price, 5, sl, tp2, "APEX_"+tag+"_T2", MagicNumber, 0, clr);
   ticket3 = OrderSend(Symbol(), type, each, price, 5, sl, 0,   "APEX_"+tag+"_T3", MagicNumber, 0, clr);
   tp1Done = false;

   if ((ticket1>0||ticket2>0||ticket3>0) && ShowLabels)
      Label("Entry_"+tag+TimeToStr(Time[0]), Time[0],
         (type==OP_BUY?Low[0]-50*_Point*10:High[0]+50*_Point*10),
         StringFormat("%s SL:%.5f TP1:%.5f", (type==OP_BUY?"BUY":"SELL"), sl, tp1), clr);

   // Clean up zone boxes after entry
   ObjectDelete("APEX_FVG_BOX_"+tag); ObjectDelete("APEX_OB_BOX_"+tag);
   ObjectDelete("APEX_OTE_BOX_"+tag);
}

//============================================================
//  TRADE MANAGEMENT
//============================================================
void ManageTrades() {
   double atr = iATR(NULL, 0, ATR_Period, 1);

   if (ticket3 > 0 && OrderSelect(ticket3, SELECT_BY_TICKET)) {
      if (OrderCloseTime() > 0) { ticket3 = -1; }
      else {
         int    type   = OrderType();
         double openPx = OrderOpenPrice();
         double slNow  = OrderStopLoss();
         double newSL  = slNow;

         if (type == OP_BUY) {
            if (!tp1Done && Bid > openPx + atr*TP1_RR) { newSL = openPx + 3*Point*10; tp1Done=true; }
            if (tp1Done) { double c = Bid - atr*Trail_ATR; if (c > newSL) newSL = c; }
         }
         if (type == OP_SELL) {
            if (!tp1Done && Ask < openPx - atr*TP1_RR) { newSL = openPx - 3*Point*10; tp1Done=true; }
            if (tp1Done) { double c = Ask + atr*Trail_ATR; if (c < newSL) newSL = c; }
         }
         if (newSL != slNow && newSL > 0)
            OrderModify(ticket3, openPx, NormalizeDouble(newSL,Digits), OrderTakeProfit(), 0);
      }
   } else if (ticket3 > 0) ticket3 = -1;

   if (ticket1>0 && OrderSelect(ticket1,SELECT_BY_TICKET) && OrderCloseTime()>0) ticket1=-1;
   if (ticket2>0 && OrderSelect(ticket2,SELECT_BY_TICKET) && OrderCloseTime()>0) ticket2=-1;
}

//============================================================
//  STRUCTURAL SL: beyond the swing that started the impulse
//============================================================
double CalcStructuralSL(int dir, double impSt) {
   double atr = iATR(NULL, 0, ATR_Period, 1);
   double buf = SL_Buffer_Pips * Point * 10;

   if (UseStructuralSL && impSt > 0) {
      double sl = (dir == 1) ? impSt - buf : impSt + buf;
      double dist = (dir==1) ? Ask-sl : sl-Bid;
      if (dist > 0) return sl;
   }
   // Fallback: ATR-based
   return (dir==1) ? Ask - atr*ATR_SL_Mult : Bid + atr*ATR_SL_Mult;
}

//============================================================
//  FIND FVG
//============================================================
bool FindFVG(int dir, double &hi, double &lo) {
   // High quality first (no wick overlap)
   for (int i = 1; i < FVG_Lookback-1; i++) {
      if (dir==1 && High[i+1]<Low[i-1] && Low[i]>High[i+1] && High[i]<Low[i-1]) {
         lo=High[i+1]; hi=Low[i-1]; if(hi>lo) return true;
      }
      if (dir==-1 && Low[i+1]>High[i-1] && High[i]<Low[i+1] && Low[i]>High[i-1]) {
         lo=High[i-1]; hi=Low[i+1]; if(hi>lo) return true;
      }
   }
   // Standard quality fallback
   for (int i = 1; i < FVG_Lookback-1; i++) {
      if (dir==1 && High[i+1]<Low[i-1])  { lo=High[i+1]; hi=Low[i-1]; if(hi>lo) return true; }
      if (dir==-1 && Low[i+1]>High[i-1]) { lo=High[i-1]; hi=Low[i+1]; if(hi>lo) return true; }
   }
   return false;
}

//============================================================
//  FIND ORDER BLOCK
//============================================================
bool FindOB(int dir, double &hi, double &lo) {
   for (int i = 1; i < OB_Lookback; i++) {
      if (dir==1 && Close[i]<Open[i] && i>0 && Close[i-1]>High[i]) {
         hi=High[i]; lo=Low[i]; return true;
      }
      if (dir==-1 && Close[i]>Open[i] && i>0 && Close[i-1]<Low[i]) {
         hi=High[i]; lo=Low[i]; return true;
      }
   }
   return false;
}

//============================================================
//  OTE FIBONACCI ZONE
//============================================================
void CalcOTEZone(double start, double end, int dir, double &oteH, double &oteL) {
   double range = MathAbs(end - start);
   if (range == 0) return;
   if (dir==1)  { oteH = end - range*OTE_Min; oteL = end - range*OTE_Max; }
   else         { oteL = end + range*OTE_Min;  oteH = end + range*OTE_Max; }
}

//============================================================
//  H4 BIAS
//============================================================
int GetH4Bias() {
   double ema = iMA(NULL, PERIOD_H4, 50, 0, MODE_EMA, PRICE_CLOSE, 1);
   double cls = iClose(NULL, PERIOD_H4, 1);
   return (ema==0) ? 0 : (cls>ema) ? 1 : (cls<ema) ? -1 : 0;
}

//============================================================
//  SESSION CHECK
//============================================================
bool IsInSession() {
   int h = TimeHour(TimeCurrent() - GMT_Offset * 3600);
   if (!Trade_London) return (h >= Session_Start && h < Session_End);
   return (h >= London_Start && h < London_End) || (h >= NY_Start && h < NY_End);
}

//============================================================
//  SWING DETECTION
//============================================================
bool IsSwingHigh(int i) {
   if (i<=SwingStrength || i+SwingStrength>=Bars) return false;
   for (int j=1;j<=SwingStrength;j++) if (High[i-j]>=High[i]||High[i+j]>=High[i]) return false;
   return true;
}
bool IsSwingLow(int i) {
   if (i<=SwingStrength || i+SwingStrength>=Bars) return false;
   for (int j=1;j<=SwingStrength;j++) if (Low[i-j]<=Low[i]||Low[i+j]<=Low[i]) return false;
   return true;
}
double GetSwingHigh(int n) {
   int c=0; for(int i=SwingStrength+1;i<400;i++) if(IsSwingHigh(i)){c++;if(c==n)return High[i];} return 0;
}
double GetSwingLow(int n) {
   int c=0; for(int i=SwingStrength+1;i<400;i++) if(IsSwingLow(i)){c++;if(c==n)return Low[i];} return 0;
}

//============================================================
//  POSITION SIZING
//============================================================
double CalcLots(double slDist) {
   if (slDist<=0) return MarketInfo(Symbol(),MODE_MINLOT);
   double risk  = AccountBalance() * RiskPercent / 100.0;
   double ticks = slDist / MarketInfo(Symbol(),MODE_TICKSIZE);
   double lots  = risk / (ticks * MarketInfo(Symbol(),MODE_TICKVALUE));
   double step  = MarketInfo(Symbol(),MODE_LOTSTEP);
   lots = MathFloor(lots/step)*step;
   return MathMax(MarketInfo(Symbol(),MODE_MINLOT), MathMin(MarketInfo(Symbol(),MODE_MAXLOT),lots));
}

int CountOrders() {
   int n=0;
   for(int i=OrdersTotal()-1;i>=0;i--)
      if(OrderSelect(i,SELECT_BY_POS,MODE_TRADES) &&
         OrderMagicNumber()==MagicNumber && OrderSymbol()==Symbol()) n++;
   return n;
}

//============================================================
//  NEWS FILTER
//============================================================
void FetchNews() {
   newsCount=0; lastNewsFetch=TimeCurrent();
   char req[],res[]; string hdrs; ArrayResize(req,0);
   int code = WebRequest("GET",News_URL,"",5000,req,res,hdrs);
   if (code!=200) { Print("APEX News: WebRequest failed (code=",code,"). Add URL to allowed list."); return; }
   string json=CharArrayToString(res); int pos=0;
   while(newsCount<99) {
      int ip=StringFind(json,"\"impact\":\"High\"",pos);
      if(ip<0) break;
      int os=ip; while(os>0&&StringSubstr(json,os,1)!="{") os--;
      string obj=StringSubstr(json,os,ip-os+30);
      if(StringFind(obj,"\"country\":\"USD\"")>=0 || StringFind(obj,"\"country\":\"EUR\"")>=0) {
         int dp=StringFind(json,"\"date\":\"",os);
         if(dp>0&&dp<ip+200) {
            datetime t=ParseNewsDate(StringSubstr(json,dp+8,19));
            if(t>TimeCurrent()-3600) { newsEventTimes[newsCount]=t; newsCount++; }
         }
      }
      pos=ip+15;
   }
   Print("APEX News: ",newsCount," upcoming high-impact events loaded.");
}

datetime ParseNewsDate(string s) {
   if(StringLen(s)<19) return 0;
   string f=StringSubstr(s,0,4)+"."+StringSubstr(s,5,2)+"."+StringSubstr(s,8,2)+" "+StringSubstr(s,11,2)+":"+StringSubstr(s,14,2);
   datetime utc=StringToTime(f);
   utc-=News_TZ_Offset*3600;
   utc+=GMT_Offset*3600;
   return utc;
}

bool IsNewsBlackout() {
   if(!UseNewsFilter||newsCount==0) return false;
   datetime now=TimeCurrent();
   for(int i=0;i<newsCount;i++)
      if(now>=newsEventTimes[i]-News_MinsBefore*60 && now<=newsEventTimes[i]+News_MinsAfter*60) {
         if(ShowLabels) Label("NewsBlock",Time[0],Low[0]-60*_Point*10,"NEWS BLOCK",clrYellow);
         return true;
      }
   return false;
}

//============================================================
//  VISUAL HELPERS
//============================================================
void DrawSetupBoxes(string tag, int dir,
                    bool fvgOK, double fHi, double fLo,
                    bool obOK,  double oHi, double oLo,
                    double oteH, double oteL) {
   if(!ShowZoneBoxes) return;
   datetime t2 = Time[0] + BoxProjectBars * PeriodSeconds();
   if(fvgOK) DrawBox("APEX_FVG_BOX_"+tag, Time[FVG_Lookback], fLo, t2, fHi,
                     (dir==1?FVG_Bull_Color:FVG_Bear_Color));
   if(obOK)  DrawBox("APEX_OB_BOX_"+tag,  Time[OB_Lookback],  oLo, t2, oHi,
                     (dir==1?OB_Bull_Color:OB_Bear_Color));
   if(UseOTE && oteH>0 && oteL>0)
              DrawBox("APEX_OTE_BOX_"+tag, Time[0], oteL, t2, oteH, OTE_Color);
}

void DrawBox(string name, datetime t1, double p1, datetime t2, double p2, color clr) {
   if(ObjectFind(name)>=0) ObjectDelete(name);
   ObjectCreate(name,OBJ_RECTANGLE,0,t1,p1,t2,p2);
   ObjectSet(name,OBJPROP_COLOR,clr);
   ObjectSet(name,OBJPROP_BACK,true);
   ObjectSet(name,OBJPROP_FILL,true);
   ObjectSet(name,OBJPROP_WIDTH,1);
}

void DrawHLine(string name, double price, color clr, int style) {
   if(!ShowLabels) return;
   if(ObjectFind(name)>=0) ObjectDelete(name);
   ObjectCreate(name,OBJ_HLINE,0,0,price);
   ObjectSet(name,OBJPROP_COLOR,clr);
   ObjectSet(name,OBJPROP_STYLE,style);
   ObjectSet(name,OBJPROP_WIDTH,1);
}

void Label(string name, datetime t, double price, string txt, color clr) {
   string n="APEX_"+name;
   if(ObjectFind(n)>=0) ObjectDelete(n);
   ObjectCreate(n,OBJ_TEXT,0,t,price);
   ObjectSetString(0,n,OBJPROP_TEXT,txt);
   ObjectSet(n,OBJPROP_COLOR,clr);
   ObjectSet(n,OBJPROP_FONTSIZE,8);
}

//============================================================
//  RESETS
//============================================================
void ResetBOS() {
   bosSetupActive=false; bosBias=0; bosLevel=bosImpStart=bosImpEnd=0;
   bosFvgOK=bosObOK=false; bosOteHi=bosOteLo=bosStructSL=0;
   ObjectDelete("APEX_FVG_BOX_BOS"); ObjectDelete("APEX_OB_BOX_BOS");
   ObjectDelete("APEX_OTE_BOX_BOS"); ObjectDelete("APEX_BOS_LVL_A");
}

void ResetCHoCH() {
   chochSetupActive=false; chochBias=0; chochLevel=chochBosTarget=0;
   chochImpStart=chochImpEnd=0; chochFvgOK=chochObOK=chochBOSDone=false;
   chochOteHi=chochOteLo=chochStructSL=0;
   ObjectDelete("APEX_FVG_BOX_CHOCH"); ObjectDelete("APEX_OB_BOX_CHOCH");
   ObjectDelete("APEX_OTE_BOX_CHOCH"); ObjectDelete("APEX_CHOCH_LVL");
   ObjectDelete("APEX_BOS_LVL_B");
}
