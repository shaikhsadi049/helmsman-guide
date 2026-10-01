//+------------------------------------------------------------------+
//| Assay — a gold robot that measures its own constants             |
//| Research: gold-research/README.md (dynamic portfolio 2025-2026)   |
//|                                                                  |
//| Every trade's constants are measured from the recent market:     |
//|   Stop  = quantile(qSL) of recent signals' adverse excursion     |
//|   TP1   = quantile(qTP) of recent signals' favourable excursion  |
//|   Trail = quantile(qTR) of recent H4 trend pullback depths       |
//| Entry : EMA-stack pullback + higher-TF confluence + H4/D1 trend. |
//+------------------------------------------------------------------+
#property copyright "Assay"
#property version   "1.00"
#property strict
//  the tester has no economic calendar; this ships the archive to every agent
#property tester_file "Assay_News.csv"
#include <Trade/Trade.mqh>
#include <Assay/Account.mqh>
#include <Assay/Prop.mqh>
#include <Assay/News.mqh>
#include <Assay/Journal.mqh>
#include <Assay/ChartStyle.mqh>

//+------------------------------------------------------------------+
//| RDIAL -- what the customer sees, and what only research sees.     |
//|                                                                  |
//| RDIAL is `input` in a research build and nothing at all in the   |
//| build that ships, so a hidden dial becomes a plain global with   |
//| the SAME default. The define below stays commented out in this  |
//| file forever: the backtest harness injects it into the copy it   |
//| compiles, and tools/build_release.py compiles this file as it    |
//| stands and refuses to ship unless exactly nine inputs show.      |
//+------------------------------------------------------------------+
//#define RESEARCH_BUILD
#ifdef RESEARCH_BUILD
   #define RDIAL input
#else
   #define RDIAL
#endif

//+------------------------------------------------------------------+
//| What the trader decides. Everything else is measured.            |
//+------------------------------------------------------------------+
input group "General"
input ulong           MagicBase              = 881000;   // Trade ID (magic number)
input bool            ShowPanel              = true;   // Show dashboard
input group "Risk & Money Management"
input double          MaxRiskPercent         = 5.0;   // Max risk per trade (%)
input double          MaxOpenRiskPercent     = 15;   // Max total open risk (%)
input int             MaxTotalPositions      = 10;   // Max open trades
input double          DailyLossStopPct       = 0;   // Daily loss limit (%, 0 = off)
input double          MaxDrawdownStopPercent = 0;   // Pause at drawdown (%, 0 = off)
input double          MaxSpreadPrice         = 0.80;   // Max spread ($)
input group "Prop Firm"
input bool            PropMode               = false;   // Prop firm mode
input double          PropAccountSize        = 0;   // Challenge account size ($)
input double          PropDailyLossPct       = 5.0;   // Daily loss limit (%)
input double          PropMaxLossPct         = 10.0;   // Max loss limit (%)
input bool            PropTrailing           = false;   // Max loss trails equity peak
input double          PropTargetPct          = 10.0;   // Profit target (%, 0 = none)
input ENUM_PROP_RESET PropReset              = PROP_RESET_SERVER;   // Daily reset time
input double          PropBufferPct          = 1.0;   // Safety buffer before limits (%)
input int             PropMinDays            = 0;   // Minimum trading days
input bool            PropFlatWeekend        = false;   // Close all before weekend
input group "News Filter"
input bool            NewsShield             = false;   // News filter
input int             NewsBeforeMin          = 30;   // Pause before news (minutes)
input int             NewsAfterMin           = 30;   // Pause after news (minutes)
input string          NewsCurrencies         = "USD";   // News currencies (e.g. USD,EUR)


enum ADX_RULE { ADX_ANY = 0, ADX_LT30 = 1 };
enum ENTRY_KIND { E_PB = 0, E_RSI2 = 1, E_BRK = 2, E_RSIF = 3, E_ZF = 4, E_FBO = 5 };   // 3..5 = mean reversion (fade)
enum RISK_MODE { RISK_DD_TREND = 0, RISK_DD_EDGE = 1, RISK_DD = 2, RISK_EDGE = 3, RISK_FIXED_MAX = 4 };
#define NS 11

#ifdef RESEARCH_BUILD
input group "=== Assay ==="
#endif
RDIAL double MinRiskPercent   = 1.0;    // dynamic risk per trade: lowest % of equity
RDIAL RISK_MODE RiskMode      = RISK_DD_TREND; // DD_TREND = drawdown x gold daily trend strength (research best), DD_EDGE = drawdown x slot edge, DD = drawdown only, EDGE = edge only (risky), FIXED_MAX = always MaxRiskPercent
RDIAL int    TrendEMA         = 50;     // DD_TREND: daily EMA; trend strength = |close - EMA| / daily ATR
RDIAL int    TrendLookback    = 250;    // DD_TREND: strength is ranked against the last N days (0..1)
RDIAL double EdgeLow          = 0.73;   // slot edge (median MFE / median MAE of recent signals) at or below this -> lowest edge score
RDIAL double EdgeHigh         = 2.6;    // slot edge at or above this -> full edge score
RDIAL double FixedLots        = 0.01;   // used when MaxRiskPercent = 0
//  When the size the risk model asks for rounds below the broker's minimum
//  lot, take the minimum lot anyway IF what it really risks is still inside
//  MaxRiskPercent. No new number: the ceiling is the one already set above,
//  and the cost is measured from the stop the risk model just computed. On a
//  large account it never fires. On a small one it is the difference between
//  seeing 0.8% of signals and seeing every one the ceiling can pay for.
RDIAL bool   MinLotStretch    = true;   // below the minimum lot: take the minimum lot when it fits inside MaxRiskPercent
//  A stretched trade is always the minimum lot, so the risk model's answer --
//  smaller in a drawdown, smaller for a fade while the trend is strong -- has
//  no size left to express itself in. The only lever remaining is whether to
//  take the trade. This lets a slot stretch only while it is in the better
//  half of its own regime. 0.5 is not a threshold anyone picked: TrendScore is
//  a percentile rank against the last 250 days, so 0.5 is its median by
//  construction, and 1 - TrendScore for a fade slot has the same median.
RDIAL double MinLotStretchMaxPct = 2;   // a stretched min-lot trade may risk at most this % of equity (0 = MaxRiskPercent)
RDIAL bool   MinLotStretchFades = false; // the stretch for the fade slots too (A59: their wide-stop signals average ~0R)
RDIAL bool   MinLotRegimeGate = false;  // stretch only while the slot is in the better half of its own regime
RDIAL int    ServerUTCOffset  = 2;      // broker server time minus UTC, hours
RDIAL int    MaxHoldDays      = 30;     // safety time exit
RDIAL double ThrottleFullDD     = 20;   // risk slides from Max toward Min as equity falls below its peak; at this drawdown % it is MinRiskPercent
RDIAL double PyrRiskMult      = 1.0;    // a pyramid add's stop distance, as a share of a first entry's (its size is a first entry's)
RDIAL bool   PyrBookAtTp1     = false;  // a pyramid add closes whole at its first target instead of running
RDIAL int    MaxPositions     = 1;      // per slot. >1 = pyramiding: add only while all open positions are risk-free (hedging account)
RDIAL double TP1FractionOverride = -1;  // -1 = use each slot's F1; 0.5 = close half at TP1; 0 = only lock the stop at TP1
//  What to do when TP1 is reached but the slice cannot be banked because the
//  whole position is already the minimum lot. Only reachable where a partial
//  was actually asked for (F1 > 0); slots with F1 = 0 are unaffected, since
//  for them locking the stop IS the mechanism rather than a consolation.
RDIAL int    MinLotTp1Mode    = 0;      // 0 = lock the stop anyway (as before), 1 = leave it running, 2 = close it all
//  Profit ratchet. The H4 trail is wide by design (it is measured from whole
//  H4 trend pullbacks) and only moves on an H4 close, so an intraday spike to
//  several R could fall all the way back to the TP1 lock. Once open profit
//  reaches what only the best tenth of this slot's recent signals reached
//  (the 0.9 quantile of their favourable excursion, in R), the stop keeps at
//  least RatchetKeep of the open profit, checked on every tick.
//  2025-01..2026-07, S1-S6 + fades, 1..5% risk: same total growth, losing
//  months 5 -> 3, trades that reached 2R but ended under 0.5R 46 -> 35.
RDIAL bool   ProfitRatchet    = true;
RDIAL double RatchetQ         = 0.9;    // which recent-signal profit counts as "big" (quantile)
RDIAL double RatchetKeep      = 0.5;    // share of open profit the stop keeps once it is big
RDIAL int    BackfillDays     = 240;    // days of history scanned at start to calibrate (research used ~7 months)

#ifdef RESEARCH_BUILD
input group "=== Prop firm ==="
#endif
//  One switch and the firm's own numbers. Everything else is derived: the
//  per-trade risk becomes the daily allowance shared across the most positions
//  the EA may hold, so a full book stopped out together still fits in one day.
//  kept out of the dialog: sensible for every firm checked, and a trader who
//  needs to change them is better served by asking than by guessing
bool   PropDayOfInitial = true;  // daily allowance as % of the initial size (else of the day's start)
RDIAL int  WeekendCloseMins = 30;     // how long before that close to stop and flatten

#ifdef RESEARCH_BUILD
input group "=== Strategy slots (spec string, or OFF) ==="
#endif
// Keys: TF=M3|M5|M15|M30|H1  ENTRY=PB|RSI2|BRK  EMA=30|40|60 (PB)  RSI=10|5 (RSI2)  BRKN=20 (BRK)
//       CONF1/CONF2=NONE|M15|H1|H4 (higher-TF EMA stack must agree)  ADX=ANY|LT30  SESS=1|0
//       LOOK (signals used for calibration)  QSL QTP QTR (quantiles)  LOCK (R)  F1 (share closed at TP1)
// Defaults = the 7-strategy portfolio from the research (steps 1..7). Use OFF to disable a slot.
RDIAL string Slot1 = "TF=M30;ENTRY=PB;EMA=30;CONF1=H1;SESS=1;LOOK=60;QSL=0.7;QTP=0.3;LOCK=0.25;QTR=0.8;F1=0";
RDIAL string Slot2 = "TF=M15;ENTRY=BRK;BRKN=20;CONF1=H1;CONF2=H4;SESS=0;LOOK=60;QSL=0.5;QTP=0.2;LOCK=0.1;QTR=0.8;F1=0";
RDIAL string Slot3 = "TF=M3;ENTRY=RSI2;RSI=10;CONF1=M15;CONF2=H1;SESS=1;LOOK=60;QSL=0.7;QTP=0.2;LOCK=0.1;QTR=0.5;F1=0.5";
RDIAL string Slot4 = "TF=M30;ENTRY=BRK;BRKN=20;SESS=0;LOOK=60;QSL=0.7;QTP=0.2;LOCK=0.25;QTR=0.8;F1=0";
RDIAL string Slot5 = "TF=M5;ENTRY=PB;EMA=30;CONF1=M15;CONF2=H1;SESS=1;LOOK=60;QSL=0.5;QTP=0.5;LOCK=0.25;QTR=0.5;F1=0.5";
RDIAL string Slot6 = "TF=M3;ENTRY=RSI2;RSI=5;CONF1=M15;CONF2=H1;SESS=1;LOOK=60;QSL=0.7;QTP=0.2;LOCK=0.1;QTR=0.5;F1=0.5";
RDIAL string Slot7 = "OFF;TF=M3;ENTRY=BRK;BRKN=20;CONF1=M15;CONF2=H1;SESS=0;LOOK=60;QSL=0.7;QTP=0.2;LOCK=0.1;QTR=0.8;F1=0";

#ifdef RESEARCH_BUILD
input group "=== Sideways / mean-reversion slots (fade stretched moves while the H4 trend is off) ==="
#endif
// ENTRY=RSIF (RSI(2) below RSI= -> buy, above 100-RSI= -> sell) | ZF (close beyond Z= std devs of the 20-bar mean)
//       | FBO (bar pierces the BRKN-bar extreme but closes back inside)
// REG=NO4H: only while the H4 6-EMA stack is NOT aligned. Exit: full close at a market-measured target
// (broker TP), market-measured stop, or after HOR minutes. No trailing, no DXY.
RDIAL double MRRiskMult = 0.5;          // risk of a fade trade = normal dynamic risk x this (and it grows when the trend is WEAK)
RDIAL string Slot8  = "TF=M15;ENTRY=RSIF;RSI=5;REG=NO4H;SESS=1;HOR=360;LOOK=60;QSL=0.7;QTP=0.5";
RDIAL string Slot9  = "TF=H1;ENTRY=ZF;Z=2;REG=NO4H;SESS=0;HOR=720;LOOK=60;QSL=0.7;QTP=0.5";
RDIAL string Slot10 = "TF=M30;ENTRY=ZF;Z=2.5;REG=NO4H;SESS=0;HOR=480;LOOK=60;QSL=0.7;QTP=0.5";
RDIAL string Slot11 = "TF=H1;ENTRY=FBO;BRKN=20;REG=NO4H;SESS=1;HOR=720;LOOK=60;QSL=0.7;QTP=0.5";

#ifdef RESEARCH_BUILD
input group "=== Daily DXY (tighten runner trail when the dollar turns against gold) ==="
#endif
RDIAL bool   UseDXY           = true;
RDIAL string DXYSymbol        = "";     // e.g. "DXY" or "USDX"; empty = build DXY from 6 FX pairs
RDIAL double DXYAgainstTrail  = 0.7;    // trail width multiplier when USD daily trend opposes the trade

#ifdef RESEARCH_BUILD
input group "=== Session (UTC hours) ==="
#endif
RDIAL int SessFromUTC = 7;
RDIAL int SessToUTC   = 20;

#ifdef RESEARCH_BUILD
input group "=== Research journal (tester only) ==="
#endif
RDIAL int    JournalMode = 0;       // 0 off; 1 = log every signal and what was done with it; 2 = take EVERY signal at JournalLots to measure its outcome
RDIAL double JournalLots = 1.0;     // mode 2 size: large enough that the partial at the first target can be taken
RDIAL string JournalTag  = "";      // file name tag
RDIAL string SlotVeto    = "";      // research: "S3:hour<7;F9:adx>35" -- skip a slot's signal when the rule holds

//--- constants of the method (same as the research)
#define K_MIN          0.5
#define K_MAX          8.0
#define R1_MIN         0.1
#define R1_MAX         3.0
#define EPISODES       20
#define MAX_SIGS       400

struct Sig { datetime t; int dir; double lvl; double atr; double mae; double mfe; bool done; datetime endT; };

struct Slot
{
   bool on, mr; ENUM_TIMEFRAMES tf, c1, c2; int entry, pb, rsiTh, brkN, adx, horizon, look, reg; bool sess; double qsl, qtp, lock, qtr, f1, zTh, km, rm, tm; ulong magic;
   Sig sigs[]; int nsig;
   datetime lastBar;
   // last calibrated values (for the panel)
   double kNow, r1Now, trNow, riskNow;
};
Slot S[NS];
CTrade trade;
CPropGuard g_prop;
//  declared up here so OnInit can reset it: on an input change MT5 keeps the
//  globals, and a `ready` left true after Load() emptied every slot's history
//  let the EA trade on default stops until twenty new signals had arrived
bool ready = false;
//  every slot's last decision, for the panel: what it did with its last signal
//  and why. The Monday Relay sat through 250 pips in silence is the reason.
string   g_why[11];
datetime g_whyT[11];
//  every signal's fate since the EA started, for the panel: taken, skipped
//  because even the smallest lot's stop costs more than the risk allows,
//  skipped because the slot or the book was full, or any other gate
int g_sigN[11], g_takeN[11], g_wideN[11], g_busyN[11];
void Why(const int k, const string s)
{
   if(k < 0 || k >= 11) return;
   g_why[k] = s; g_whyT[k] = TimeCurrent();
   g_sigN[k]++;
   if(StringFind(s, "opened") == 0) g_takeN[k]++;
   else if(StringFind(s, "too wide") >= 0) g_wideN[k]++;
   else if(StringFind(s, "busy") >= 0) g_busyN[k]++;
}
double epDepth[]; int nEp = 0; datetime lastH4 = 0;

//------------------------------------------------------------------ indicator helpers
int hE[7][12]; int hA[12], hX[12], h20[12], h50[12], hR[12]; ENUM_TIMEFRAMES tfL[12]; int nTf = 0;
const int EL[7] = {30, 35, 40, 45, 50, 60, 20};

int TI(ENUM_TIMEFRAMES tf)
{
   for(int i = 0; i < nTf; i++) if(tfL[i] == tf) return i;
   int i = nTf++; tfL[i] = tf;
   for(int k = 0; k < 6; k++) hE[k][i] = iMA(_Symbol, tf, EL[k], 0, MODE_EMA, PRICE_CLOSE);
   hA[i] = iATR(_Symbol, tf, 14);
   hX[i] = iADXWilder(_Symbol, tf, 14);
   hR[i] = iRSI(_Symbol, tf, 2, PRICE_CLOSE);
   h20[i] = iMA(_Symbol, tf, 20, 0, MODE_EMA, PRICE_CLOSE);
   h50[i] = iMA(_Symbol, tf, 50, 0, MODE_EMA, PRICE_CLOSE);
   return i;
}
double B(int h, int shift, int buf = 0) { double v[1]; if(CopyBuffer(h, buf, shift, 1, v) != 1) return EMPTY_VALUE; return v[0]; }

// shift of the last bar of `tf` that is fully closed at time T
int ClosedShift(ENUM_TIMEFRAMES tf, datetime T)
{
   int s = iBarShift(_Symbol, tf, T - 1, false);
   if(s < 0) return -1;
   datetime o = iTime(_Symbol, tf, s);
   if(o + PeriodSeconds(tf) <= T) return s;
   return s + 1;
}
int StackAt(ENUM_TIMEFRAMES tf, int shift)
{
   if(shift < 0) return 0;
   int i = TI(tf); double e[6];
   for(int k = 0; k < 6; k++) { e[k] = B(hE[k][i], shift); if(e[k] == EMPTY_VALUE) return 0; }
   bool bu = true, be = true;
   for(int k = 0; k < 5; k++) { if(!(e[k] > e[k + 1])) bu = false; if(!(e[k] < e[k + 1])) be = false; }
   return bu ? 1 : (be ? -1 : 0);
}
// H4 / D1 filter: previous closed HTF bar relative to the HTF bar containing T-1s, EMA20 vs EMA50
int HtfDirAt(ENUM_TIMEFRAMES tf, datetime T)
{
   int s = iBarShift(_Symbol, tf, T - 1, false);
   if(s < 0) return 0;
   int i = TI(tf); double f = B(h20[i], s + 1), sl = B(h50[i], s + 1);
   if(f == EMPTY_VALUE || sl == EMPTY_VALUE) return 0;
   return f > sl ? 1 : -1;
}
bool InSessionUTC(datetime serverT)
{
   MqlDateTime t; TimeToStruct(serverT - ServerUTCOffset * 3600, t);
   return t.hour >= SessFromUTC && t.hour < SessToUTC;
}

//------------------------------------------------------------------ signal on bar `sh` of slot tf (bar close time T)
// mean-reversion (fade) signal: no trend needed; optionally only while the H4 stack is not aligned
int FadeSignalAt(Slot &s, int sh)
{
   datetime T = iTime(_Symbol, s.tf, sh) + PeriodSeconds(s.tf);
   int i = TI(s.tf);
   double h = iHigh(_Symbol, s.tf, sh), l = iLow(_Symbol, s.tf, sh), c = iClose(_Symbol, s.tf, sh);
   int dir = 0;
   if(s.entry == E_RSIF)
   {
      double r = B(hR[i], sh);
      if(r == EMPTY_VALUE) return 0;
      if(r < s.rsiTh) dir = 1; else if(r > 100 - s.rsiTh) dir = -1;
   }
   else if(s.entry == E_ZF)
   {
      double x[]; if(CopyClose(_Symbol, s.tf, sh, 20, x) != 20) return 0;
      double m = 0, v = 0; for(int k = 0; k < 20; k++) m += x[k]; m /= 20;
      for(int k = 0; k < 20; k++) v += (x[k] - m) * (x[k] - m);
      double sd = MathSqrt(v / 19); if(sd <= 0) return 0;
      double z = (c - m) / sd;
      if(z < -s.zTh) dir = 1; else if(z > s.zTh) dir = -1;
   }
   else
   {
      int hi = iHighest(_Symbol, s.tf, MODE_HIGH, s.brkN, sh + 1), lo = iLowest(_Symbol, s.tf, MODE_LOW, s.brkN, sh + 1);
      if(hi < 0 || lo < 0) return 0;
      double hh = iHigh(_Symbol, s.tf, hi), ll = iLow(_Symbol, s.tf, lo);
      if(h > hh && c < hh) dir = -1; else if(l < ll && c > ll) dir = 1;
   }
   if(dir == 0) return 0;
   if(s.reg == 1 && StackAt(PERIOD_H4, ClosedShift(PERIOD_H4, T)) != 0) return 0;
   if(s.sess && !InSessionUTC(T - 60)) return 0;
   return dir;
}
int SignalAt(Slot &s, int sh)
{
   if(s.mr) return FadeSignalAt(s, sh);
   datetime T = iTime(_Symbol, s.tf, sh) + PeriodSeconds(s.tf);
   int st = StackAt(s.tf, sh);
   if(st == 0) return 0;
   int i = TI(s.tf);
   double o = iOpen(_Symbol, s.tf, sh), h = iHigh(_Symbol, s.tf, sh), l = iLow(_Symbol, s.tf, sh), c = iClose(_Symbol, s.tf, sh);
   int dir = 0;
   if(s.entry == E_PB)
   {
      // stack aligned, bar dips into EMA(pb) and closes back beyond EMA30 in trend direction
      int pbk = s.pb == 40 ? 2 : (s.pb == 60 ? 5 : 0);
      double ePb = B(hE[pbk][i], sh), e30 = B(hE[0][i], sh);
      if(st == 1 && l <= ePb && c > e30 && c > o) dir = 1;
      if(st == -1 && h >= ePb && c < e30 && c < o) dir = -1;
   }
   else if(s.entry == E_RSI2)
   {
      // short-term exhaustion against the trend: RSI(2) below th (long) / above 100-th (short)
      double r = B(hR[i], sh);
      if(r == EMPTY_VALUE) return 0;
      if(st == 1 && r < s.rsiTh) dir = 1;
      if(st == -1 && r > 100 - s.rsiTh) dir = -1;
   }
   else
   {
      // close beyond the extreme of the previous brkN bars in trend direction
      int hi = iHighest(_Symbol, s.tf, MODE_HIGH, s.brkN, sh + 1), lo = iLowest(_Symbol, s.tf, MODE_LOW, s.brkN, sh + 1);
      if(hi < 0 || lo < 0) return 0;
      if(st == 1 && c > iHigh(_Symbol, s.tf, hi)) dir = 1;
      if(st == -1 && c < iLow(_Symbol, s.tf, lo)) dir = -1;
   }
   if(dir == 0) return 0;
   if(HtfDirAt(PERIOD_H4, T) != dir || HtfDirAt(PERIOD_D1, T) != dir) return 0;
   if(s.c1 != PERIOD_CURRENT && StackAt(s.c1, ClosedShift(s.c1, T)) != dir) return 0;
   if(s.c2 != PERIOD_CURRENT && StackAt(s.c2, ClosedShift(s.c2, T)) != dir) return 0;
   if(s.adx == ADX_LT30) { double a = B(hX[i], sh); if(!(a < 30)) return 0; }
   if(s.sess && !InSessionUTC(T - 60)) return 0;
   return dir;
}

//------------------------------------------------------------------ market measurements
void Excursion(Sig &g, ENUM_TIMEFRAMES tf)
{
   double hi[], lo[];
   int n1 = CopyHigh(_Symbol, tf, g.t, g.endT - 1, hi), n2 = CopyLow(_Symbol, tf, g.t, g.endT - 1, lo);
   if(n1 <= 0 || n2 <= 0) return;
   double a = 0, f = 0;
   for(int k = 0; k < MathMin(n1, n2); k++)
   {
      if(g.dir == 1) { a = MathMax(a, g.lvl - lo[k]); f = MathMax(f, hi[k] - g.lvl); }
      else           { a = MathMax(a, hi[k] - g.lvl); f = MathMax(f, g.lvl - lo[k]); }
   }
   g.mae = a / g.atr; g.mfe = f / g.atr; g.done = true;
}
void AddSig(Slot &s, datetime T, int dir, double lvl, double atr)
{
   if(s.nsig >= MAX_SIGS) { for(int k = 1; k < s.nsig; k++) s.sigs[k - 1] = s.sigs[k]; s.nsig--; }
   if(ArraySize(s.sigs) < s.nsig + 1) ArrayResize(s.sigs, s.nsig + 50);
   Sig g; g.t = T; g.dir = dir; g.lvl = lvl; g.atr = atr; g.mae = 0; g.mfe = 0; g.done = false; g.endT = T + s.horizon * 60;
   s.sigs[s.nsig++] = g;
}
void Resolve(Slot &s, datetime now)
{
   for(int k = 0; k < s.nsig; k++) if(!s.sigs[k].done && s.sigs[k].endT <= now) Excursion(s.sigs[k], s.tf);
}
double Quantile(double &x[], int n, double q)
{
   double t[]; ArrayResize(t, n); for(int k = 0; k < n; k++) t[k] = x[k];
   ArraySort(t);
   double pos = q * (n - 1); int lo = (int)MathFloor(pos); int hi = (int)MathMin(n - 1, lo + 1);
   return t[lo] + (t[hi] - t[lo]) * (pos - lo);
}
// q-quantile of the last `look` resolved signals (field: 0 = mae, 1 = mfe); returns `def` when too few
double SigQuantile(Slot &s, int field, double q, double def)
{
   double x[]; ArrayResize(x, s.look); int c = 0;
   for(int k = s.nsig - 1; k >= 0 && c < s.look; k--)
      if(s.sigs[k].done) x[c++] = field == 0 ? s.sigs[k].mae : s.sigs[k].mfe;
   if(c < MathMax(10, s.look / 3)) return def;
   return Quantile(x, c, q);
}
// H4 trend episodes: deepest pullback from the running extreme while the 6-EMA stack held (ATR units)
void UpdateEpisodes()
{
   int n = (int)MathMin(1500, Bars(_Symbol, PERIOD_H4) - 70);
   if(n < 50) return;
   ArrayResize(epDepth, 0); nEp = 0;
   int state = 0; double ext = 0, deep = 0;
   for(int sh = n; sh >= 1; sh--)
   {
      int st = StackAt(PERIOD_H4, sh);
      double h = iHigh(_Symbol, PERIOD_H4, sh), l = iLow(_Symbol, PERIOD_H4, sh), a = B(hA[TI(PERIOD_H4)], sh);
      if(a == EMPTY_VALUE || a <= 0) continue;
      if(st != state)
      {
         if(state != 0) { ArrayResize(epDepth, nEp + 1); epDepth[nEp++] = deep; }
         state = st; deep = 0; ext = st == 1 ? h : l;
      }
      else if(state == 1) { ext = MathMax(ext, h); deep = MathMax(deep, (ext - l) / a); }
      else if(state == -1) { ext = MathMin(ext, l); deep = MathMax(deep, (h - ext) / a); }
   }
}
double TrailQuantile(double q)
{
   if(nEp < 8) return 3.0;
   int c = (int)MathMin(EPISODES, nEp); double x[]; ArrayResize(x, c);
   for(int k = 0; k < c; k++) x[k] = epDepth[nEp - c + k];
   return Quantile(x, c, q);
}

//------------------------------------------------------------------ daily DXY
// DXY = 50.14348112 * EURUSD^-0.576 * USDJPY^0.136 * GBPUSD^-0.119 * USDCAD^0.091 * USDSEK^0.042 * USDCHF^0.036
//  The six pairs, as THIS broker names them. Resolved once in OnInit through
//  AcctFx, which tries the gold symbol's suffix twin, the bare name, and then
//  every symbol whose base and profit currencies match. An empty slot means
//  the broker does not carry that pair, and DXY is switched off for the run.
string g_fx[6];
bool   g_fxInv[6];            // only the opposite pair exists: use 1/price
bool   g_dxyLive = false;
string g_dxyNative = "";      // a native dollar index, when the pairs cannot be found

double DxyClose(int shift)
{
   if(DXYSymbol != "") return iClose(DXYSymbol, PERIOD_D1, shift);
   if(!g_dxyLive) return 0;
   if(g_dxyNative != "")
   {
      int nsh = iBarShift(g_dxyNative, PERIOD_D1, iTime(_Symbol, PERIOD_D1, shift), false);
      return nsh < 0 ? 0 : iClose(g_dxyNative, PERIOD_D1, nsh);
   }
   double w[6] = {-0.576, 0.136, -0.119, 0.091, 0.042, 0.036};
   datetime t = iTime(_Symbol, PERIOD_D1, shift);
   double v = 50.14348112;
   for(int k = 0; k < 6; k++)
   {
      string sym = g_fx[k];
      int sh = iBarShift(sym, PERIOD_D1, t, false);
      double c = sh < 0 ? 0 : iClose(sym, PERIOD_D1, sh);
      if(c <= 0) return 0;
      if(g_fxInv[k]) c = 1.0 / c;
      v *= MathPow(c, w[k]);
   }
   return v;
}
// +1 = USD daily uptrend (EMA20 > EMA50 on the previous closed day), -1 = downtrend, 0 = unknown
int UsdDailyDir()
{
   int n = 160; double c[]; ArrayResize(c, n);
   for(int k = 0; k < n; k++) { c[k] = DxyClose(n - k); if(c[k] <= 0) return 0; }   // oldest -> newest, ends at shift 1
   double a20 = 2.0 / 21, a50 = 2.0 / 51, e20 = c[0], e50 = c[0];
   for(int k = 1; k < n; k++) { e20 += a20 * (c[k] - e20); e50 += a50 * (c[k] - e50); }
   return e20 > e50 ? 1 : -1;
}


//------------------------------------------------------------------ account-level risk guards
//  money per 1.00 of price per `lots` -- through the account layer's LOSS
//  tick value, the same figure Lots() sizes with
double MoneyPerPriceUnit(double lots)
{
   return lots * AcctLossPerLot(1.0);
}
// % of equity that would be lost if every open position of this EA hit its stop now
double OpenRiskPercent()
{
   double eq = AccountInfoDouble(ACCOUNT_EQUITY), risk = 0;
   if(eq <= 0) return 100;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      PositionGetTicket(k);
      long mg = PositionGetInteger(POSITION_MAGIC);
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || mg < (long)MagicBase || mg >= (long)MagicBase + NS) continue;
      int d = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1;
      double sl = PositionGetDouble(POSITION_SL), op = PositionGetDouble(POSITION_PRICE_OPEN), v = PositionGetDouble(POSITION_VOLUME);
      if(sl <= 0) { risk += eq; continue; }                      // no stop = unlimited risk
      double lossPts = (op - sl) * d;                            // <= 0 when the stop is already in profit
      if(lossPts > 0) risk += lossPts * MoneyPerPriceUnit(v);
   }
   return risk / eq * 100.0;
}
// equity peak persists across restarts in a terminal global variable.
//
// [perf] The peak is now held in memory as well. It is still seeded from the
// terminal global on the first call and still written back whenever the peak
// MOVES; what is gone is rebuilding the key string and rewriting an unchanged
// value on every tick. The panel reaches this function eleven times per tick
// through RiskPctNow -> DDScore, so that was 11 string builds and 33 terminal
// global operations per tick. Every value this function returns is unchanged.
string g_peakKey = "";
double g_peak    = 0.0;
//  set while the dashboard draws: between two of this symbol's ticks equity can
//  still move (another EA's position), and the panel must never record a peak
//  the trading path did not see
bool   g_peakFrozen = false;
double CurrentDrawdown()
{
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_peakKey == "")
   {
      //  keyed by LOGIN too: the peak drives the risk throttle, and without the
      //  login a move from a demo to a live account inherited the demo's peak
      g_peakKey = "ASSAY_PEAK_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))
                  + "_" + _Symbol + "_" + IntegerToString((long)MagicBase);
      g_peak = GlobalVariableCheck(g_peakKey) ? GlobalVariableGet(g_peakKey) : eq;
      GlobalVariableSet(g_peakKey, g_peak);
   }
   if(eq > g_peak && !g_peakFrozen) { g_peak = eq; GlobalVariableSet(g_peakKey, g_peak); }
   return g_peak > 0 ? 1.0 - eq / g_peak : 0;
}
bool DrawdownStopActive()
{
   if(MaxDrawdownStopPercent <= 0) return false;
   return CurrentDrawdown() * 100.0 > MaxDrawdownStopPercent;
}
// drawdown score: 1 at the equity peak, falling linearly to 0 at ThrottleFullDD
double DDScore()
{
   if(ThrottleFullDD <= 0) return 1.0;
   return MathMax(0.0, 1.0 - CurrentDrawdown() * 100.0 / ThrottleFullDD);
}
// edge score of a slot: median favourable / median adverse move of its recent signals, scaled 0..1
double EdgeScore(Slot &s)
{
   double mae = SigQuantile(s, 0, 0.5, -1), mfe = SigQuantile(s, 1, 0.5, -1);
   if(mae <= 0 || mfe < 0 || EdgeHigh <= EdgeLow) return 0.5;    // not enough history yet -> neutral
   return MathMax(0.0, MathMin(1.0, (mfe / mae - EdgeLow) / (EdgeHigh - EdgeLow)));
}
// gold daily trend strength now, ranked 0..1 against the last TrendLookback days (0.5 while history is short)
int hTrE = INVALID_HANDLE, hTrA = INVALID_HANDLE; datetime trDay = 0; double trScore = 0.5;
double TrendScore()
{
   datetime d = iTime(_Symbol, PERIOD_D1, 0);
   if(d == trDay) return trScore;
   if(hTrE == INVALID_HANDLE) hTrE = iMA(_Symbol, PERIOD_D1, TrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(hTrA == INVALID_HANDLE) hTrA = iATR(_Symbol, PERIOD_D1, 14);
   int n = TrendLookback;
   double e[], a[], c[];
   ArraySetAsSeries(e, true); ArraySetAsSeries(a, true); ArraySetAsSeries(c, true);
   if(CopyBuffer(hTrE, 0, 1, n, e) != n || CopyBuffer(hTrA, 0, 1, n, a) != n || CopyClose(_Symbol, PERIOD_D1, 1, n, c) != n)
      return 0.5;                                     // data not ready: neutral, try again next call
   double v0 = a[0] > 0 ? MathAbs(c[0] - e[0]) / a[0] : 0; int below = 0, cnt = 0;
   for(int k = 1; k < n; k++) if(a[k] > 0) { cnt++; if(MathAbs(c[k] - e[k]) / a[k] < v0) below++; }
   trScore = cnt > n / 2 ? (double)below / cnt : 0.5;
   trDay = d;
   return trScore;
}
// risk % for a new trade of this slot: MinRiskPercent .. MaxRiskPercent
double RiskPctNow(Slot &s)
{
   double mn = MathMin(MinRiskPercent, MaxRiskPercent), mx = MaxRiskPercent;
   if(g_prop.On())
     {
      //  the same market-driven shape, scaled down to the ceiling a challenge
      //  can carry: both ends move together, so x still means what it meant
      double ceil = g_prop.RiskCeilingPct(MaxTotalPositions);
      if(ceil < mx) { mn = mn * ceil / mx; mx = ceil; }
     }
   double x;
   if(RiskMode == RISK_FIXED_MAX)  x = 1.0;
   else if(RiskMode == RISK_DD)    x = DDScore();
   else if(RiskMode == RISK_EDGE)  x = EdgeScore(s);
   else if(RiskMode == RISK_DD_EDGE) x = DDScore() * (0.5 + 0.5 * EdgeScore(s));
   else                            x = DDScore() * (s.mr ? 1.0 - TrendScore() : TrendScore());   // fades get more risk when the trend is weak
   return (mn + (mx - mn) * x) * (s.mr ? MRRiskMult : 1.0);
}

//------------------------------------------------------------------ trading
double Lots(double stopDist, double riskPct, double regime = 1.0, bool stretchOk = true)
{
   double mn = g_acct.volMin;
   if(MaxRiskPercent <= 0) return MathMax(mn, FixedLots);
   double perLot = AcctLossPerLot(stopDist);  // money lost per 1.00 lot at this stop
   if(perLot <= 0) return 0;
   double eq     = AccountInfoDouble(ACCOUNT_EQUITY);
   //  equity and perLot are both in the account's own currency, so a cent
   //  account needs no correction here -- the scale cancels
   double lots   = AcctFloorLots(eq * riskPct / 100.0 / perLot);
   if(lots <= 0)
     {
      //  The risk model did not refuse this trade -- the size it asked for does
      //  not exist at the broker's lot step. Ask what the minimum lot actually
      //  costs and take it only if that is inside the ceiling already set.
      if(!MinLotStretch || !stretchOk || eq <= 0.0) return 0;
      //  no size left to say "less" with, so say "not now" instead
      if(MinLotRegimeGate && regime < 0.5) return 0;
      double costPct = mn * perLot / eq * 100.0;
      //  Measured against MaxRiskPercent, and it cannot usefully be measured
      //  against riskPct instead: reaching this branch means lots < mn, which
      //  means eq*riskPct/100/perLot < mn, which means riskPct < costPct
      //  already. A dial offering that comparison rejected every trade and was
      //  deleted rather than shipped. Risk is expressed through SIZE, and at
      //  the minimum lot there is no size left to express it with.
      double stretchCeil = g_prop.On() ? MathMin(MaxRiskPercent, g_prop.RiskCeilingPct(MaxTotalPositions)) : MaxRiskPercent;
      if(MinLotStretchMaxPct > 0) stretchCeil = MathMin(stretchCeil, MinLotStretchMaxPct);
      if(costPct > stretchCeil) return 0;      // genuinely unaffordable, skip as before
      return mn;
     }
   return lots;
}
// ---- per-position state (several positions per slot when pyramiding)
struct PState { ulong tk; int slot; int dir; double risk, lvl, entry, best, trailW, r1, lock, ratA; bool tp1Done; datetime openT; };
PState PS[]; int nPS = 0;
int FindPS(ulong tk) { for(int k = 0; k < nPS; k++) if(PS[k].tk == tk) return k; return -1; }
void DropClosed()
{
   for(int k = nPS - 1; k >= 0; k--)
      if(!PositionSelectByTicket(PS[k].tk)) { for(int j = k + 1; j < nPS; j++) PS[j - 1] = PS[j]; nPS--; }
}
int SlotPositions(Slot &s, int &dirOut, bool &allLocked)
{
   int c = 0; allLocked = true; dirOut = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong t = PositionGetTicket(k);
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != (long)s.magic) continue;
      int d = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1;
      double sl = PositionGetDouble(POSITION_SL), op = PositionGetDouble(POSITION_PRICE_OPEN);
      bool locked = sl > 0 && ((d == 1 && sl >= op) || (d == -1 && sl <= op));
      if(!locked) allLocked = false;
      if(dirOut != 0 && dirOut != d) allLocked = false;
      dirOut = d; c++;
   }
   return c;
}
// a new entry is allowed when the slot is flat, or (pyramiding) every open position is already risk-free in the same direction
bool CanEnter(Slot &s, int dir)
{
   //  the outcome run takes every signal: the book is not the question there
   if(JournalMode == 2) return true;
   int d; bool locked;
   int c = SlotPositions(s, d, locked);
   int total = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   { PositionGetTicket(k); long mg = PositionGetInteger(POSITION_MAGIC); if(PositionGetString(POSITION_SYMBOL) == _Symbol && mg >= (long)MagicBase && mg < (long)MagicBase + NS) total++; }
   if(total >= MaxTotalPositions) return false;
   if(c == 0) return true;
   return c < MaxPositions && locked && d == dir;
}
void Open(Slot &s, int slotIdx, int dir, double lvl, double atr)
{
   double k = MathMax(s.mr ? 0.3 : K_MIN, MathMin(K_MAX, SigQuantile(s, 0, s.qsl, 2.0)));
   double risk = k * atr;
   //  a pyramid add -- the slot already holds positions, all risk-free. It is
   //  SIZED as a first entry (risk), but its stop sits PyrRiskMult as far
   //  (stopDist): it came in higher, so it gets less room and risks less.
   int pyD; bool pyLk;
   bool pyAdd = MaxPositions > 1 && SlotPositions(s, pyD, pyLk) > 0;
   double stopDist = pyAdd ? risk * PyrRiskMult : risk;
   double r1 = 0;
   if(s.qtp > 0) r1 = MathMax(R1_MIN, MathMin(s.mr ? 5.0 : R1_MAX, SigQuantile(s, 1, s.qtp, 1.0) / k));
   double ratA = (ProfitRatchet && !s.mr) ? SigQuantile(s, 1, RatchetQ, 0) / k : 0;   // "big" profit in R, 0 = not enough history
   //  the slot's exit scale (KM, RM, TM in its spec -- A64/A65). Stop, first
   //  target and trail stay measured from the market; only their size moves.
   //  Applied after r1 is measured, so the first target keeps its R.
   k *= s.km; risk = k * atr; stopDist = pyAdd ? risk * PyrRiskMult : risk;
   r1 *= s.rm;
   double tw = s.qtr > 0 ? TrailQuantile(s.qtr) * B(hA[TI(PERIOD_H4)], 1) : 0;
   if(UseDXY && tw > 0)
   {
      int usd = UsdDailyDir();
      if(usd != 0 && usd == dir) tw *= DXYAgainstTrail;     // USD rising vs gold long (or falling vs short) -> protect profit sooner
   }
   tw *= s.tm;
   s.kNow = k; s.r1Now = r1; s.trNow = tw;
   //  in PRICE: 80 points was $0.80 on a 2-digit feed and $0.08 on a 3-digit one
   //  the outcome run (JournalMode 2) skips every gate and sizes at JournalLots
   double lots = JournalLots;
   if(JournalMode != 2)
   {
   double sprNow = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(sprNow > MaxSpreadPrice + g_acct.point * 0.5)
     { Why(slotIdx, StringFormat("skipped: spread $%.2f > $%.2f", sprNow, MaxSpreadPrice)); return; }
   if(DrawdownStopActive()) { Why(slotIdx, "skipped: drawdown pause"); Print("Drawdown stop active: equity is more than ", MaxDrawdownStopPercent, "% below its peak - no new trades"); return; }
   string pwhy = "";
   if(!g_prop.CanOpen(pwhy)) { Why(slotIdx, "skipped: " + pwhy); return; }
   if(DailyLossStopPct > 0 && DayLossStopHit()) { Why(slotIdx, "skipped: daily loss limit"); return; }
   if(NewsShield && NewsBlocked(TimeCurrent(), NewsBeforeMin, NewsAfterMin, NewsCurrencies))
     { g_newsBlocks++; Why(slotIdx, "skipped: news in the window"); return; }
   double riskPct = RiskPctNow(s);
   s.riskNow = riskPct;
   //  the same regime score RiskPctNow multiplies into x -- a fade slot reads
   //  the trend inverted, because it wants the half of the market the trend
   //  slots do not.
   double regime = (RiskMode == RISK_DD_TREND)
                   ? (s.mr ? 1.0 - TrendScore() : TrendScore()) : 1.0;
   lots = Lots(risk, riskPct, regime, !s.mr || MinLotStretchFades);
   if(lots > 0 && MaxRiskPercent > 0)
   {
      // shrink (or skip) the trade so the summed open risk stays under MaxOpenRiskPercent
      double room = MaxOpenRiskPercent - OpenRiskPercent();
      double thisRisk = risk * MoneyPerPriceUnit(lots) / AccountInfoDouble(ACCOUNT_EQUITY) * 100.0;
      if(room <= 0) lots = 0;
      else if(thisRisk > room)
         lots = AcctFloorLots(lots * room / thisRisk);
      if(lots <= 0) { Why(slotIdx, "skipped: open-risk cap"); Print("Slot ", slotIdx + 1, ": open-risk cap ", MaxOpenRiskPercent, "% reached - skipped"); return; }
   }
   if(lots <= 0) { Why(slotIdx, StringFormat("skipped: $%.2f stop too wide for %.2f%%", risk, riskPct)); Print("Slot ", slotIdx + 1, ": stop $", DoubleToString(risk, 2), " too wide for risk " + DoubleToString(riskPct, 2) + "% - skipped"); return; }
   if(g_prop.On())
     {
      //  BREACH-PROOF SIZING. Assume every open position AND this one are all
      //  stopped out together. Equity must still clear the nearest floor, or
      //  the trade is shrunk until it does, or it is not opened at all.
      double worst = WorstCaseEquity();
      if(worst == -DBL_MAX)
        { Why(slotIdx, "skipped: a position has no stop"); Print("Slot ", slotIdx + 1, ": a position on this account has no stop -- prop mode opens nothing until it does"); return; }
      double room = g_prop.RoomFromWorst(worst);
      //  the new trade's loss is measured from the side of the book it will
      //  fill on, not from the signal bar's close: after a gap the difference
      //  can be most of the stop
      double fillPx = dir > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double stopPx = lvl - dir * risk;
      double perLot = AcctLossPerLot(MathMax(risk, (fillPx - stopPx) * dir));
      double fitProp = (room > 0 && perLot > 0) ? AcctFloorLots(room / perLot) : 0;
      if(fitProp <= 0)
        { Why(slotIdx, "skipped: prop room too small"); Print("Slot ", slotIdx + 1, ": prop room ", DoubleToString(room, 2), " cannot carry even the minimum lot - skipped"); return; }
      if(fitProp < lots)
        { Print("Slot ", slotIdx + 1, ": prop room caps ", DoubleToString(lots, 2), " to ", DoubleToString(fitProp, 2), " lots"); lots = fitProp; }
     }
   //  the broker has to be able to carry it: at 1:30 on a prop account ten
   //  positions can run out of margin, and an order the broker refuses for
   //  "not enough money" would otherwise vanish with no record of why
   double fit = AcctFitMargin(dir, lots);
   if(fit <= 0) { Why(slotIdx, "skipped: not enough margin"); Print("Slot ", slotIdx + 1, ": not enough free margin for ", DoubleToString(lots, 2), " lots - skipped"); return; }
   if(fit < lots) { Print("Slot ", slotIdx + 1, ": margin allows ", DoubleToString(fit, 2), " of ", DoubleToString(lots, 2), " lots"); lots = fit; }
   }
   trade.SetExpertMagicNumber(s.magic);
   double sl = NormalizeDouble(lvl - dir * stopDist, _Digits);
   double tp = s.mr && r1 > 0 ? NormalizeDouble(lvl + dir * r1 * risk, _Digits)
             : (pyAdd && PyrBookAtTp1 && r1 > 0 ? NormalizeDouble(lvl + dir * r1 * stopDist, _Digits) : 0);   // fades: whole position at the target
   //  the order comment names the strategy, so the trader's own history does
   string cmt = "Assay " + (s.mr ? "F" : "S") + IntegerToString(slotIdx + 1);
   bool ok = dir == 1 ? trade.Buy(lots, _Symbol, 0, sl, tp, cmt) : trade.Sell(lots, _Symbol, 0, sl, tp, cmt);
   if(!(ok && trade.ResultRetcode() == TRADE_RETCODE_DONE))
      Why(slotIdx, StringFormat("broker refused (%u)", trade.ResultRetcode()));
   if(ok && trade.ResultRetcode() == TRADE_RETCODE_DONE)
   {
      Why(slotIdx, StringFormat("opened %s %.2f", dir > 0 ? "BUY" : "SELL", lots));
      g_jTk = trade.ResultOrder();
      ArrayResize(PS, nPS + 1);
      PS[nPS].tk = trade.ResultOrder(); PS[nPS].slot = slotIdx; PS[nPS].dir = dir; PS[nPS].risk = stopDist; PS[nPS].lvl = lvl;
      PS[nPS].entry = trade.ResultPrice(); PS[nPS].best = trade.ResultPrice(); PS[nPS].trailW = tw; PS[nPS].r1 = r1;
      PS[nPS].lock = s.lock; PS[nPS].ratA = ratA; PS[nPS].tp1Done = (r1 <= 0) || s.mr || (pyAdd && PyrBookAtTp1); PS[nPS].openT = TimeCurrent();
      nPS++;
      g_prop.OnTradeOpened();
   }
}
void ManagePosition(Slot &s, int slotIdx, ulong tk, bool newH4)
{
   if(!PositionSelectByTicket(tk)) return;
   int dir = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1;
   double vol = PositionGetDouble(POSITION_VOLUME), sl = PositionGetDouble(POSITION_SL);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), px = dir == 1 ? bid : ask;
   int i = FindPS(tk);
   if(i < 0)
   {
      // EA (re)started with this position already open: rebuild its state from the position itself
      double op = PositionGetDouble(POSITION_PRICE_OPEN);
      if(sl <= 0) return;
      ArrayResize(PS, nPS + 1); i = nPS++;
      PS[i].tk = tk; PS[i].slot = slotIdx; PS[i].dir = dir; PS[i].entry = op; PS[i].lvl = op; PS[i].risk = MathAbs(op - sl);
      PS[i].best = dir == 1 ? MathMax(op, px) : MathMin(op, px); PS[i].r1 = 0; PS[i].lock = s.lock;
      double km0 = MathMax(s.mr ? 0.3 : K_MIN, MathMin(K_MAX, SigQuantile(s, 0, s.qsl, 2.0)));
      PS[i].ratA = (ProfitRatchet && !s.mr && PS[i].risk > 0) ? SigQuantile(s, 1, RatchetQ, 0) / km0 : 0;
      PS[i].tp1Done = true;                                  // partial state unknown -> never partial-close again (fades keep their broker TP)
      PS[i].trailW = s.qtr > 0 ? TrailQuantile(s.qtr) * B(hA[TI(PERIOD_H4)], 1) * s.tm : 0;
      PS[i].openT = (datetime)PositionGetInteger(POSITION_TIME);
   }
   PS[i].best = dir == 1 ? MathMax(PS[i].best, px) : MathMin(PS[i].best, px);
   trade.SetExpertMagicNumber(s.magic);
   double nsl = sl;
   if(!PS[i].tp1Done && PS[i].risk > 0 && (px - PS[i].lvl) * dir >= PS[i].r1 * PS[i].risk)
   {
      double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double frac = TP1FractionOverride >= 0 ? TP1FractionOverride : s.f1;
      double part = MathFloor(vol * frac / step) * step;
      bool   took = (part >= vmin && part < vol);
      if(took) trade.PositionClosePartial(tk, part);
      //  A partial that was asked for and could not be taken: the position is
      //  already the minimum lot, so there is nothing to split. The old code
      //  still marked TP1 done and dragged the stop to entry + lock*R, which
      //  turned every small-account trade into a scratch -- the largest win of
      //  the whole 2025 $500 year was $6.53 against $25,436 at $16,000.
      //
      //  `wanted` is what keeps this away from slots 1, 2 and 4: they ship
      //  F1 = 0, where locking the stop is the documented mechanism and not a
      //  consolation for a failed partial.
      bool wanted = (frac > 0.0);
      if(wanted && !took && MinLotTp1Mode == 2)
        {
         trade.PositionClose(tk);
         PS[i].tp1Done = true;
         return;
        }
      PS[i].tp1Done = true;
      if(!(wanted && !took && MinLotTp1Mode == 1))
        {
         double lk = PS[i].entry + dir * PS[i].lock * PS[i].risk;
         if((dir == 1 && lk > nsl) || (dir == -1 && lk < nsl)) nsl = lk;
        }
   }
   if(newH4 && PS[i].trailW > 0)
   {
      double ns = PS[i].best - dir * PS[i].trailW;
      if((dir == 1 && ns > nsl) || (dir == -1 && ns < nsl)) nsl = ns;
   }
   if(PS[i].ratA > 0 && PS[i].risk > 0 && (PS[i].best - PS[i].entry) * dir >= PS[i].ratA * PS[i].risk)
   {
      double rs = PS[i].entry + dir * RatchetKeep * (PS[i].best - PS[i].entry);
      //  move only in steps of a tenth of R, so a running spike is not a stream of modify requests
      if((dir == 1 && rs > nsl + 0.1 * PS[i].risk) || (dir == -1 && rs < nsl - 0.1 * PS[i].risk)) nsl = rs;
   }
   if(TimeCurrent() - PS[i].openT > MaxHoldDays * 86400) { trade.PositionClose(tk); return; }
   if(s.mr && TimeCurrent() - PS[i].openT >= s.horizon * 60) { trade.PositionClose(tk); return; }   // fade did not work in time
   if(MathAbs(nsl - sl) > _Point)
   {
      //  the freeze level as well as the stops level: inside it the broker
      //  refuses any modification, and most publish 0 but not all
      double lvl = MathMax(g_acct.stopsLevelPts, g_acct.freezeLevelPts) * g_acct.point;
      if((dir == 1 && nsl < bid - lvl) || (dir == -1 && nsl > ask + lvl)) trade.PositionModify(tk, NormalizeDouble(nsl, _Digits), PositionGetDouble(POSITION_TP));
   }
}
void Manage(Slot &s, int slotIdx, bool newH4)
{
   ulong tks[]; int n = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong t = PositionGetTicket(k);
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == (long)s.magic)
      { ArrayResize(tks, n + 1); tks[n++] = t; }
   }
   for(int k = 0; k < n; k++) ManagePosition(s, slotIdx, tks[k], newH4);
}

//------------------------------------------------------------------ setup
ENUM_TIMEFRAMES ParseTF(string v)
{
   if(v == "M1") return PERIOD_M1; if(v == "M3") return PERIOD_M3; if(v == "M5") return PERIOD_M5; if(v == "M15") return PERIOD_M15;
   if(v == "M30") return PERIOD_M30; if(v == "H1") return PERIOD_H1; if(v == "H4") return PERIOD_H4; if(v == "D1") return PERIOD_D1;
   return PERIOD_CURRENT;
}
string SpecGet(string spec, string key, string def)
{
   string parts[]; int n = StringSplit(spec, ';', parts);
   for(int k = 0; k < n; k++)
   {
      string kv[]; if(StringSplit(parts[k], '=', kv) != 2) continue;
      StringTrimLeft(kv[0]); StringTrimRight(kv[0]); StringTrimLeft(kv[1]); StringTrimRight(kv[1]);
      StringToUpper(kv[0]);
      if(kv[0] == key) { string v = kv[1]; StringToUpper(v); return v; }
   }
   return def;
}
void Load(int k, string spec)
{
   string sp = spec; StringTrimLeft(sp); StringTrimRight(sp); string up = sp; StringToUpper(up);
   S[k].on = !(up == "" || up == "OFF" || StringFind(up, "OFF;") == 0);   // "OFF;..." keeps the spec but disables the slot
   S[k].magic = MagicBase + k; S[k].nsig = 0; S[k].lastBar = 0; S[k].kNow = 0; S[k].r1Now = 0; S[k].trNow = 0; S[k].riskNow = 0;
   ArrayResize(S[k].sigs, 0);
   if(!S[k].on) return;
   S[k].tf = ParseTF(SpecGet(sp, "TF", "M15"));
   string e = SpecGet(sp, "ENTRY", "PB");
   S[k].entry = e == "RSI2" ? E_RSI2 : e == "BRK" ? E_BRK : e == "RSIF" ? E_RSIF : e == "ZF" ? E_ZF : e == "FBO" ? E_FBO : E_PB;
   S[k].mr = S[k].entry >= E_RSIF;
   S[k].zTh = StringToDouble(SpecGet(sp, "Z", "2"));
   S[k].reg = SpecGet(sp, "REG", "ANY") == "NO4H" ? 1 : 0;
   S[k].pb = (int)StringToInteger(SpecGet(sp, "EMA", "30"));
   S[k].rsiTh = (int)StringToInteger(SpecGet(sp, "RSI", S[k].mr ? "5" : "10"));
   S[k].brkN = (int)StringToInteger(SpecGet(sp, "BRKN", "20"));
   string c1 = SpecGet(sp, "CONF1", "NONE"), c2 = SpecGet(sp, "CONF2", "NONE");
   S[k].c1 = c1 == "NONE" ? PERIOD_CURRENT : ParseTF(c1);
   S[k].c2 = c2 == "NONE" ? PERIOD_CURRENT : ParseTF(c2);
   S[k].adx = SpecGet(sp, "ADX", "ANY") == "LT30" ? ADX_LT30 : ADX_ANY;
   S[k].sess = SpecGet(sp, "SESS", "1") == "1";
   int defHor = S[k].tf <= PERIOD_M3 ? 720 : (S[k].tf <= PERIOD_M15 ? 1440 : (S[k].tf <= PERIOD_M30 ? 2880 : 4320));
   S[k].horizon = (int)StringToInteger(SpecGet(sp, "HOR", IntegerToString(defHor)));
   S[k].look = (int)StringToInteger(SpecGet(sp, "LOOK", "60"));
   S[k].qsl = StringToDouble(SpecGet(sp, "QSL", "0.5"));
   S[k].qtp = StringToDouble(SpecGet(sp, "QTP", "0.3"));
   S[k].lock = StringToDouble(SpecGet(sp, "LOCK", "0.25"));
   S[k].qtr = S[k].mr ? 0 : StringToDouble(SpecGet(sp, "QTR", "0.8"));
   S[k].f1 = S[k].mr ? 1 : StringToDouble(SpecGet(sp, "F1", "0.5"));
   S[k].km = StringToDouble(SpecGet(sp, "KM", "1"));
   S[k].rm = StringToDouble(SpecGet(sp, "RM", "1"));
   S[k].tm = StringToDouble(SpecGet(sp, "TM", "1"));
   TI(S[k].tf); TI(PERIOD_H4); TI(PERIOD_D1);
   if(S[k].c1 != PERIOD_CURRENT) TI(S[k].c1);
   if(S[k].c2 != PERIOD_CURRENT) TI(S[k].c2);
   PrintFormat("Slot %d: %s", k + 1, sp);
}
void Backfill(Slot &s)
{
   // scan from the newest closed bar backwards and stop once enough signals are collected (fast start, same calibration)
   int n = (int)MathMin((double)BackfillDays * 86400.0 / PeriodSeconds(s.tf), (double)(Bars(_Symbol, s.tf) - 80));
   int need = MathMin(MAX_SIGS, s.look * 3);
   datetime tT[]; int tD[]; double tL[], tA[]; int c = 0;
   ArrayResize(tT, need); ArrayResize(tD, need); ArrayResize(tL, need); ArrayResize(tA, need);
   for(int sh = 2; sh <= n && c < need; sh++)
   {
      int d = SignalAt(s, sh);
      if(d == 0) continue;
      double atr = B(hA[TI(s.tf)], sh);
      if(atr == EMPTY_VALUE || atr <= 0) continue;
      tT[c] = iTime(_Symbol, s.tf, sh) + PeriodSeconds(s.tf); tD[c] = d; tL[c] = iClose(_Symbol, s.tf, sh); tA[c] = atr; c++;
   }
   for(int k = c - 1; k >= 0; k--) AddSig(s, tT[k], tD[k], tL[k], tA[k]);   // oldest first
   Resolve(s, TimeCurrent());
   PrintFormat("Slot %d (%s): %d historical signals calibrated", (int)(s.magic - MagicBase + 1), EnumToString(s.tf), s.nsig);
}
//  DXY: find the six pairs by this broker's names and make sure their daily
//  history is actually there. In a backtest it is decided ONCE, at init, so a
//  run cannot change behaviour halfway because a pair's history arrived late --
//  exactly what happened to the early research runs. Live, it is retried on
//  every new H4 bar until it succeeds, so a terminal that had not synchronised
//  FX history at start-up is not left without DXY for the whole session.
void DxyTry(const bool first)
{
   if(!UseDXY || DXYSymbol != "" || g_dxyLive) return;
   if(!first && MQLInfoInteger(MQL_TESTER)) return;
   string p[6] = {"EUR", "USD", "GBP", "USD", "USD", "USD"};
   string q[6] = {"USD", "JPY", "USD", "CAD", "SEK", "CHF"};
   string missing = "";
   for(int k = 0; k < 6; k++)
   {
      g_fx[k] = AcctFx(p[k], q[k], g_fxInv[k]);
      double c[];
      if(g_fx[k] == "" || CopyClose(g_fx[k], PERIOD_D1, 1, 170, c) < 170)
      { missing = p[k] + q[k] + (g_fx[k] == "" ? " is not offered by this broker" : " (" + g_fx[k] + ") has too little daily history"); break; }
   }
   if(missing == "")
   {
      g_dxyLive = true;
      string names = "";
      for(int k = 0; k < 6; k++) names += g_fx[k] + (g_fxInv[k] ? "(inv)" : "") + " ";
      Print("Assay: DXY from ", names);
      return;
   }
   //  the pairs could not all be found: a native dollar index says the same
   //  thing about the dollar's direction, so use one if the broker has it
   string idx = AcctDollarIndex();
   double ci[];
   if(idx != "" && CopyClose(idx, PERIOD_D1, 1, 170, ci) >= 170)
   {
      g_dxyNative = idx;
      g_dxyLive = true;
      Print("Assay: DXY from the broker's own index ", idx, " -- ", missing);
      return;
   }
   if(first) Print("Assay: DXY off for now -- ", missing, ", and no dollar index was found");
}

int OnInit()
{
   ready = false;
   //  the ribbons, ADX, RSI and ATR keep working; the tester just does not
   //  draw eight lines and three sub-windows over the chart
   TesterHideIndicators(true);
   if(PropMode)
     {
      //  the firm's numbers cannot be guessed: a size taken from the balance at
      //  attach put the floor $2,640 past a real firm's on a challenge that was
      //  already down, and a limit at or below the buffer halts on every tick
      if(PropAccountSize <= 0)
        { Print("Assay prop: set the account size to your challenge's size (for example 100000)."); return INIT_PARAMETERS_INCORRECT; }
      if(PropDailyLossPct <= PropBufferPct || PropMaxLossPct <= PropBufferPct)
        { Print("Assay prop: the daily and maximum loss limits must both be larger than the safety buffer."); return INIT_PARAMETERS_INCORRECT; }
     }
   string why = "";
   if(!AcctInit(_Symbol, why)) { Print("Assay cannot start: ", why); return INIT_FAILED; }
   Print("Assay account: ", AcctSummary());
   if(!g_acct.hedging)
     {
      //  eleven slots, each holding its own position, cannot exist on an
      //  account that merges every position on a symbol into one
      Print("Assay needs a HEDGING account. This one is netting, so every slot's position "
            "would be merged into one and managed by eleven different rules. Not trading.");
      return INIT_FAILED;
     }
   AcctSetupTrade(trade, 0.30);
   if(NewsShield) NewsInit(NewsCurrencies);
   g_prop.Init(PropMode, PropDailyLossPct, PropMaxLossPct, PropTrailing, PropTargetPct, PropReset,
               PropBufferPct, PropMinDays, PropDayOfInitial, PropAccountSize, MagicBase);
   //  the panel lives on a real or visual chart only: in a non-visual backtest
   //  there is no one to look at it, and drawing it would only cost time
   g_dashOn = ShowPanel && (!MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_VISUAL_MODE));
   //  styled before the panel starts: the panel takes its theme from the chart
   if(g_dashOn) CsApply();
   //  the chart layer before the panel: objects created later are drawn on
   //  top, and the panel must sit above the layer's labels
   if(g_dashOn)
     {
      OvClear();                // the object overlay of earlier builds
      g_layerOn = g_layer.Init("ASSAY_LAYER", PropServerOffset(TimeCurrent()));
      g_layer.Currency(g_acct.dispCur);
     }
   if(g_dashOn && !g_dash.Init("ASSAY_PANEL", true)) { Print("Assay: dashboard could not start"); g_dashOn = false; }
   JInit(JournalMode, JournalTag);
   VetoParse();
   DxyTry(true);
   Load(0, Slot1); Load(1, Slot2); Load(2, Slot3); Load(3, Slot4); Load(4, Slot5); Load(5, Slot6); Load(6, Slot7);
   Load(7, Slot8); Load(8, Slot9); Load(9, Slot10); Load(10, Slot11);
   EventSetTimer(5);          // indicators need a moment to build before the backfill
   return INIT_SUCCEEDED;
}
#include <Assay/Feed.mqh>
#include <Assay/LayerFeed.mqh>
void OnTimer()
{
   if(!ready)
   {
      for(int k = 0; k < NS; k++) if(S[k].on) Backfill(S[k]);
      UpdateEpisodes();
      ready = true;
      //  the timer only outlives the backfill when there is a panel to draw
      if(!g_dashOn) EventKillTimer(); else EventSetTimer(1);
   }
   if(g_dashOn)
   {
      g_peakFrozen = true;
      DashTick();
      g_peakFrozen = false;
   }
   //  live: keeps the chart current between ticks (the tester redraws per tick)
   if(!MQLInfoInteger(MQL_TESTER)) LayerTick();
}
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(g_layerOn && id == CHARTEVENT_CHART_CHANGE) LayerTick();
   if(g_dashOn && g_dash.OnEvent(id, lparam, dparam, sparam))
   {
      g_peakFrozen = true;
      DashTick(true);
      g_peakFrozen = false;
   }
}
void OnDeinit(const int r) { JClose(); if(r == REASON_REMOVE || r == REASON_CHARTCLOSE || r == REASON_TEMPLATE) CsRestore(); if(NewsShield) PrintFormat("Assay news: %d entries refused around releases", g_newsBlocks); EventKillTimer(); Comment(""); if(g_dashOn) g_dash.Shutdown(); if(g_layerOn) g_layer.Shutdown(); if(hTrE != INVALID_HANDLE) IndicatorRelease(hTrE); if(hTrA != INVALID_HANDLE) IndicatorRelease(hTrA); }

//  Seconds from `now` to the end of this broker's last gold session of the
//  week, read from the symbol's own session table. -1 when it is not Friday or
//  the broker publishes no Friday session.
long SecondsToWeekClose(const datetime now)
{
   MqlDateTime d; TimeToStruct(now, d);
   if(d.day_of_week != FRIDAY) return -1;
   datetime from = 0, to = 0, last = 0;
   for(uint i = 0; i < 16; i++)
   {
      if(!SymbolInfoSessionTrade(_Symbol, FRIDAY, i, from, to)) break;
      if(to > last) last = to;
   }
   if(last == 0) return -1;
   //  session times are offsets from 00:00; 24:00 comes back as a whole day
   long endSec = (long)last % 86400;
   if(endSec == 0) endSec = 86400;
   long nowSec = d.hour * 3600 + d.min * 60 + d.sec;
   return endSec - nowSec;
}

bool NearWeekClose(const datetime now)
{
   if(!g_prop.On() || !PropFlatWeekend) return false;
   long s = SecondsToWeekClose(now);
   return s >= 0 && s <= (long)WeekendCloseMins * 60;
}

//  The retail daily stop. The day's starting balance is rebuilt from deal
//  history at the first check of each server day -- right even if the EA was
//  off at midnight -- and cached for the rest of the day.
long   g_dlsDay = 0;
double g_dlsStart = 0;
bool DayLossStopHit()
{
   MqlDateTime d; TimeToStruct(TimeCurrent(), d);
   long key = (long)d.year * 1000 + d.day_of_year;
   if(key != g_dlsDay)
   {
      d.hour = 0; d.min = 0; d.sec = 0;
      datetime t = StructToTime(d);
      double bal = AccountInfoDouble(ACCOUNT_BALANCE), since = 0;
      if(HistorySelect(t, TimeCurrent() + 86400))
         for(int i = 0; i < HistoryDealsTotal(); i++)
         {
            ulong tk = HistoryDealGetTicket(i);
            if(tk == 0 || (datetime)HistoryDealGetInteger(tk, DEAL_TIME) < t) continue;
            since += HistoryDealGetDouble(tk, DEAL_PROFIT) + HistoryDealGetDouble(tk, DEAL_COMMISSION)
                     + HistoryDealGetDouble(tk, DEAL_SWAP) + HistoryDealGetDouble(tk, DEAL_FEE);
         }
      g_dlsStart = bal - since;
      g_dlsDay = key;
   }
   return g_dlsStart > 0 && AccountInfoDouble(ACCOUNT_EQUITY) <= g_dlsStart * (1.0 - DailyLossStopPct / 100.0);
}

//  Equity if every position on the ACCOUNT were stopped out now: balance, plus
//  each position's result at its stop, plus its swap. Locked profit counts as
//  locked -- the float above a stop in profit is given back when it is hit,
//  which the first prop check ignored. Positions of other EAs and manual ones
//  count too, because the firm's limit is on the account. A position with no
//  stop makes the worst case unbounded: returns -DBL_MAX.
double WorstCaseEquity()
{
   double w = AccountInfoDouble(ACCOUNT_BALANCE);
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      if(PositionGetTicket(k) == 0) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      double sl = PositionGetDouble(POSITION_SL);
      if(sl <= 0) return -DBL_MAX;
      double op = PositionGetDouble(POSITION_PRICE_OPEN), v = PositionGetDouble(POSITION_VOLUME);
      int d = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1;
      double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
      double move = (sl - op) * d;
      double tv = SymbolInfoDouble(sym, move < 0 ? SYMBOL_TRADE_TICK_VALUE_LOSS : SYMBOL_TRADE_TICK_VALUE_PROFIT);
      if(tv <= 0) tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
      if(ts <= 0 || tv <= 0) return -DBL_MAX;
      w += move / ts * tv * v + PositionGetDouble(POSITION_SWAP);
   }
   return w;
}

//  What flattening this EA's book would cost right now: the spread on each.
double CloseCostEA()
{
   double c = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      if(PositionGetTicket(k) == 0) continue;
      long mg = PositionGetInteger(POSITION_MAGIC);
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || mg < (long)MagicBase || mg >= (long)MagicBase + NS) continue;
      double spr = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
      c += AcctLossPerLot(spr) * PositionGetDouble(POSITION_VOLUME);
   }
   return c;
}

int EAPositionCount()
{
   int n = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      if(PositionGetTicket(k) == 0) continue;
      long mg = PositionGetInteger(POSITION_MAGIC);
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && mg >= (long)MagicBase && mg < (long)MagicBase + NS) n++;
   }
   return n;
}

//  Close every position this EA owns. Used by the prop guardian; retried on
//  every tick while it is halted, because a close can fail and a guardian
//  that reports itself flat while a position survives is worse than none.
void CloseAllEA(const string why)
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong t = PositionGetTicket(k);
      if(t == 0) continue;
      long mg = PositionGetInteger(POSITION_MAGIC);
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || mg < (long)MagicBase || mg >= (long)MagicBase + NS) continue;
      trade.SetExpertMagicNumber((ulong)mg);
      if(!trade.PositionClose(t))
         PrintFormat("Assay %s: close of #%I64u failed (%u) -- retrying next tick", why, t, trade.ResultRetcode());
   }
}

//  research journal: one row per signal -- the market at the signal bar's
//  close and what the EA did with it. Reads only; changes nothing.
void JSignal(Slot &s, int k, datetime b, int dir, double lvl, double atr)
{
   int i = TI(s.tf), i4 = TI(PERIOD_H4), iD = TI(PERIOD_D1);
   double adx = B(hX[i], 1), rsi = B(hR[i], 1), a4 = B(hA[i4], 1), aD = B(hA[iD], 1);
   double e30 = B(hE[0][i], 1), e60 = B(hE[5][i], 1);
   double o = iOpen(_Symbol, s.tf, 1), h = iHigh(_Symbol, s.tf, 1), l = iLow(_Symbol, s.tf, 1), c = iClose(_Symbol, s.tf, 1);
   double dh = iHigh(_Symbol, PERIOD_D1, 0), dl = iLow(_Symbol, PERIOD_D1, 0);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   int nEA = 0, nSlot = 0;
   for(int q = PositionsTotal() - 1; q >= 0; q--)
   {
      if(PositionGetTicket(q) == 0) continue;
      long mg = PositionGetInteger(POSITION_MAGIC);
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || mg < (long)MagicBase || mg >= (long)MagicBase + NS) continue;
      nEA++; if(mg == (long)s.magic) nSlot++;
   }
   int n24 = 0;
   for(int q = s.nsig - 1; q >= 0 && s.sigs[q].t > b - 86400; q--) n24++;
   string why = g_why[k]; StringReplace(why, ",", ";");
   double u = atr > 0 ? atr : 1;
   JRow(StringFormat("%d,%I64d,%d,%.3f,%.4f,%.4f,%.4f,%.4f,%.3f,%I64u,%s,"
        "%.2f,%.2f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,"
        "%.3f,%.4f,%.4f,%d,%d,%d,%d,%d,%.3f,%.3f,%d,%d",
        k + 1, (long)b, dir, lvl, atr, s.kNow, s.r1Now, s.trNow, s.riskNow, g_jTk, why,
        adx, rsi, a4, aD, (lvl - e30) / u, (e30 - e60) / u, (h - l) / u, h > l ? (c - o) / (h - l) : 0.0,
        aD > 0 ? (dh - dl) / aD : 0.0, dh > dl ? (c - dl) / (dh - dl) : 0.5,
        SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID),
        TrendScore(), g_peak > 0 ? 1.0 - eq / g_peak : 0.0, UsdDailyDir(), nEA, nSlot, StackAt(PERIOD_H4, 1), n24,
        s.lock, TP1FractionOverride >= 0 ? TP1FractionOverride : s.f1, s.mr ? 1 : 0, s.horizon));
}

//  research veto: skip a slot's signal in a named market condition. The
//  features are the journal's, signed by the trade's direction.
string g_vFeat[]; int g_vSlot[]; int g_vOp[]; double g_vVal[]; int g_vN = 0;
void VetoParse(void)
{
   g_vN = 0;
   string rules[]; int n = StringSplit(SlotVeto, ';', rules);
   for(int i = 0; i < n; i++)
   {
      string r = rules[i]; StringTrimLeft(r); StringTrimRight(r);
      int c = StringFind(r, ":"); if(c < 1) continue;
      string sl = StringSubstr(r, 0, c), body = StringSubstr(r, c + 1);
      int p = StringFind(body, "<"), op = -1;
      if(p < 0) { p = StringFind(body, ">"); op = 1; }
      if(p < 0) { p = StringFind(body, "~"); op = 0; }   // equality; "=" would break the .set line
      if(p < 1) continue;
      int slot = sl == "*" ? -1 : (int)StringToInteger(StringSubstr(sl, 1)) - 1;
      ArrayResize(g_vFeat, g_vN + 1); ArrayResize(g_vSlot, g_vN + 1); ArrayResize(g_vOp, g_vN + 1); ArrayResize(g_vVal, g_vN + 1);
      g_vFeat[g_vN] = StringSubstr(body, 0, p); g_vSlot[g_vN] = slot; g_vOp[g_vN] = op;
      g_vVal[g_vN] = StringToDouble(StringSubstr(body, p + 1));
      PrintFormat("Assay veto: slot %s  %s %s %.4f", sl, g_vFeat[g_vN], op > 0 ? ">" : op < 0 ? "<" : "~", g_vVal[g_vN]);
      g_vN++;
   }
}
double Feat(Slot &s, const string f, datetime b, int dir, double lvl, double atr)
{
   int i = TI(s.tf);
   double u = atr > 0 ? atr : 1;
   if(f == "adx") return B(hX[i], 1);
   if(f == "rsi_with") { double r = B(hR[i], 1); return dir > 0 ? r : 100 - r; }
   if(f == "atr") return atr;
   if(f == "atr_ratio") { double a4 = B(hA[TI(PERIOD_H4)], 1); return a4 > 0 ? atr / a4 : 0; }
   if(f == "atr_d1") return B(hA[TI(PERIOD_D1)], 1);
   if(f == "ema30_with") return (lvl - B(hE[0][i], 1)) / u * dir;
   if(f == "ribbon_with") return (B(hE[0][i], 1) - B(hE[5][i], 1)) / u * dir;
   if(f == "bar_rng") return (iHigh(_Symbol, s.tf, 1) - iLow(_Symbol, s.tf, 1)) / u;
   if(f == "body_with") { double h = iHigh(_Symbol, s.tf, 1), l = iLow(_Symbol, s.tf, 1); return h > l ? (iClose(_Symbol, s.tf, 1) - iOpen(_Symbol, s.tf, 1)) / (h - l) * dir : 0; }
   double dh = iHigh(_Symbol, PERIOD_D1, 0), dl = iLow(_Symbol, PERIOD_D1, 0);
   if(f == "d1_rng") { double aD = B(hA[TI(PERIOD_D1)], 1); return aD > 0 ? (dh - dl) / aD : 0; }
   if(f == "d1_pos_with") { double ps = dh > dl ? (iClose(_Symbol, s.tf, 1) - dl) / (dh - dl) : 0.5; return dir > 0 ? ps : 1 - ps; }
   if(f == "spread") return SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(f == "trend") return TrendScore();
   if(f == "sig_24h") { int n = 0; for(int q = s.nsig - 1; q >= 0 && s.sigs[q].t > b - 86400; q--) n++; return n; }
   MqlDateTime t; TimeToStruct(b - PropServerOffset(b) * 3600, t);
   if(f == "hour") return t.hour;
   if(f == "wday") return t.day_of_week;
   if(f == "usd_with") return UsdDailyDir() * dir;
   if(f == "h4_with") return StackAt(PERIOD_H4, 1) * dir;
   return 0;
}
bool Vetoed(Slot &s, int k, datetime b, int dir, double lvl, double atr)
{
   for(int i = 0; i < g_vN; i++)
   {
      if(g_vSlot[i] != -1 && g_vSlot[i] != k) continue;
      double v = Feat(s, g_vFeat[i], b, dir, lvl, atr);
      if((g_vOp[i] > 0 && v > g_vVal[i]) || (g_vOp[i] < 0 && v < g_vVal[i]) || (g_vOp[i] == 0 && MathAbs(v - g_vVal[i]) < 1e-9))
      { Why(k, "skipped: veto " + g_vFeat[i]); return true; }
   }
   return false;
}

void OnTick()
{
   //  the guardian runs first, before readiness and before any management:
   //  if a limit is reached nothing else may act on this tick
   ENUM_PROP_ACTION pa = g_prop.Tick(g_prop.On() ? CloseCostEA() : 0.0);
   if(pa != PROP_OK)
     {
      CloseAllEA(pa == PROP_CLOSE_DAY ? "PROP_DAY" : pa == PROP_CLOSE_TOTAL ? "PROP_TOTAL" : "PROP_TARGET");
      if(pa == PROP_CLOSE_TARGET && EAPositionCount() == 0) g_prop.ConfirmPass();
      return;
     }
   //  the weekend gap is the one loss a stop cannot cap, so in prop mode the
   //  book is flat before the broker stops quoting for the week
   if(NearWeekClose(TimeCurrent()))
     {
      CloseAllEA("PROP_WEEKEND");
      return;
     }
   if(!ready)
   {
      if(MQLInfoInteger(MQL_TESTER)) OnTimer();   // timers do not run before the first tick in the tester
      else return;
   }
   DropClosed();
   bool newH4 = false;
   datetime h4 = iTime(_Symbol, PERIOD_H4, 0);
   if(h4 != lastH4) { lastH4 = h4; newH4 = true; UpdateEpisodes(); DxyTry(false); }
   for(int k = 0; k < NS; k++)
   {
      if(!S[k].on) continue;
      Manage(S[k], k, newH4);
      datetime b = iTime(_Symbol, S[k].tf, 0);
      if(b == S[k].lastBar) continue;
      S[k].lastBar = b;
      Resolve(S[k], TimeCurrent());
      int d = SignalAt(S[k], 1);
      if(d == 0) continue;
      double atr = B(hA[TI(S[k].tf)], 1), lvl = iClose(_Symbol, S[k].tf, 1);
      g_jTk = 0;
      if(g_vN > 0 && Vetoed(S[k], k, b, d, lvl, atr)) { }   // Why() names the rule
      else if(CanEnter(S[k], d)) Open(S[k], k, d, lvl, atr);   // calibrate with signals known BEFORE this one
      else Why(k, "skipped: slot busy or book full");
      if(JOn()) JSignal(S[k], k, b, d, lvl, atr);
      LaySig(b, lvl, d, S[k].mr, g_why[k]);
      AddSig(S[k], b, d, lvl, atr);              // every signal feeds future calibration
   }
   //  These two ran inside the old text panel, and the first one is not a
   //  reader: it raises the stored equity peak, which sets the risk throttle.
   //  They stay here, every tick that reaches this point, whatever ShowPanel
   //  says -- so the panel is now a display switch and nothing else. With the
   //  panel on, this is exactly what ran before; with it off, the EA now trades
   //  the same as with it on, which it did not.
   CurrentDrawdown();
   TrendScore();
   if(g_layerOn) LayerTick();
}
//+------------------------------------------------------------------+
