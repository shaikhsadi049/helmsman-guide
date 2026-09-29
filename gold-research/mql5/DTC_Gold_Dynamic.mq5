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
#property version   "3.10"
#property strict
#include <Trade/Trade.mqh>

enum ADX_RULE { ADX_ANY = 0, ADX_LT30 = 1 };
enum ENTRY_KIND { E_PB = 0, E_RSI2 = 1, E_BRK = 2 };
enum RISK_MODE { RISK_DD_EDGE = 0, RISK_DD = 1, RISK_EDGE = 2, RISK_FIXED_MAX = 3 };
#define NS 7

input group "=== Common ==="
input double MinRiskPercent   = 1.0;    // dynamic risk per trade: lowest % of equity
input double MaxRiskPercent   = 5.0;    // dynamic risk per trade: highest % of equity (0 = use FixedLots)
input RISK_MODE RiskMode      = RISK_DD_EDGE; // DD_EDGE = drawdown x slot edge (research best), DD = drawdown only, EDGE = edge only (risky), FIXED_MAX = always MaxRiskPercent
input double EdgeLow          = 0.73;   // slot edge (median MFE / median MAE of recent signals) at or below this -> lowest edge score
input double EdgeHigh         = 2.6;    // slot edge at or above this -> full edge score
input double FixedLots        = 0.01;   // used when MaxRiskPercent = 0
input double MaxSpreadPoints  = 80;     // skip entries when spread is wider (points)
input int    ServerUTCOffset  = 2;      // broker server time minus UTC, hours
input int    MaxHoldDays      = 30;     // safety time exit
input double MaxOpenRiskPercent = 15;   // cap on the summed risk of all open positions (positions with a stop in profit count as 0)
input double ThrottleFullDD     = 20;   // risk slides from Max toward Min as equity falls below its peak; at this drawdown % it is MinRiskPercent
input double MaxDrawdownStopPercent = 0; // hard stop for NEW trades at this drawdown % (0 = off; research: a hard stop hurt recovery)
input int    MaxTotalPositions = 7;     // cap on open positions across all slots
input int    MaxPositions     = 1;      // per slot. >1 = pyramiding: add only while all open positions are risk-free (hedging account)
input double TP1FractionOverride = -1;  // -1 = use each slot's F1; 0.5 = close half at TP1; 0 = only lock the stop at TP1
input int    BackfillDays     = 240;    // days of history scanned at start to calibrate (research used ~7 months)
input ulong  MagicBase        = 881000;
input bool   ShowPanel        = true;

input group "=== Strategy slots (spec string, or OFF) ==="
// Keys: TF=M3|M5|M15|M30|H1  ENTRY=PB|RSI2|BRK  EMA=30|40|60 (PB)  RSI=10|5 (RSI2)  BRKN=20 (BRK)
//       CONF1/CONF2=NONE|M15|H1|H4 (higher-TF EMA stack must agree)  ADX=ANY|LT30  SESS=1|0
//       LOOK (signals used for calibration)  QSL QTP QTR (quantiles)  LOCK (R)  F1 (share closed at TP1)
// Defaults = the 7-strategy portfolio from the research (steps 1..7). Use OFF to disable a slot.
input string Slot1 = "TF=M30;ENTRY=PB;EMA=30;CONF1=H1;SESS=1;LOOK=60;QSL=0.7;QTP=0.3;LOCK=0.25;QTR=0.8;F1=0";
input string Slot2 = "TF=M15;ENTRY=BRK;BRKN=20;CONF1=H1;CONF2=H4;SESS=0;LOOK=60;QSL=0.5;QTP=0.2;LOCK=0.1;QTR=0.8;F1=0";
input string Slot3 = "TF=M3;ENTRY=RSI2;RSI=10;CONF1=M15;CONF2=H1;SESS=1;LOOK=60;QSL=0.7;QTP=0.2;LOCK=0.1;QTR=0.5;F1=0.5";
input string Slot4 = "TF=M30;ENTRY=BRK;BRKN=20;SESS=0;LOOK=60;QSL=0.7;QTP=0.2;LOCK=0.25;QTR=0.8;F1=0";
input string Slot5 = "TF=M5;ENTRY=PB;EMA=30;CONF1=M15;CONF2=H1;SESS=1;LOOK=60;QSL=0.5;QTP=0.5;LOCK=0.25;QTR=0.5;F1=0.5";
input string Slot6 = "TF=M3;ENTRY=RSI2;RSI=5;CONF1=M15;CONF2=H1;SESS=1;LOOK=60;QSL=0.7;QTP=0.2;LOCK=0.1;QTR=0.5;F1=0.5";
input string Slot7 = "TF=M3;ENTRY=BRK;BRKN=20;CONF1=M15;CONF2=H1;SESS=0;LOOK=60;QSL=0.7;QTP=0.2;LOCK=0.1;QTR=0.8;F1=0";

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
#define R1_MIN         0.1
#define R1_MAX         3.0
#define EPISODES       20
#define MAX_SIGS       400

struct Sig { datetime t; int dir; double lvl; double atr; double mae; double mfe; bool done; datetime endT; };

struct Slot
{
   bool on; ENUM_TIMEFRAMES tf, c1, c2; int entry, pb, rsiTh, brkN, adx, horizon, look; bool sess; double qsl, qtp, lock, qtr, f1; ulong magic;
   Sig sigs[]; int nsig;
   datetime lastBar;
   // last calibrated values (for the panel)
   double kNow, r1Now, trNow, riskNow;
};
Slot S[NS];
CTrade trade;
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
int SignalAt(Slot &s, int sh)
{
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


//------------------------------------------------------------------ account-level risk guards
double MoneyPerPriceUnit(double lots)
{
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   return ts > 0 ? lots * tv / ts : 0;
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
// equity peak persists across restarts in a terminal global variable
double CurrentDrawdown()
{
   string key = "DTCDYN_PEAK_" + _Symbol + "_" + IntegerToString((long)MagicBase);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double peak = GlobalVariableCheck(key) ? GlobalVariableGet(key) : eq;
   if(eq > peak) peak = eq;
   GlobalVariableSet(key, peak);
   return peak > 0 ? 1.0 - eq / peak : 0;
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
// risk % for a new trade of this slot: MinRiskPercent .. MaxRiskPercent
double RiskPctNow(Slot &s)
{
   double mn = MathMin(MinRiskPercent, MaxRiskPercent), mx = MaxRiskPercent;
   double x;
   if(RiskMode == RISK_FIXED_MAX)  x = 1.0;
   else if(RiskMode == RISK_DD)    x = DDScore();
   else if(RiskMode == RISK_EDGE)  x = EdgeScore(s);
   else                            x = DDScore() * (0.5 + 0.5 * EdgeScore(s));
   return mn + (mx - mn) * x;
}

//------------------------------------------------------------------ trading
double Lots(double stopDist, double riskPct)
{
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), mn = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), mx = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(MaxRiskPercent <= 0) return MathMax(mn, FixedLots);
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0 || stopDist <= 0) return 0;
   double lots = AccountInfoDouble(ACCOUNT_EQUITY) * riskPct / 100.0 / (stopDist / ts * tv);
   lots = MathFloor(lots / step) * step;
   if(lots < mn) return 0;                 // risk too small for the minimum lot -> skip rather than over-risk
   return MathMin(mx, lots);
}
// ---- per-position state (several positions per slot when pyramiding)
struct PState { ulong tk; int slot; int dir; double risk, lvl, entry, best, trailW, r1, lock; bool tp1Done; datetime openT; };
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
   if(DrawdownStopActive()) { Print("Drawdown stop active: equity is more than ", MaxDrawdownStopPercent, "% below its peak - no new trades"); return; }
   double riskPct = RiskPctNow(s);
   s.riskNow = riskPct;
   double lots = Lots(risk, riskPct);
   if(lots > 0 && MaxRiskPercent > 0)
   {
      // shrink (or skip) the trade so the summed open risk stays under MaxOpenRiskPercent
      double room = MaxOpenRiskPercent - OpenRiskPercent();
      double thisRisk = risk * MoneyPerPriceUnit(lots) / AccountInfoDouble(ACCOUNT_EQUITY) * 100.0;
      if(room <= 0) lots = 0;
      else if(thisRisk > room)
      {
         double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
         lots = MathFloor(lots * room / thisRisk / step) * step;
         if(lots < SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN)) lots = 0;
      }
      if(lots <= 0) { Print("Slot ", slotIdx + 1, ": open-risk cap ", MaxOpenRiskPercent, "% reached - skipped"); return; }
   }
   if(lots <= 0) { Print("Slot ", slotIdx + 1, ": stop $", DoubleToString(risk, 2), " too wide for risk " + DoubleToString(riskPct, 2) + "% - skipped"); return; }
   trade.SetExpertMagicNumber(s.magic);
   double sl = NormalizeDouble(lvl - dir * risk, _Digits);
   bool ok = dir == 1 ? trade.Buy(lots, _Symbol, 0, sl, 0, "DTC-dyn") : trade.Sell(lots, _Symbol, 0, sl, 0, "DTC-dyn");
   if(ok && trade.ResultRetcode() == TRADE_RETCODE_DONE)
   {
      ArrayResize(PS, nPS + 1);
      PS[nPS].tk = trade.ResultOrder(); PS[nPS].slot = slotIdx; PS[nPS].dir = dir; PS[nPS].risk = risk; PS[nPS].lvl = lvl;
      PS[nPS].entry = trade.ResultPrice(); PS[nPS].best = trade.ResultPrice(); PS[nPS].trailW = tw; PS[nPS].r1 = r1;
      PS[nPS].lock = s.lock; PS[nPS].tp1Done = (r1 <= 0); PS[nPS].openT = TimeCurrent();
      nPS++;
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
      PS[i].tp1Done = true;                                  // partial state unknown -> never partial-close again
      PS[i].trailW = s.qtr > 0 ? TrailQuantile(s.qtr) * B(hA[TI(PERIOD_H4)], 1) : 0;
      PS[i].openT = (datetime)PositionGetInteger(POSITION_TIME);
   }
   PS[i].best = dir == 1 ? MathMax(PS[i].best, px) : MathMin(PS[i].best, px);
   trade.SetExpertMagicNumber(s.magic);
   double nsl = sl;
   if(!PS[i].tp1Done && PS[i].risk > 0 && (px - PS[i].lvl) * dir >= PS[i].r1 * PS[i].risk)
   {
      double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      double frac = TP1FractionOverride >= 0 ? TP1FractionOverride : s.f1;
      double part = MathFloor(vol * frac / step) * step;
      if(part >= SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN) && part < vol) trade.PositionClosePartial(tk, part);
      PS[i].tp1Done = true;
      double lk = PS[i].entry + dir * PS[i].lock * PS[i].risk;
      if((dir == 1 && lk > nsl) || (dir == -1 && lk < nsl)) nsl = lk;
   }
   if(newH4 && PS[i].trailW > 0)
   {
      double ns = PS[i].best - dir * PS[i].trailW;
      if((dir == 1 && ns > nsl) || (dir == -1 && ns < nsl)) nsl = ns;
   }
   if(TimeCurrent() - PS[i].openT > MaxHoldDays * 86400) { trade.PositionClose(tk); return; }
   if(MathAbs(nsl - sl) > _Point)
   {
      double lvl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
      if((dir == 1 && nsl < bid - lvl) || (dir == -1 && nsl > ask + lvl)) trade.PositionModify(tk, NormalizeDouble(nsl, _Digits), 0);
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
   S[k].on = !(up == "" || up == "OFF");
   S[k].magic = MagicBase + k; S[k].nsig = 0; S[k].lastBar = 0; S[k].kNow = 0; S[k].r1Now = 0; S[k].trNow = 0; S[k].riskNow = 0;
   ArrayResize(S[k].sigs, 0);
   if(!S[k].on) return;
   S[k].tf = ParseTF(SpecGet(sp, "TF", "M15"));
   string e = SpecGet(sp, "ENTRY", "PB");
   S[k].entry = e == "RSI2" ? E_RSI2 : (e == "BRK" ? E_BRK : E_PB);
   S[k].pb = (int)StringToInteger(SpecGet(sp, "EMA", "30"));
   S[k].rsiTh = (int)StringToInteger(SpecGet(sp, "RSI", "10"));
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
   S[k].qtr = StringToDouble(SpecGet(sp, "QTR", "0.8"));
   S[k].f1 = StringToDouble(SpecGet(sp, "F1", "0.5"));
   TI(S[k].tf); TI(PERIOD_H4); TI(PERIOD_D1);
   if(S[k].c1 != PERIOD_CURRENT) TI(S[k].c1);
   if(S[k].c2 != PERIOD_CURRENT) TI(S[k].c2);
   PrintFormat("Slot %d: %s", k + 1, sp);
}
void Backfill(Slot &s)
{
   // scan from the newest closed bar backwards and stop once enough signals are collected (fast start, same calibration)
   int n = (int)MathMin((long)BackfillDays * 86400 / PeriodSeconds(s.tf), Bars(_Symbol, s.tf) - 80);
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
int OnInit()
{
   Load(0, Slot1); Load(1, Slot2); Load(2, Slot3); Load(3, Slot4); Load(4, Slot5); Load(5, Slot6); Load(6, Slot7);
   EventSetTimer(5);          // indicators need a moment to build before the backfill
   return INIT_SUCCEEDED;
}
bool ready = false;
void OnTimer()
{
   if(ready) return;
   for(int k = 0; k < NS; k++) if(S[k].on) Backfill(S[k]);
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
   DropClosed();
   bool newH4 = false;
   datetime h4 = iTime(_Symbol, PERIOD_H4, 0);
   if(h4 != lastH4) { lastH4 = h4; newH4 = true; UpdateEpisodes(); }
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
      if(CanEnter(S[k], d)) Open(S[k], k, d, lvl, atr);   // calibrate with signals known BEFORE this one
      AddSig(S[k], b, d, lvl, atr);              // every signal feeds future calibration
   }
   if(ShowPanel)
   {
      string txt = "DTC Gold Dynamic (7 slots)\n";
      for(int k = 0; k < NS; k++) if(S[k].on)
         txt += StringFormat("Slot %d %s | signals %d | last SL %.2f ATR, TP1 %.2f R, trail $%.1f | risk now %.2f%%\n",
                             k + 1, EnumToString(S[k].tf), S[k].nsig, S[k].kNow, S[k].r1Now, S[k].trNow, RiskPctNow(S[k]));
      Comment(txt);
   }
}
//+------------------------------------------------------------------+
