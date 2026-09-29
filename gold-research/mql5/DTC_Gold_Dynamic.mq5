//+------------------------------------------------------------------+
//| DTC Gold Dynamic EA — self-calibrating multi-timeframe robot      |
//| Research: gold-research/README.md (dynamic portfolio 2025-2026)   |
//|                                                                  |
//| Every trade's constants are measured from the recent market:     |
//|   Stop  = quantile(qSL) of recent signals' adverse excursion     |
//|   TP1   = quantile(qTP) of recent signals' favourable excursion  |
//|   Trail = quantile(qTR) of recent H4 trend pullback depths       |
//| Entry : EMA-stack pullback + higher-TF confluence + H4/D1 trend. |
//+------------------------------------------------------------------+
#property copyright "DTC research"
#property version   "2.00"
#property strict
#include <Trade/Trade.mqh>

enum ADX_RULE { ADX_ANY = 0, ADX_LT30 = 1 };

input group "=== Common ==="
input double RiskPercent      = 0.5;    // risk per trade, % of equity (0 = use FixedLots)
input double FixedLots        = 0.01;   // used when RiskPercent = 0
input double MaxSpreadPoints  = 80;     // skip entries when spread is wider (points)
input int    ServerUTCOffset  = 2;      // broker server time minus UTC, hours
input int    MaxHoldDays      = 30;     // safety time exit
input double TP1Fraction      = 0.5;    // share closed at TP1. 0.5 = smoother equity; 0 = only lock the stop at TP1 (more total profit, bumpier)
input int    BackfillDays     = 240;    // days of history scanned at start to calibrate (research used ~7 months)
input ulong  MagicBase        = 881000;
input bool   ShowPanel        = true;

input group "=== Slot 1: 5m pullback (15m+1H confluence) ==="
input bool            S1_On      = true;
input ENUM_TIMEFRAMES S1_TF      = PERIOD_M5;
input int             S1_PbEMA   = 30;
input ENUM_TIMEFRAMES S1_Conf1   = PERIOD_M15;
input ENUM_TIMEFRAMES S1_Conf2   = PERIOD_H1;
input ADX_RULE        S1_Adx     = ADX_ANY;
input int             S1_Horizon = 1440;    // minutes used to measure a signal's excursions
input int             S1_Look    = 60;      // how many recent signals calibrate the constants
input double          S1_qSL     = 0.50;
input double          S1_qTP     = 0.50;    // 0 = no TP1
input double          S1_Lock    = 0.25;
input double          S1_qTR     = 0.80;    // 0 = no trail

input group "=== Slot 2: 15m pullback (1H confluence, ADX<30) ==="
input bool            S2_On      = true;
input ENUM_TIMEFRAMES S2_TF      = PERIOD_M15;
input int             S2_PbEMA   = 40;
input ENUM_TIMEFRAMES S2_Conf1   = PERIOD_H1;
input ENUM_TIMEFRAMES S2_Conf2   = PERIOD_CURRENT;
input ADX_RULE        S2_Adx     = ADX_LT30;
input int             S2_Horizon = 1440;
input int             S2_Look    = 60;
input double          S2_qSL     = 0.50;
input double          S2_qTP     = 0.50;
input double          S2_Lock    = 0.25;
input double          S2_qTR     = 0.80;

input group "=== Slot 3: 1H pullback ==="
input bool            S3_On      = true;
input ENUM_TIMEFRAMES S3_TF      = PERIOD_H1;
input int             S3_PbEMA   = 40;
input ENUM_TIMEFRAMES S3_Conf1   = PERIOD_CURRENT;
input ENUM_TIMEFRAMES S3_Conf2   = PERIOD_CURRENT;
input ADX_RULE        S3_Adx     = ADX_ANY;
input int             S3_Horizon = 4320;
input int             S3_Look    = 30;
input double          S3_qSL     = 0.50;
input double          S3_qTP     = 0.30;
input double          S3_Lock    = 0.25;
input double          S3_qTR     = 0.50;

input group "=== Daily DXY (tighten runner trail when the dollar turns against gold) ==="
input bool   UseDXY           = true;
input string DXYSymbol        = "";     // e.g. "DXY" or "USDX"; empty = build DXY from 6 FX pairs
input string FxSuffix         = "";     // broker suffix for FX pairs, e.g. ".m"
input double DXYAgainstTrail  = 0.7;    // trail width multiplier when USD daily trend opposes the trade

input group "=== Session (UTC hours) ==="
input int SessFromUTC = 7;
input int SessToUTC   = 20;

//--- constants of the method (same as the research)
#define K_MIN          0.5
#define K_MAX          8.0
#define R1_MIN         0.2
#define R1_MAX         3.0
#define EPISODES       20
#define MAX_SIGS       400

struct Sig { datetime t; int dir; double lvl; double atr; double mae; double mfe; bool done; datetime endT; };

struct Slot
{
   bool on; ENUM_TIMEFRAMES tf, c1, c2; int pb, adx, horizon, look; double qsl, qtp, lock, qtr; ulong magic;
   Sig sigs[]; int nsig;
   datetime lastBar;
   // open trade state
   double risk, lvl, entry, best, trailW; bool tp1Done; datetime openT;
   // last calibrated values (for the panel)
   double kNow, r1Now, trNow;
};
Slot S[3];
CTrade trade;
double epDepth[]; int nEp = 0; datetime lastH4 = 0;

//------------------------------------------------------------------ indicator helpers
int hE[7][12]; int hA[12], hX[12], h20[12], h50[12]; ENUM_TIMEFRAMES tfL[12]; int nTf = 0;
const int EL[7] = {30, 35, 40, 45, 50, 60, 20};

int TI(ENUM_TIMEFRAMES tf)
{
   for(int i = 0; i < nTf; i++) if(tfL[i] == tf) return i;
   int i = nTf++; tfL[i] = tf;
   for(int k = 0; k < 6; k++) hE[k][i] = iMA(_Symbol, tf, EL[k], 0, MODE_EMA, PRICE_CLOSE);
   hA[i] = iATR(_Symbol, tf, 14);
   hX[i] = iADXWilder(_Symbol, tf, 14);
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
int SignalAt(Slot &s, int sh)
{
   datetime T = iTime(_Symbol, s.tf, sh) + PeriodSeconds(s.tf);
   int st = StackAt(s.tf, sh);
   if(st == 0) return 0;
   int i = TI(s.tf);
   int pbk = s.pb == 40 ? 2 : (s.pb == 60 ? 5 : 0);
   double ePb = B(hE[pbk][i], sh), e30 = B(hE[0][i], sh);
   double o = iOpen(_Symbol, s.tf, sh), h = iHigh(_Symbol, s.tf, sh), l = iLow(_Symbol, s.tf, sh), c = iClose(_Symbol, s.tf, sh);
   int dir = 0;
   if(st == 1 && l <= ePb && c > e30 && c > o) dir = 1;
   if(st == -1 && h >= ePb && c < e30 && c < o) dir = -1;
   if(dir == 0) return 0;
   if(HtfDirAt(PERIOD_H4, T) != dir || HtfDirAt(PERIOD_D1, T) != dir) return 0;
   if(s.c1 != PERIOD_CURRENT && StackAt(s.c1, ClosedShift(s.c1, T)) != dir) return 0;
   if(s.c2 != PERIOD_CURRENT && StackAt(s.c2, ClosedShift(s.c2, T)) != dir) return 0;
   if(s.adx == ADX_LT30) { double a = B(hX[i], sh); if(!(a < 30)) return 0; }
   if(!InSessionUTC(T - 60)) return 0;
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
double DxyClose(int shift)
{
   if(DXYSymbol != "") return iClose(DXYSymbol, PERIOD_D1, shift);
   string p[6] = {"EURUSD", "USDJPY", "GBPUSD", "USDCAD", "USDSEK", "USDCHF"};
   double w[6] = {-0.576, 0.136, -0.119, 0.091, 0.042, 0.036};
   datetime t = iTime(_Symbol, PERIOD_D1, shift);
   double v = 50.14348112;
   for(int k = 0; k < 6; k++)
   {
      string sym = p[k] + FxSuffix;
      int sh = iBarShift(sym, PERIOD_D1, t, false);
      double c = sh < 0 ? 0 : iClose(sym, PERIOD_D1, sh);
      if(c <= 0) return 0;
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

//------------------------------------------------------------------ trading
double Lots(double stopDist)
{
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), mn = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), mx = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(RiskPercent <= 0) return MathMax(mn, FixedLots);
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0 || stopDist <= 0) return 0;
   double lots = AccountInfoDouble(ACCOUNT_EQUITY) * RiskPercent / 100.0 / (stopDist / ts * tv);
   lots = MathFloor(lots / step) * step;
   if(lots < mn) return 0;                 // risk too small for the minimum lot -> skip rather than over-risk
   return MathMin(mx, lots);
}
bool GetPos(Slot &s, ulong &tk, int &dir, double &vol, double &sl)
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong t = PositionGetTicket(k);
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == (long)s.magic)
      { tk = t; vol = PositionGetDouble(POSITION_VOLUME); sl = PositionGetDouble(POSITION_SL); dir = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1; return true; }
   }
   return false;
}
void Open(Slot &s, int dir, double lvl, double atr)
{
   double k = MathMax(K_MIN, MathMin(K_MAX, SigQuantile(s, 0, s.qsl, 2.0)));
   double risk = k * atr;
   double r1 = 0;
   if(s.qtp > 0) r1 = MathMax(R1_MIN, MathMin(R1_MAX, SigQuantile(s, 1, s.qtp, 1.0) / k));
   double tw = s.qtr > 0 ? TrailQuantile(s.qtr) * B(hA[TI(PERIOD_H4)], 1) : 0;
   if(UseDXY && tw > 0)
   {
      int usd = UsdDailyDir();
      if(usd != 0 && usd == dir) tw *= DXYAgainstTrail;     // USD rising vs gold long (or falling vs short) -> protect profit sooner
   }
   s.kNow = k; s.r1Now = r1; s.trNow = tw;
   if((SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point > MaxSpreadPoints) return;
   double lots = Lots(risk);
   if(lots <= 0) { Print("Slot ", s.magic - MagicBase + 1, ": stop $", DoubleToString(risk, 2), " too wide for RiskPercent - skipped"); return; }
   trade.SetExpertMagicNumber(s.magic);
   double sl = NormalizeDouble(lvl - dir * risk, _Digits);
   bool ok = dir == 1 ? trade.Buy(lots, _Symbol, 0, sl, 0, "DTC-dyn") : trade.Sell(lots, _Symbol, 0, sl, 0, "DTC-dyn");
   if(ok)
   {
      s.risk = risk; s.lvl = lvl; s.entry = trade.ResultPrice(); s.best = s.entry; s.trailW = tw;
      s.tp1Done = (r1 <= 0); s.r1Now = r1; s.openT = TimeCurrent();
   }
}
void Manage(Slot &s, bool newH4)
{
   ulong tk; int dir; double vol, sl;
   if(!GetPos(s, tk, dir, vol, sl)) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), px = dir == 1 ? bid : ask;
   if(s.risk <= 0 || s.openT == 0)
   {
      // EA (re)started with a position already open: rebuild the trade state from the position itself
      s.entry = PositionGetDouble(POSITION_PRICE_OPEN);
      s.openT = (datetime)PositionGetInteger(POSITION_TIME);
      s.lvl = s.entry;
      s.risk = sl > 0 ? MathAbs(s.entry - sl) : 0;
      s.best = dir == 1 ? MathMax(s.entry, px) : MathMin(s.entry, px);
      s.tp1Done = true;                                  // partial state unknown -> do not partial-close again
      s.trailW = s.qtr > 0 ? TrailQuantile(s.qtr) * B(hA[TI(PERIOD_H4)], 1) : 0;
      if(s.risk <= 0) return;
   }
   s.best = dir == 1 ? MathMax(s.best, px) : MathMin(s.best, px);
   trade.SetExpertMagicNumber(s.magic);
   double nsl = sl;
   if(!s.tp1Done && s.risk > 0 && (px - s.lvl) * dir >= s.r1Now * s.risk)
   {
      double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      double part = MathFloor(vol * TP1Fraction / step) * step;
      if(part >= SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN) && part < vol) trade.PositionClosePartial(tk, part);
      s.tp1Done = true;
      double lk = s.entry + dir * s.lock * s.risk;
      if((dir == 1 && lk > nsl) || (dir == -1 && lk < nsl)) nsl = lk;
   }
   if(newH4 && s.trailW > 0)
   {
      double ns = s.best - dir * s.trailW;
      if((dir == 1 && ns > nsl) || (dir == -1 && ns < nsl)) nsl = ns;
   }
   if(TimeCurrent() - s.openT > MaxHoldDays * 86400) { trade.PositionClose(tk); return; }
   if(MathAbs(nsl - sl) > _Point)
   {
      double lvl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
      if((dir == 1 && nsl < bid - lvl) || (dir == -1 && nsl > ask + lvl)) trade.PositionModify(tk, NormalizeDouble(nsl, _Digits), 0);
   }
}

//------------------------------------------------------------------ setup
void Load(int k, bool on, ENUM_TIMEFRAMES tf, int pb, ENUM_TIMEFRAMES c1, ENUM_TIMEFRAMES c2, int adx, int hor, int look,
          double qsl, double qtp, double lock, double qtr)
{
   S[k].on = on; S[k].tf = tf; S[k].pb = pb; S[k].c1 = c1; S[k].c2 = c2; S[k].adx = adx; S[k].horizon = hor; S[k].look = look;
   S[k].qsl = qsl; S[k].qtp = qtp; S[k].lock = lock; S[k].qtr = qtr; S[k].magic = MagicBase + k; S[k].nsig = 0; S[k].lastBar = 0;
   S[k].tp1Done = true; S[k].kNow = 0; S[k].r1Now = 0; S[k].trNow = 0;
   S[k].risk = 0; S[k].openT = 0; S[k].best = 0; S[k].trailW = 0; S[k].entry = 0; S[k].lvl = 0;
   ArrayResize(S[k].sigs, 0);
   TI(tf); TI(PERIOD_H4); TI(PERIOD_D1);
   if(c1 != PERIOD_CURRENT) TI(c1);
   if(c2 != PERIOD_CURRENT) TI(c2);
}
void Backfill(Slot &s)
{
   int n = (int)MathMin((long)BackfillDays * 86400 / PeriodSeconds(s.tf), Bars(_Symbol, s.tf) - 80);
   for(int sh = n; sh >= 2; sh--)
   {
      int d = SignalAt(s, sh);
      if(d == 0) continue;
      double atr = B(hA[TI(s.tf)], sh);
      if(atr == EMPTY_VALUE || atr <= 0) continue;
      AddSig(s, iTime(_Symbol, s.tf, sh) + PeriodSeconds(s.tf), d, iClose(_Symbol, s.tf, sh), atr);
   }
   Resolve(s, TimeCurrent());
   PrintFormat("Slot %d (%s): %d historical signals calibrated", (int)(s.magic - MagicBase + 1), EnumToString(s.tf), s.nsig);
}
int OnInit()
{
   Load(0, S1_On, S1_TF, S1_PbEMA, S1_Conf1, S1_Conf2, S1_Adx, S1_Horizon, S1_Look, S1_qSL, S1_qTP, S1_Lock, S1_qTR);
   Load(1, S2_On, S2_TF, S2_PbEMA, S2_Conf1, S2_Conf2, S2_Adx, S2_Horizon, S2_Look, S2_qSL, S2_qTP, S2_Lock, S2_qTR);
   Load(2, S3_On, S3_TF, S3_PbEMA, S3_Conf1, S3_Conf2, S3_Adx, S3_Horizon, S3_Look, S3_qSL, S3_qTP, S3_Lock, S3_qTR);
   EventSetTimer(5);          // indicators need a moment to build before the backfill
   return INIT_SUCCEEDED;
}
bool ready = false;
void OnTimer()
{
   if(ready) return;
   for(int k = 0; k < 3; k++) if(S[k].on) Backfill(S[k]);
   UpdateEpisodes();
   ready = true;
   EventKillTimer();
}
void OnDeinit(const int r) { EventKillTimer(); Comment(""); }

void OnTick()
{
   if(!ready)
   {
      if(MQLInfoInteger(MQL_TESTER)) OnTimer();   // timers do not run before the first tick in the tester
      else return;
   }
   bool newH4 = false;
   datetime h4 = iTime(_Symbol, PERIOD_H4, 0);
   if(h4 != lastH4) { lastH4 = h4; newH4 = true; UpdateEpisodes(); }
   for(int k = 0; k < 3; k++)
   {
      if(!S[k].on) continue;
      Manage(S[k], newH4);
      datetime b = iTime(_Symbol, S[k].tf, 0);
      if(b == S[k].lastBar) continue;
      S[k].lastBar = b;
      Resolve(S[k], TimeCurrent());
      int d = SignalAt(S[k], 1);
      if(d == 0) continue;
      double atr = B(hA[TI(S[k].tf)], 1), lvl = iClose(_Symbol, S[k].tf, 1);
      ulong tk; int pd; double v, sl;
      bool busy = GetPos(S[k], tk, pd, v, sl);
      if(!busy) Open(S[k], d, lvl, atr);         // calibrate with signals known BEFORE this one
      AddSig(S[k], b, d, lvl, atr);              // every signal feeds future calibration
   }
   if(ShowPanel)
   {
      string txt = "DTC Gold Dynamic\n";
      for(int k = 0; k < 3; k++) if(S[k].on)
         txt += StringFormat("Slot %d %s | signals %d | last SL %.2f ATR, TP1 %.2f R, trail $%.1f\n",
                             k + 1, EnumToString(S[k].tf), S[k].nsig, S[k].kNow, S[k].r1Now, S[k].trNow);
      Comment(txt);
   }
}
//+------------------------------------------------------------------+
