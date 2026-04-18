// APEX_SMC_EA.mq4 v4 — Balanced Edition
// Target: 10-20 trades/month | High accuracy | H1 timeframe
//
// TWO SETUPS run in parallel:
//   A) BOS CONTINUATION — requires displacement candle (real breakout, not noise)
//   B) CHoCH REVERSAL   — requires liquidity sweep first (institutional reversal)
//
// REQUIRED FOR BOTH:
//   - London or NY kill zone
//   - H4 EMA50 bias agrees
//   - ADX > 20 AND rising (trending, not ranging)
//   - HIGH QUALITY FVG (strict: zero wick overlap between candle 1 and 3)
//
// CONTINUATION also requires:
//   - Displacement candle on BOS (body > 1.5x average = real breakout)
//
// REVERSAL also requires:
//   - Liquidity sweep before CHoCH (equal highs/lows taken first)
//
// Exit: Structural SL | TP1 2:1 (40%) | TP2 4:1 (35%) | TP3 trailing (25%)
// Pair: EURUSD | Timeframe: H1
//
// SETUP: Tools → Options → Expert Advisors → Allow WebRequest
//        Add URL: https://nfs.faireconomy.media

#property strict
#property description "APEX SMC EA v4 — Balanced Edition"

//============================================================
//  SESSION
//============================================================
extern int    GMT_Offset      = 2;
extern int    London_Start    = 7;
extern int    London_End      = 11;
extern int    NY_Start        = 12;
extern int    NY_End          = 17;

//============================================================
//  STRUCTURE
//============================================================
extern int    SwingStrength   = 4;    // Between v2(5) and v3(3) — balanced
extern int    FVG_Lookback    = 25;
extern int    OB_Lookback     = 40;
extern int    MaxBarsInSetup  = 30;   // Reset if no entry within 30 H1 bars (~30hrs)
extern int    EqPips          = 4;    // Equal high/low tolerance for sweep detection

//============================================================
//  QUALITY FILTERS
//============================================================
extern int    ADX_Period      = 14;
extern double ADX_Min         = 20.0; // Min ADX — filters ranging markets
extern bool   RequireADXRising = true; // ADX must be rising (momentum building)
extern double DisplaceMulti   = 1.5;  // BOS candle body must be > avg * this
extern int    DisplaceAvgBars = 10;   // Average over last N bars for displacement check
extern bool   RequireSweep    = true; // CHoCH reversal requires liquidity sweep first

//============================================================
//  RISK
//============================================================
extern double RiskPercent     = 2.0;
extern bool   UseStructuralSL = true;
extern int    ATR_Period      = 14;
extern double ATR_SL_Mult     = 2.5;
extern double SL_Buffer_Pips  = 6.0;
extern double TP1_RR          = 2.0;   // Close 40% here
extern double TP2_RR          = 4.0;   // Close 35% here
extern double Trail_ATR       = 1.5;   // Trail last 25%
extern int    MaxOpenTrades   = 1;

//============================================================
//  VISUALS
//============================================================
extern bool   ShowZoneBoxes   = true;
extern bool   ShowLabels      = true;
extern int    BoxProjectBars  = 35;
extern color  FVG_Bull_Color  = C'0,90,0';
extern color  FVG_Bear_Color  = C'90,0,0';
extern color  OB_Bull_Color   = C'0,50,110';
extern color  OB_Bear_Color   = C'110,35,0';
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
//  SETUP A — BOS Continuation state
//============================================================
bool   bosActive   = false;
int    bosBias     = 0;
double bosLevel    = 0;
double bosImpSt    = 0;
double bosImpEnd   = 0;
double bosFvgHi    = 0, bosFvgLo = 0;
bool   bosFvgOK    = false;
double bosObHi     = 0, bosObLo  = 0;
bool   bosObOK     = false;
int    bosBar      = 0;

//============================================================
//  SETUP B — CHoCH Reversal state
//============================================================
bool   chActive    = false;
int    chBias      = 0;
double chChochLvl  = 0;
double chBosTarget = 0;
double chImpSt     = 0;
double chImpEnd    = 0;
double chFvgHi     = 0, chFvgLo = 0;
bool   chFvgOK     = false;
double chObHi      = 0, chObLo  = 0;
bool   chObOK      = false;
bool   chBOSDone   = false;
bool   chSwept     = false;
int    chBar       = 0;

//============================================================
//  TRADE MANAGEMENT
//============================================================
int    t1 = -1, t2 = -1, t3 = -1;
bool   tp1Done = false;

//============================================================
//  NEWS CACHE
//============================================================
datetime newsTime[100];
int      newsCount     = 0;
datetime lastFetch     = 0;

//============================================================
int OnInit() {
   ResetBOS(); ResetCH();
   if (UseNewsFilter) FetchNews();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { ObjectsDeleteAll(0, "APEX_"); }

//============================================================
void OnTick() {
   static datetime lastBar = 0;
   if (Time[0] == lastBar) return;
   lastBar = Time[0];

   if (!IsTradeAllowed() || AccountFreeMargin() < 50) return;
   if (UseNewsFilter && TimeCurrent() - lastFetch > 3600) FetchNews();

   ManageTrades();

   if (CountOrders() >= MaxOpenTrades) return;
   if (t1==-1 && t2==-1 && t3==-1) tp1Done = false;

   RunContinuation();
   RunReversal();
}

//============================================================
//  GLOBAL QUALITY GATES — both setups must pass these
//============================================================
bool PassesGlobalFilters(int dir) {
   if (!IsInKillZone()) return false;
   if (GetH4Bias() != dir) return false;

   double adxNow  = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MAIN, 1);
   double adxPrev = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MAIN, 3);
   if (adxNow < ADX_Min) return false;
   if (RequireADXRising && adxNow <= adxPrev) return false;

   return true;
}

//============================================================
//  SETUP A: BOS CONTINUATION
//  Finds trending BOS with a DISPLACEMENT candle — real breakout only
//============================================================
void RunContinuation() {
   if (!bosActive) { DetectBOS(); return; }
   if (Bars - bosBar > MaxBarsInSetup) { ResetBOS(); return; }
   CheckBOSEntry();
}

void DetectBOS() {
   double sh1=GetSwingHigh(1), sh2=GetSwingHigh(2);
   double sl1=GetSwingLow(1),  sl2=GetSwingLow(2);
   if (sh1==0||sh2==0||sl1==0||sl2==0) return;

   double c = Close[1];
   bool bullTrend = sh1>sh2 && sl1>sl2;
   bool bearTrend = sh1<sh2 && sl1<sl2;

   // Bullish BOS
   if (bullTrend && c > sh1) {
      if (!PassesGlobalFilters(1)) return;
      if (!IsDisplacementCandle(1)) return;             // Real breakout check
      bool fok = FindFVGStrict(1, bosFvgHi, bosFvgLo); // Strict FVG only
      bool ook = FindOB(1, bosObHi, bosObLo);
      if (!fok && !ook) return;
      bosBias=1; bosLevel=sh1; bosImpSt=sl1; bosImpEnd=sh1;
      bosFvgOK=fok; bosObOK=ook; bosActive=true; bosBar=Bars;
      DrawZones("BOS",1,fok,bosFvgHi,bosFvgLo,ook,bosObHi,bosObLo);
      if (ShowLabels) { DrawHLine("APEX_BOS_A",sh1,clrLime,STYLE_SOLID); Label("BOSA_"+TimeToStr(Time[1]),Time[1],Low[1]-28*_Point*10,"BOS↑ [Disp]",clrLime); }
   }

   // Bearish BOS
   if (bearTrend && c < sl1) {
      if (!PassesGlobalFilters(-1)) return;
      if (!IsDisplacementCandle(1)) return;
      bool fok = FindFVGStrict(-1, bosFvgHi, bosFvgLo);
      bool ook = FindOB(-1, bosObHi, bosObLo);
      if (!fok && !ook) return;
      bosBias=-1; bosLevel=sl1; bosImpSt=sh1; bosImpEnd=sl1;
      bosFvgOK=fok; bosObOK=ook; bosActive=true; bosBar=Bars;
      DrawZones("BOS",-1,fok,bosFvgHi,bosFvgLo,ook,bosObHi,bosObLo);
      if (ShowLabels) { DrawHLine("APEX_BOS_A",sl1,clrRed,STYLE_SOLID); Label("BOSA_"+TimeToStr(Time[1]),Time[1],High[1]+28*_Point*10,"BOS↓ [Disp]",clrRed); }
   }
}

void CheckBOSEntry() {
   if (IsNewsBlackout()) return;
   double eHi,eLo;
   GetEntryZone(bosBias,bosFvgOK,bosFvgHi,bosFvgLo,bosObOK,bosObHi,bosObLo,eHi,eLo);

   if (bosBias==1 && Ask>=eLo && Ask<=eHi) {
      double sl = StructSL(1, bosImpSt);
      if (sl>0) { PlaceOrders(OP_BUY, Ask, sl, "A"); ResetBOS(); }
   }
   if (bosBias==-1 && Bid<=eHi && Bid>=eLo) {
      double sl = StructSL(-1, bosImpSt);
      if (sl>0) { PlaceOrders(OP_SELL, Bid, sl, "A"); ResetBOS(); }
   }

   double atr = iATR(NULL,0,ATR_Period,1);
   if (bosBias== 1 && Bid > bosImpEnd + atr*2) ResetBOS();
   if (bosBias==-1 && Ask < bosImpEnd - atr*2) ResetBOS();
}

//============================================================
//  SETUP B: CHoCH REVERSAL
//  Requires liquidity sweep BEFORE the CHoCH — institutional signature
//============================================================
void RunReversal() {
   if (!chActive) { DetectCHoCH(); return; }
   if (Bars - chBar > MaxBarsInSetup) { ResetCH(); return; }
   if (!chBOSDone) WaitForBOS();
   else            CheckCHEntry();
}

void DetectCHoCH() {
   double sh1=GetSwingHigh(1), sh2=GetSwingHigh(2);
   double sl1=GetSwingLow(1),  sl2=GetSwingLow(2);
   if (sh1==0||sh2==0||sl1==0||sl2==0) return;

   double adxNow = iADX(NULL,0,ADX_Period,PRICE_CLOSE,MODE_MAIN,1);
   if (adxNow < ADX_Min) return;
   if (!IsInKillZone()) return;

   double c = Close[1];
   bool priorBull = sh1>sh2 && sl1>sl2;
   bool priorBear = sh1<sh2 && sl1<sl2;

   // Bullish CHoCH: was bearish, now breaks swing high
   if (priorBear && c > sh1) {
      // H4 doesn't need to agree for reversals — it's catching the turn
      bool swept = RequireSweep ? HasLiquiditySweep(1) : true;
      if (!swept) return;
      chBias=1; chChochLvl=sh1; chBosTarget=sh2; chImpSt=sl1; chImpEnd=sh1;
      chActive=true; chBOSDone=false; chSwept=swept; chBar=Bars;
      if (ShowLabels) { DrawHLine("APEX_CHOCH",sh1,clrDodgerBlue,STYLE_DASH); Label("CHB_"+TimeToStr(Time[1]),Time[1],Low[1]-28*_Point*10,"CHoCH↑ [Sweep]",clrDodgerBlue); }
   }

   // Bearish CHoCH: was bullish, now breaks swing low
   if (priorBull && c < sl1) {
      bool swept = RequireSweep ? HasLiquiditySweep(-1) : true;
      if (!swept) return;
      chBias=-1; chChochLvl=sl1; chBosTarget=sl2; chImpSt=sh1; chImpEnd=sl1;
      chActive=true; chBOSDone=false; chSwept=swept; chBar=Bars;
      if (ShowLabels) { DrawHLine("APEX_CHOCH",sl1,clrOrangeRed,STYLE_DASH); Label("CHS_"+TimeToStr(Time[1]),Time[1],High[1]+28*_Point*10,"CHoCH↓ [Sweep]",clrOrangeRed); }
   }
}

void WaitForBOS() {
   double c=Close[1];
   double atr=iATR(NULL,0,ATR_Period,1);
   if (chBias==1  && c < chImpSt-atr)   { ResetCH(); return; }
   if (chBias==-1 && c > chImpSt+atr)   { ResetCH(); return; }
   bool bosOk=(chBias==1&&c>chBosTarget)||(chBias==-1&&c<chBosTarget);
   if (!bosOk) return;
   chFvgOK = FindFVGStrict(chBias, chFvgHi, chFvgLo);
   chObOK  = FindOB(chBias, chObHi, chObLo);
   if (!chFvgOK && !chObOK) { ResetCH(); return; }
   chBOSDone = true;
   DrawZones("CH",chBias,chFvgOK,chFvgHi,chFvgLo,chObOK,chObHi,chObLo);
   if (ShowLabels) DrawHLine("APEX_BOS_B",chBosTarget,(chBias==1?clrLime:clrRed),STYLE_SOLID);
}

void CheckCHEntry() {
   if (IsNewsBlackout()) return;
   double eHi,eLo;
   GetEntryZone(chBias,chFvgOK,chFvgHi,chFvgLo,chObOK,chObHi,chObLo,eHi,eLo);

   if (chBias==1 && Ask>=eLo && Ask<=eHi) {
      double sl=StructSL(1,chImpSt);
      if (sl>0) { PlaceOrders(OP_BUY,Ask,sl,"B"); ResetCH(); }
   }
   if (chBias==-1 && Bid<=eHi && Bid>=eLo) {
      double sl=StructSL(-1,chImpSt);
      if (sl>0) { PlaceOrders(OP_SELL,Bid,sl,"B"); ResetCH(); }
   }

   double atr=iATR(NULL,0,ATR_Period,1);
   if (chBias==1  && Bid > chImpEnd+atr*2) ResetCH();
   if (chBias==-1 && Ask < chImpEnd-atr*2) ResetCH();
}

//============================================================
//  DISPLACEMENT CANDLE — body must be significantly larger than average
//  Confirms the BOS is real institutional movement, not noise
//============================================================
bool IsDisplacementCandle(int bar) {
   double avgBody = 0;
   for (int i = 1; i <= DisplaceAvgBars; i++)
      avgBody += MathAbs(Close[bar+i] - Open[bar+i]);
   avgBody /= DisplaceAvgBars;
   double body = MathAbs(Close[bar] - Open[bar]);
   return body > avgBody * DisplaceMulti;
}

//============================================================
//  LIQUIDITY SWEEP — equal highs/lows taken out before CHoCH
//  Bullish sweep: equal lows breached then price closes back above
//  Bearish sweep: equal highs breached then price closes back below
//============================================================
bool HasLiquiditySweep(int dir) {
   double tol = EqPips * Point * 10;
   for (int i = 3; i < 40; i++) {
      for (int j = i+2; j < 40; j++) {
         if (dir == 1 && MathAbs(Low[i]-Low[j]) < tol) {
            double lvl = (Low[i]+Low[j])/2.0;
            for (int k=1; k<i; k++)
               if (Low[k] < lvl-tol && Close[1] > lvl) {
                  if (ShowLabels) Label("Sw_B_"+TimeToStr(Time[k]),Time[k],Low[k]-15*_Point*10,"Sweep↑",clrAqua);
                  return true;
               }
         }
         if (dir == -1 && MathAbs(High[i]-High[j]) < tol) {
            double lvl = (High[i]+High[j])/2.0;
            for (int k=1; k<i; k++)
               if (High[k] > lvl+tol && Close[1] < lvl) {
                  if (ShowLabels) Label("Sw_S_"+TimeToStr(Time[k]),Time[k],High[k]+15*_Point*10,"Sweep↓",clrMagenta);
                  return true;
               }
         }
      }
   }
   return false;
}

//============================================================
//  STRICT FVG — zero wick overlap allowed (highest quality only)
//============================================================
bool FindFVGStrict(int dir, double &hi, double &lo) {
   for (int i = 1; i < FVG_Lookback-1; i++) {
      if (dir==1 && High[i+1]<Low[i-1] && Low[i]>High[i+1] && High[i]<Low[i-1]) {
         lo=High[i+1]; hi=Low[i-1]; if(hi>lo) return true;
      }
      if (dir==-1 && Low[i+1]>High[i-1] && High[i]<Low[i+1] && Low[i]>High[i-1]) {
         lo=High[i-1]; hi=Low[i+1]; if(hi>lo) return true;
      }
   }
   return false;
}

//============================================================
//  ORDER BLOCK
//============================================================
bool FindOB(int dir, double &hi, double &lo) {
   for (int i=1;i<OB_Lookback;i++) {
      if (dir==1  && Close[i]<Open[i] && i>0 && Close[i-1]>High[i]) { hi=High[i];lo=Low[i];return true; }
      if (dir==-1 && Close[i]>Open[i] && i>0 && Close[i-1]<Low[i])  { hi=High[i];lo=Low[i];return true; }
   }
   return false;
}

//============================================================
//  ENTRY ZONE: FVG takes priority, OB as fallback
//============================================================
void GetEntryZone(int dir, bool fok, double fHi, double fLo,
                  bool ook, double oHi, double oLo,
                  double &eHi, double &eLo) {
   if (fok)      { eHi=fHi; eLo=fLo; }
   else if (ook) { eHi=oHi; eLo=oLo; }
   else          { eHi=0;   eLo=0; return; }
   if (fok && ook) {
      double iHi=MathMin(fHi,oHi), iLo=MathMax(fLo,oLo);
      if (iHi>iLo) { eHi=iHi; eLo=iLo; }
   }
}

//============================================================
//  STRUCTURAL SL
//============================================================
double StructSL(int dir, double impSt) {
   double atr=iATR(NULL,0,ATR_Period,1);
   double buf=SL_Buffer_Pips*Point*10;
   if (UseStructuralSL && impSt>0) {
      double sl=(dir==1)?impSt-buf:impSt+buf;
      double dist=(dir==1)?Ask-sl:sl-Bid;
      if (dist>atr*0.5) return sl;
   }
   return (dir==1)?Ask-atr*ATR_SL_Mult:Bid+atr*ATR_SL_Mult;
}

//============================================================
//  PLACE ORDERS — split 40/35/25 across 3 targets
//============================================================
void PlaceOrders(int type, double price, double sl, string tag) {
   double slDist=(type==OP_BUY)?price-sl:sl-price;
   if (slDist<=0) return;
   double lots=CalcLots(slDist);
   double step=MarketInfo(Symbol(),MODE_LOTSTEP);
   double minL=MarketInfo(Symbol(),MODE_MINLOT);

   // Split: 40%, 35%, 25%
   double l1=MathMax(minL,MathFloor(lots*0.40/step)*step);
   double l2=MathMax(minL,MathFloor(lots*0.35/step)*step);
   double l3=MathMax(minL,MathFloor(lots*0.25/step)*step);

   double tp1=(type==OP_BUY)?price+slDist*TP1_RR:price-slDist*TP1_RR;
   double tp2=(type==OP_BUY)?price+slDist*TP2_RR:price-slDist*TP2_RR;
   color  clr=(type==OP_BUY)?clrGreen:clrRed;

   t1=OrderSend(Symbol(),type,l1,price,5,sl,tp1,"APEX_"+tag+"1",MagicNumber,0,clr);
   t2=OrderSend(Symbol(),type,l2,price,5,sl,tp2,"APEX_"+tag+"2",MagicNumber,0,clr);
   t3=OrderSend(Symbol(),type,l3,price,5,sl,0,  "APEX_"+tag+"3",MagicNumber,0,clr);

   if ((t1>0||t2>0||t3>0) && ShowLabels)
      Label("Ent_"+tag+TimeToStr(Time[0]),Time[0],
         (type==OP_BUY?Low[0]-55*_Point*10:High[0]+55*_Point*10),
         StringFormat("%s  SL:%.5f  TP1:%.5f  TP2:%.5f",
            (type==OP_BUY?"▲BUY":"▼SELL"),sl,tp1,tp2),clr);

   ObjectDelete("APEX_FVG_BOX_"+tag);
   ObjectDelete("APEX_OB_BOX_"+tag);
}

//============================================================
//  TRADE MANAGEMENT — breakeven at TP1, trail remainder
//============================================================
void ManageTrades() {
   double atr=iATR(NULL,0,ATR_Period,1);
   if (t3>0 && OrderSelect(t3,SELECT_BY_TICKET)) {
      if (OrderCloseTime()>0) { t3=-1; }
      else {
         int type=OrderType(); double op=OrderOpenPrice(),slN=OrderStopLoss(),nSL=slN;
         if (type==OP_BUY) {
            if (!tp1Done&&Bid>op+atr*TP1_RR) { nSL=op+3*Point*10; tp1Done=true; }
            if (tp1Done) { double c=Bid-atr*Trail_ATR; if(c>nSL) nSL=c; }
         }
         if (type==OP_SELL) {
            if (!tp1Done&&Ask<op-atr*TP1_RR) { nSL=op-3*Point*10; tp1Done=true; }
            if (tp1Done) { double c=Ask+atr*Trail_ATR; if(c<nSL) nSL=c; }
         }
         if (nSL!=slN&&nSL>0) OrderModify(t3,op,NormalizeDouble(nSL,Digits),OrderTakeProfit(),0);
      }
   } else if (t3>0) t3=-1;
   if (t1>0&&OrderSelect(t1,SELECT_BY_TICKET)&&OrderCloseTime()>0) t1=-1;
   if (t2>0&&OrderSelect(t2,SELECT_BY_TICKET)&&OrderCloseTime()>0) t2=-1;
}

//============================================================
//  H4 BIAS
//============================================================
int GetH4Bias() {
   double ema=iMA(NULL,PERIOD_H4,50,0,MODE_EMA,PRICE_CLOSE,1);
   double cls=iClose(NULL,PERIOD_H4,1);
   return (ema==0)?0:(cls>ema)?1:(cls<ema)?-1:0;
}

//============================================================
//  KILL ZONE
//============================================================
bool IsInKillZone() {
   int h=TimeHour(TimeCurrent()-GMT_Offset*3600);
   return (h>=London_Start&&h<London_End)||(h>=NY_Start&&h<NY_End);
}

//============================================================
//  SWING DETECTION
//============================================================
bool IsSwingHigh(int i) {
   if (i<=SwingStrength||i+SwingStrength>=Bars) return false;
   for (int j=1;j<=SwingStrength;j++) if(High[i-j]>=High[i]||High[i+j]>=High[i]) return false;
   return true;
}
bool IsSwingLow(int i) {
   if (i<=SwingStrength||i+SwingStrength>=Bars) return false;
   for (int j=1;j<=SwingStrength;j++) if(Low[i-j]<=Low[i]||Low[i+j]<=Low[i]) return false;
   return true;
}
double GetSwingHigh(int n) { int c=0;for(int i=SwingStrength+1;i<400;i++) if(IsSwingHigh(i)){c++;if(c==n)return High[i];}return 0; }
double GetSwingLow(int n)  { int c=0;for(int i=SwingStrength+1;i<400;i++) if(IsSwingLow(i)) {c++;if(c==n)return Low[i]; }return 0; }

//============================================================
//  POSITION SIZING
//============================================================
double CalcLots(double slDist) {
   if(slDist<=0) return MarketInfo(Symbol(),MODE_MINLOT);
   double risk=AccountBalance()*RiskPercent/100.0;
   double ticks=slDist/MarketInfo(Symbol(),MODE_TICKSIZE);
   double lots=risk/(ticks*MarketInfo(Symbol(),MODE_TICKVALUE));
   double step=MarketInfo(Symbol(),MODE_LOTSTEP);
   lots=MathFloor(lots/step)*step;
   return MathMax(MarketInfo(Symbol(),MODE_MINLOT),MathMin(MarketInfo(Symbol(),MODE_MAXLOT),lots));
}

int CountOrders() {
   int n=0;
   for(int i=OrdersTotal()-1;i>=0;i--)
      if(OrderSelect(i,SELECT_BY_POS,MODE_TRADES)&&OrderMagicNumber()==MagicNumber&&OrderSymbol()==Symbol()) n++;
   return n;
}

//============================================================
//  NEWS FILTER
//============================================================
void FetchNews() {
   newsCount=0; lastFetch=TimeCurrent();
   char req[],res[]; string hdrs; ArrayResize(req,0);
   int code=WebRequest("GET",News_URL,"",5000,req,res,hdrs);
   if(code!=200){Print("APEX: News fetch failed (code=",code,"). Enable WebRequest URL.");return;}
   string json=CharArrayToString(res); int pos=0;
   while(newsCount<99){
      int ip=StringFind(json,"\"impact\":\"High\"",pos); if(ip<0) break;
      int os=ip; while(os>0&&StringSubstr(json,os,1)!="{") os--;
      string obj=StringSubstr(json,os,ip-os+30);
      if(StringFind(obj,"\"country\":\"USD\"")>=0||StringFind(obj,"\"country\":\"EUR\"")>=0){
         int dp=StringFind(json,"\"date\":\"",os);
         if(dp>0&&dp<ip+200){
            datetime t=ParseDate(StringSubstr(json,dp+8,19));
            if(t>TimeCurrent()-3600){newsTime[newsCount]=t;newsCount++;}
         }
      }
      pos=ip+15;
   }
   Print("APEX: ",newsCount," high-impact news events loaded.");
}

datetime ParseDate(string s) {
   if(StringLen(s)<19) return 0;
   string f=StringSubstr(s,0,4)+"."+StringSubstr(s,5,2)+"."+StringSubstr(s,8,2)+" "+StringSubstr(s,11,2)+":"+StringSubstr(s,14,2);
   datetime utc=StringToTime(f); utc-=News_TZ_Offset*3600; utc+=GMT_Offset*3600;
   return utc;
}

bool IsNewsBlackout() {
   if(!UseNewsFilter||newsCount==0) return false;
   datetime now=TimeCurrent();
   for(int i=0;i<newsCount;i++)
      if(now>=newsTime[i]-News_MinsBefore*60&&now<=newsTime[i]+News_MinsAfter*60){
         if(ShowLabels) Label("NB",Time[0],Low[0]-65*_Point*10,"⛔ NEWS",clrYellow);
         return true;
      }
   return false;
}

//============================================================
//  VISUALS
//============================================================
void DrawZones(string tag, int dir, bool fok, double fHi, double fLo,
               bool ook, double oHi, double oLo) {
   if(!ShowZoneBoxes) return;
   datetime t2=Time[0]+BoxProjectBars*PeriodSeconds();
   if(fok) DrawBox("APEX_FVG_BOX_"+tag,Time[FVG_Lookback],fLo,t2,fHi,(dir==1?FVG_Bull_Color:FVG_Bear_Color));
   if(ook) DrawBox("APEX_OB_BOX_"+tag, Time[OB_Lookback], oLo,t2,oHi,(dir==1?OB_Bull_Color:OB_Bear_Color));
}

void DrawBox(string n,datetime t1,double p1,datetime t2,double p2,color clr){
   if(ObjectFind(n)>=0) ObjectDelete(n);
   ObjectCreate(n,OBJ_RECTANGLE,0,t1,p1,t2,p2);
   ObjectSet(n,OBJPROP_COLOR,clr); ObjectSet(n,OBJPROP_BACK,true);
   ObjectSet(n,OBJPROP_FILL,true); ObjectSet(n,OBJPROP_WIDTH,1);
}

void DrawHLine(string n,double p,color clr,int sty){
   if(ObjectFind(n)>=0) ObjectDelete(n);
   ObjectCreate(n,OBJ_HLINE,0,0,p);
   ObjectSet(n,OBJPROP_COLOR,clr); ObjectSet(n,OBJPROP_STYLE,sty); ObjectSet(n,OBJPROP_WIDTH,1);
}

void Label(string n,datetime t,double p,string txt,color clr){
   string nn="APEX_"+n; if(ObjectFind(nn)>=0) ObjectDelete(nn);
   ObjectCreate(nn,OBJ_TEXT,0,t,p);
   ObjectSetString(0,nn,OBJPROP_TEXT,txt);
   ObjectSet(nn,OBJPROP_COLOR,clr); ObjectSet(nn,OBJPROP_FONTSIZE,8);
}

//============================================================
//  RESETS
//============================================================
void ResetBOS(){
   bosActive=false;bosBias=0;bosLevel=bosImpSt=bosImpEnd=0;bosFvgOK=bosObOK=false;
   ObjectDelete("APEX_FVG_BOX_BOS");ObjectDelete("APEX_OB_BOX_BOS");ObjectDelete("APEX_BOS_A");
}
void ResetCH(){
   chActive=false;chBias=0;chChochLvl=chBosTarget=chImpSt=chImpEnd=0;
   chFvgOK=chObOK=chBOSDone=chSwept=false;
   ObjectDelete("APEX_FVG_BOX_CH");ObjectDelete("APEX_OB_BOX_CH");
   ObjectDelete("APEX_CHOCH");ObjectDelete("APEX_BOS_B");
}
