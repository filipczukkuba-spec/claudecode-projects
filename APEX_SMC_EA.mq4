// APEX_SMC_EA.mq4 v2 — Advanced Smart Money Concepts Expert Advisor
// Full confluence: Kill Zones + H4 Bias + Liquidity Sweep + CHoCH + BOS +
//   Order Block + FVG + OTE Fibonacci + Premium/Discount
// NEW: Visual zone boxes on chart + News filter (ForexFactory calendar)
//
// SETUP REQUIRED:
//   1. Tools → Options → Expert Advisors → Allow WebRequest for listed URLs
//      Add: https://nfs.faireconomy.media
//   2. Set GMT_Offset to your broker's server time offset from GMT
//
// Pair: EURUSD | Timeframe: H1

#property strict
#property description "APEX SMC EA v2 — Visual Zones + News Filter"

//============================================================
//  SESSION
//============================================================
extern int    GMT_Offset     = 2;
extern bool   Trade_London   = true;
extern bool   Trade_NewYork  = true;
extern int    London_Start   = 7;
extern int    London_End     = 10;
extern int    NY_Start       = 12;
extern int    NY_End         = 15;

//============================================================
//  STRUCTURE
//============================================================
extern int    SwingStrength  = 5;
extern int    FVG_Lookback   = 40;
extern int    OB_Lookback    = 60;
extern int    EqPips         = 3;

//============================================================
//  OTE FIBONACCI
//============================================================
extern double OTE_Min        = 0.62;
extern double OTE_Max        = 0.79;

//============================================================
//  RISK
//============================================================
extern double RiskPercent    = 2.0;
extern bool   UseStructuralSL = true;
extern int    ATR_Period     = 14;
extern double ATR_SL_Mult    = 3.0;
extern double SL_Buffer_Pips = 8.0;
extern double TP1_RR         = 2.0;
extern double TP2_RR         = 4.0;
extern double Trail_ATR      = 2.0;

//============================================================
//  VISUALS
//============================================================
extern bool   ShowZoneBoxes  = true;  // Draw FVG/OB/OTE boxes on chart
extern bool   ShowLabels     = true;  // Draw CHoCH/BOS/entry labels
extern int    BoxProjectBars = 40;    // How many bars to extend boxes rightward
extern color  FVG_Bull_Color = C'0,100,0';     // Dark green FVG box
extern color  FVG_Bear_Color = C'100,0,0';     // Dark red FVG box
extern color  OB_Bull_Color  = C'0,60,120';    // Dark blue OB box
extern color  OB_Bear_Color  = C'120,40,0';    // Dark orange OB box
extern color  OTE_Color      = C'80,60,0';     // Dark gold OTE zone
extern int    MagicNumber    = 777888;

//============================================================
//  NEWS FILTER
//============================================================
extern bool   UseNewsFilter   = true;
extern int    News_MinsBefore = 30;  // Pause trading X minutes before high-impact news
extern int    News_MinsAfter  = 15;  // Pause trading X minutes after
extern int    News_TZ_Offset  = -5;  // ForexFactory calendar timezone (EST = -5)
extern string News_URL        = "https://nfs.faireconomy.media/ff_calendar_thisweek.json";

//============================================================
//  STATE MACHINE
//============================================================
#define STAGE_WAIT   0
#define STAGE_CHOCH  1
#define STAGE_BOS    2
#define STAGE_ENTRY  3

int    stage    = STAGE_WAIT;
int    bias     = 0;
double impStart = 0;
double impEnd   = 0;
double chochLvl = 0;
double bosLvl   = 0;

double obHi = 0, obLo = 0;
bool   obOK = false;

double fvgHi = 0, fvgLo = 0;
bool   fvgOK = false;

double oteHi = 0, oteLo = 0;
double structSL = 0;

int    ticket1 = -1, ticket2 = -1, ticket3 = -1;
bool   tp1Done = false, tp2Done = false;

bool   sweepBull = false, sweepBear = false;
double sweepLvl  = 0;

//============================================================
//  NEWS CACHE
//============================================================
datetime newsEventTimes[100];
int      newsCount     = 0;
datetime lastNewsFetch = 0;

//============================================================
int OnInit() {
   ResetState();
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
   if (AccountFreeMargin() < 100) return;

   // Refresh news calendar every hour
   if (UseNewsFilter && TimeCurrent() - lastNewsFetch > 3600)
      FetchNews();

   ManageTrades();

   if (CountOrders() > 0) return;

   if (ticket1 == -1 && ticket2 == -1 && ticket3 == -1) {
      tp1Done = false;
      tp2Done = false;
   }

   switch (stage) {
      case STAGE_WAIT:  CheckForCHoCH(); break;
      case STAGE_CHOCH: CheckForBOS();   break;
      case STAGE_BOS:   CheckForBOS();   break;
      case STAGE_ENTRY: CheckForEntry(); break;
   }
}

//============================================================
//  CHoCH — Change of Character
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

   if (priorBear && c > sh1 && h4bias == 1) {
      if (!IsInDiscountZone(sl2, sh2)) return;
      DetectLiquiditySweep();
      bias = 1; chochLvl = sh1; impStart = sl1; impEnd = sh1; bosLvl = sh2;
      stage = STAGE_CHOCH;
      if (ShowLabels) {
         DrawHLine("APEX_CHOCH_LVL", chochLvl, clrDodgerBlue, STYLE_DASH);
         Label("CHoCH_B_"+TimeToStr(Time[1]), Time[1], Low[1]-30*_Point*10, "CHoCH↑", clrDodgerBlue);
      }
   }

   if (priorBull && c < sl1 && h4bias == -1) {
      if (!IsInPremiumZone(sl2, sh2)) return;
      DetectLiquiditySweep();
      bias = -1; chochLvl = sl1; impStart = sh1; impEnd = sl1; bosLvl = sl2;
      stage = STAGE_CHOCH;
      if (ShowLabels) {
         DrawHLine("APEX_CHOCH_LVL", chochLvl, clrOrangeRed, STYLE_DASH);
         Label("CHoCH_S_"+TimeToStr(Time[1]), Time[1], High[1]+30*_Point*10, "CHoCH↓", clrOrangeRed);
      }
   }
}

//============================================================
//  BOS — Break of Structure
//============================================================
void CheckForBOS() {
   double c   = Close[1];
   double atr = iATR(NULL, 0, ATR_Period, 1);

   if (bias ==  1 && c < impStart - atr * 1.5) { ResetState(); return; }
   if (bias == -1 && c > impStart + atr * 1.5) { ResetState(); return; }

   bool bosOk = (bias == 1 && c > bosLvl) || (bias == -1 && c < bosLvl);
   if (!bosOk) return;

   obOK  = FindOrderBlock();
   fvgOK = FindFVG();
   CalcOTE();

   if (!fvgOK && !obOK) { ResetState(); return; }

   // Draw all zones now that BOS is confirmed
   if (ShowZoneBoxes) {
      datetime t2 = Time[0] + BoxProjectBars * PeriodSeconds();
      if (fvgOK) DrawBox("APEX_FVG_BOX", Time[FVG_Lookback], fvgLo, t2, fvgHi,
                         (bias==1 ? FVG_Bull_Color : FVG_Bear_Color));
      if (obOK)  DrawBox("APEX_OB_BOX",  Time[OB_Lookback],  obLo,  t2, obHi,
                         (bias==1 ? OB_Bull_Color : OB_Bear_Color));
      if (oteHi > 0 && oteLo > 0)
                 DrawBox("APEX_OTE_BOX", Time[0], oteLo, t2, oteHi, OTE_Color);
   }

   stage = STAGE_ENTRY;

   if (ShowLabels) {
      DrawHLine("APEX_BOS_LVL", bosLvl, (bias==1 ? clrLime : clrRed), STYLE_SOLID);
      Label("BOS_"+TimeToStr(Time[1]), Time[1],
         (bias==1 ? Low[1]-40*_Point*10 : High[1]+40*_Point*10),
         "BOS"+(bias==1?"↑":"↓"), (bias==1 ? clrLime : clrRed));
   }
}

//============================================================
//  ENTRY — All confluences must overlap
//============================================================
void CheckForEntry() {
   if (!IsInKillZone())  return;
   if (CountOrders() > 0) return;
   if (IsNewsBlackout()) return;   // News filter

   double atr = iATR(NULL, 0, ATR_Period, 1);
   CalcOTE();

   // Determine entry zone: intersection of OTE + FVG + OB
   double eHi, eLo;

   if (bias == 1) {
      eHi = fvgOK ? fvgHi : oteHi;
      eLo = fvgOK ? fvgLo : oteLo;
      if (obOK) { eHi = MathMin(eHi, obHi); eLo = MathMax(eLo, obLo); }
      if (oteHi > 0) { eHi = MathMin(eHi, oteHi); eLo = MathMax(eLo, oteLo); }
      if (eHi <= eLo) { eHi = fvgOK ? fvgHi : oteHi; eLo = fvgOK ? fvgLo : oteLo; }

      if (Ask >= eLo && Ask <= eHi) {
         double swLow = GetSwingLow(1);
         structSL = (UseStructuralSL && swLow > 0)
                    ? swLow - SL_Buffer_Pips * Point * 10
                    : Ask - atr * ATR_SL_Mult;
         double slDist = Ask - structSL;
         if (slDist < atr * 0.5) { structSL = Ask - atr * ATR_SL_Mult; slDist = Ask - structSL; }

         PlaceOrders(OP_BUY, Ask, structSL, Ask + slDist*TP1_RR, Ask + slDist*TP2_RR, slDist);
      }
   }

   if (bias == -1) {
      eHi = fvgOK ? fvgHi : oteHi;
      eLo = fvgOK ? fvgLo : oteLo;
      if (obOK) { eHi = MathMin(eHi, obHi); eLo = MathMax(eLo, obLo); }
      if (oteHi > 0) { eHi = MathMin(eHi, oteHi); eLo = MathMax(eLo, oteLo); }
      if (eHi <= eLo) { eHi = fvgOK ? fvgHi : oteHi; eLo = fvgOK ? fvgLo : oteLo; }

      if (Bid >= eLo && Bid <= eHi) {
         double swHigh = GetSwingHigh(1);
         structSL = (UseStructuralSL && swHigh > 0)
                    ? swHigh + SL_Buffer_Pips * Point * 10
                    : Bid + atr * ATR_SL_Mult;
         double slDist = structSL - Bid;
         if (slDist < atr * 0.5) { structSL = Bid + atr * ATR_SL_Mult; slDist = structSL - Bid; }

         PlaceOrders(OP_SELL, Bid, structSL, Bid - slDist*TP1_RR, Bid - slDist*TP2_RR, slDist);
      }
   }

   // Invalidate if price moved far past all zones
   double fade = atr * 3;
   if (bias ==  1 && Bid > impEnd + fade) ResetState();
   if (bias == -1 && Ask < impEnd - fade) ResetState();
}

//============================================================
//  Place 3 split orders (1/3 each at TP1, TP2, trailing)
//============================================================
void PlaceOrders(int type, double price, double sl, double tp1, double tp2, double slDist) {
   double lots    = CalcLots(slDist);
   if (lots <= 0) return;
   double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
   double minLot  = MarketInfo(Symbol(), MODE_MINLOT);
   double each    = MathMax(minLot, MathFloor(lots/3.0/lotStep)*lotStep);

   color  clr = (type == OP_BUY) ? clrGreen : clrRed;
   ticket1 = OrderSend(Symbol(), type, each, price, 5, sl, tp1, "APEX_TP1", MagicNumber, 0, clr);
   ticket2 = OrderSend(Symbol(), type, each, price, 5, sl, tp2, "APEX_TP2", MagicNumber, 0, clr);
   ticket3 = OrderSend(Symbol(), type, each, price, 5, sl, 0,   "APEX_TP3", MagicNumber, 0, clr);

   if (ticket1 > 0 || ticket2 > 0 || ticket3 > 0) {
      if (ShowLabels) {
         string dir = (type == OP_BUY) ? "BUY" : "SELL";
         Label("Entry_"+TimeToStr(Time[0]), Time[0],
            (type==OP_BUY ? Low[0]-50*_Point*10 : High[0]+50*_Point*10),
            StringFormat("%s  SL:%.5f  TP1:%.5f  TP2:%.5f", dir, sl, tp1, tp2), clr);
      }
      // Delete zone boxes — trade is on
      ObjectDelete("APEX_FVG_BOX");
      ObjectDelete("APEX_OB_BOX");
      ObjectDelete("APEX_OTE_BOX");
      ResetState();
   }
}

//============================================================
//  Trade management — breakeven + trailing for ticket3
//============================================================
void ManageTrades() {
   double atr = iATR(NULL, 0, ATR_Period, 1);

   if (ticket3 > 0 && OrderSelect(ticket3, SELECT_BY_TICKET)) {
      if (OrderCloseTime() > 0) { ticket3 = -1; return; }
      int    type   = OrderType();
      double openPx = OrderOpenPrice();
      double slNow  = OrderStopLoss();
      double newSL  = slNow;

      if (type == OP_BUY) {
         if (!tp1Done && Bid > openPx + atr * TP1_RR) {
            newSL = openPx + 5 * Point * 10; tp1Done = true;
         }
         if (tp1Done) {
            double cand = Bid - atr * Trail_ATR;
            if (cand > newSL) newSL = cand;
         }
      }
      if (type == OP_SELL) {
         if (!tp1Done && Ask < openPx - atr * TP1_RR) {
            newSL = openPx - 5 * Point * 10; tp1Done = true;
         }
         if (tp1Done) {
            double cand = Ask + atr * Trail_ATR;
            if (cand < newSL) newSL = cand;
         }
      }
      if (newSL != slNow && newSL > 0)
         OrderModify(ticket3, openPx, NormalizeDouble(newSL, Digits), OrderTakeProfit(), 0);
   } else if (ticket3 > 0) ticket3 = -1;

   if (ticket1 > 0 && OrderSelect(ticket1, SELECT_BY_TICKET) && OrderCloseTime() > 0) ticket1 = -1;
   if (ticket2 > 0 && OrderSelect(ticket2, SELECT_BY_TICKET) && OrderCloseTime() > 0) ticket2 = -1;
}

//============================================================
//  NEWS FILTER
//  Fetches ForexFactory calendar JSON, caches USD+EUR high-impact
//  event times. Blocks entry within News_MinsBefore/MinsAfter.
//  Requires: Tools → Options → Expert Advisors → Allow WebRequest
//            URL: https://nfs.faireconomy.media
//============================================================
void FetchNews() {
   newsCount    = 0;
   lastNewsFetch = TimeCurrent();

   char   req[], res[];
   string resHeaders;
   ArrayResize(req, 0);

   int code = WebRequest("GET", News_URL, "", 5000, req, res, resHeaders);
   if (code != 200) {
      Print("APEX News: WebRequest failed (code=", code,
            "). Check Tools→Options→Expert Advisors→Allow WebRequest URL.");
      return;
   }

   string json = CharArrayToString(res);
   int    pos  = 0;

   while (newsCount < 99) {
      // Find next high-impact USD or EUR event
      int impPos = StringFind(json, "\"impact\":\"High\"", pos);
      if (impPos < 0) break;

      // Look back in the same object for country
      int objStart = impPos;
      while (objStart > 0 && StringSubstr(json, objStart, 1) != "{") objStart--;

      string obj = StringSubstr(json, objStart, impPos - objStart + 30);
      bool isUSD = StringFind(obj, "\"country\":\"USD\"") >= 0;
      bool isEUR = StringFind(obj, "\"country\":\"EUR\"") >= 0;

      if (isUSD || isEUR) {
         // Extract date field from the object
         int datePos = StringFind(json, "\"date\":\"", objStart);
         if (datePos > 0 && datePos < impPos + 200) {
            int dateStart = datePos + 8;
            string dateStr = StringSubstr(json, dateStart, 19); // "YYYY-MM-DDTHH:MM:SS"
            datetime t = ParseNewsDate(dateStr);
            if (t > TimeCurrent() - 3600) {
               newsEventTimes[newsCount] = t;
               newsCount++;
            }
         }
      }
      pos = impPos + 15;
   }
   Print("APEX News: Loaded ", newsCount, " upcoming USD/EUR high-impact events.");
}

// Parse "YYYY-MM-DDTHH:MM:SS" → datetime (server time)
datetime ParseNewsDate(string s) {
   if (StringLen(s) < 19) return 0;
   string formatted = StringSubstr(s,0,4) + "." +
                      StringSubstr(s,5,2) + "." +
                      StringSubstr(s,8,2) + " " +
                      StringSubstr(s,11,2) + ":" +
                      StringSubstr(s,14,2);
   datetime utc = StringToTime(formatted);
   // Convert from FF calendar timezone to GMT, then add broker GMT offset
   utc -= News_TZ_Offset * 3600;   // to GMT
   utc += GMT_Offset     * 3600;   // to server time
   return utc;
}

bool IsNewsBlackout() {
   if (!UseNewsFilter || newsCount == 0) return false;
   datetime now    = TimeCurrent();
   int      before = News_MinsBefore * 60;
   int      after  = News_MinsAfter  * 60;
   for (int i = 0; i < newsCount; i++) {
      datetime t = newsEventTimes[i];
      if (now >= t - before && now <= t + after) {
         if (ShowLabels)
            Label("NewsBlock", Time[0], Low[0]-60*_Point*10, "NEWS BLOCK", clrYellow);
         return true;
      }
   }
   return false;
}

//============================================================
//  ORDER BLOCK
//============================================================
bool FindOrderBlock() {
   for (int i = 1; i < OB_Lookback; i++) {
      if (bias == 1 && Close[i] < Open[i] && Close[i-1] > High[i]) {
         obHi = High[i]; obLo = Low[i]; return true;
      }
      if (bias == -1 && Close[i] > Open[i] && Close[i-1] < Low[i]) {
         obHi = High[i]; obLo = Low[i]; return true;
      }
   }
   return false;
}

//============================================================
//  FAIR VALUE GAP
//============================================================
bool FindFVG() {
   // High quality: no wick overlap
   for (int i = 1; i < FVG_Lookback - 1; i++) {
      if (bias == 1 && High[i+1] < Low[i-1] && Low[i] > High[i+1] && High[i] < Low[i-1]) {
         fvgLo = High[i+1]; fvgHi = Low[i-1];
         if (fvgHi > fvgLo) return true;
      }
      if (bias == -1 && Low[i+1] > High[i-1] && High[i] < Low[i+1] && Low[i] > High[i-1]) {
         fvgLo = High[i-1]; fvgHi = Low[i+1];
         if (fvgHi > fvgLo) return true;
      }
   }
   // Standard quality fallback
   for (int i = 1; i < FVG_Lookback - 1; i++) {
      if (bias == 1 && High[i+1] < Low[i-1]) {
         fvgLo = High[i+1]; fvgHi = Low[i-1];
         if (fvgHi > fvgLo) return true;
      }
      if (bias == -1 && Low[i+1] > High[i-1]) {
         fvgLo = High[i-1]; fvgHi = Low[i+1];
         if (fvgHi > fvgLo) return true;
      }
   }
   return false;
}

//============================================================
//  OTE FIBONACCI (62%-79% retracement)
//============================================================
void CalcOTE() {
   if (impStart == 0 || impEnd == 0) return;
   double range = MathAbs(impEnd - impStart);
   if (range == 0) return;
   if (bias == 1) { oteHi = impEnd - range*OTE_Min; oteLo = impEnd - range*OTE_Max; }
   else           { oteLo = impEnd + range*OTE_Min; oteHi = impEnd + range*OTE_Max; }
}

//============================================================
//  LIQUIDITY SWEEP
//============================================================
void DetectLiquiditySweep() {
   double tol = EqPips * Point * 10;
   sweepBull = sweepBear = false;
   for (int i = 3; i < 50 && !sweepBull && !sweepBear; i++) {
      for (int j = i+1; j < 50; j++) {
         if (MathAbs(Low[i] - Low[j]) < tol) {
            double lvl = (Low[i]+Low[j])/2.0;
            for (int k = 1; k < i; k++) {
               if (Low[k] < lvl - tol && Close[1] > lvl) {
                  sweepBull = true; sweepLvl = lvl;
                  if (ShowLabels) Label("Sweep_B_"+TimeToStr(Time[i]), Time[i], Low[i]-20*_Point*10, "Sweep↑", clrAqua);
                  break;
               }
            }
            if (sweepBull) break;
         }
         if (MathAbs(High[i] - High[j]) < tol) {
            double lvl = (High[i]+High[j])/2.0;
            for (int k = 1; k < i; k++) {
               if (High[k] > lvl + tol && Close[1] < lvl) {
                  sweepBear = true; sweepLvl = lvl;
                  if (ShowLabels) Label("Sweep_S_"+TimeToStr(Time[i]), Time[i], High[i]+20*_Point*10, "Sweep↓", clrMagenta);
                  break;
               }
            }
            if (sweepBear) break;
         }
      }
   }
}

//============================================================
//  H4 BIAS
//============================================================
int GetH4Bias() {
   double ema = iMA(NULL, PERIOD_H4, 50, 0, MODE_EMA, PRICE_CLOSE, 1);
   double cls = iClose(NULL, PERIOD_H4, 1);
   if (ema == 0) return 0;
   return (cls > ema) ? 1 : (cls < ema) ? -1 : 0;
}

//============================================================
//  KILL ZONE
//============================================================
bool IsInKillZone() {
   int h = TimeHour(TimeCurrent() - GMT_Offset * 3600);
   if (Trade_London  && h >= London_Start && h < London_End) return true;
   if (Trade_NewYork && h >= NY_Start     && h < NY_End)     return true;
   return false;
}

//============================================================
//  PREMIUM / DISCOUNT
//============================================================
bool IsInDiscountZone(double lo, double hi) {
   return (hi <= lo) ? true : Ask < (hi+lo)/2.0;
}
bool IsInPremiumZone(double lo, double hi) {
   return (hi <= lo) ? true : Bid > (hi+lo)/2.0;
}

//============================================================
//  SWING DETECTION
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
   int c = 0;
   for (int i = SwingStrength+1; i < 400; i++)
      if (IsSwingHigh(i)) { c++; if (c==n) return High[i]; }
   return 0;
}
double GetSwingLow(int n) {
   int c = 0;
   for (int i = SwingStrength+1; i < 400; i++)
      if (IsSwingLow(i))  { c++; if (c==n) return Low[i];  }
   return 0;
}

//============================================================
//  POSITION SIZING
//============================================================
double CalcLots(double slDist) {
   if (slDist <= 0) return MarketInfo(Symbol(), MODE_MINLOT);
   double risk  = AccountBalance() * RiskPercent / 100.0;
   double ticks = slDist / MarketInfo(Symbol(), MODE_TICKSIZE);
   double lots  = risk / (ticks * MarketInfo(Symbol(), MODE_TICKVALUE));
   double step  = MarketInfo(Symbol(), MODE_LOTSTEP);
   lots = MathFloor(lots/step)*step;
   return MathMax(MarketInfo(Symbol(), MODE_MINLOT),
          MathMin(MarketInfo(Symbol(), MODE_MAXLOT), lots));
}

int CountOrders() {
   int n = 0;
   for (int i = OrdersTotal()-1; i >= 0; i--)
      if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES) &&
          OrderMagicNumber() == MagicNumber && OrderSymbol() == Symbol()) n++;
   return n;
}

//============================================================
//  VISUAL HELPERS
//============================================================

// Semi-transparent filled rectangle
void DrawBox(string name, datetime t1, double p1, datetime t2, double p2, color clr) {
   if (!ShowZoneBoxes) return;
   if (ObjectFind(name) >= 0) ObjectDelete(name);
   ObjectCreate(name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSet(name, OBJPROP_COLOR,     clr);
   ObjectSet(name, OBJPROP_BACK,      true);   // draw behind candles
   ObjectSet(name, OBJPROP_WIDTH,     1);
   ObjectSet(name, OBJPROP_STYLE,     STYLE_SOLID);
   ObjectSet(name, OBJPROP_FILL,      true);
}

// Horizontal dashed line at price level
void DrawHLine(string name, double price, color clr, int style) {
   if (!ShowLabels) return;
   if (ObjectFind(name) >= 0) ObjectDelete(name);
   ObjectCreate(name, OBJ_HLINE, 0, 0, price);
   ObjectSet(name, OBJPROP_COLOR, clr);
   ObjectSet(name, OBJPROP_STYLE, style);
   ObjectSet(name, OBJPROP_WIDTH, 1);
}

// Text label at position
void Label(string name, datetime t, double price, string txt, color clr) {
   string n = "APEX_" + name;
   if (ObjectFind(n) >= 0) ObjectDelete(n);
   ObjectCreate(n, OBJ_TEXT, 0, t, price);
   ObjectSetString(0, n, OBJPROP_TEXT, txt);
   ObjectSet(n, OBJPROP_COLOR,    clr);
   ObjectSet(n, OBJPROP_FONTSIZE, 8);
}

//============================================================
//  RESET
//============================================================
void ResetState() {
   stage = STAGE_WAIT; bias = 0;
   impStart = impEnd = chochLvl = bosLvl = 0;
   obOK = fvgOK = false;
   oteHi = oteLo = structSL = 0;
   // Remove zone boxes when setup is invalidated
   ObjectDelete("APEX_FVG_BOX");
   ObjectDelete("APEX_OB_BOX");
   ObjectDelete("APEX_OTE_BOX");
   ObjectDelete("APEX_CHOCH_LVL");
   ObjectDelete("APEX_BOS_LVL");
}
