//+------------------------------------------------------------------+
//| DTC Gold Multi-TF EA                                             |
//| Research: gold-research/README.md                                |
//| Up to 3 independent strategy slots (e.g. 1H high-win + 5m/15m    |
//| runners). Each slot: EMA-stack entry (swing / pullback), H4+D1   |
//| trend filter, optional higher-TF confluence, volatility-adaptive |
//| ATR stop, TP1 partial + stop lock, runner managed on a higher TF |
//| (chandelier trail, trend-break exit, profit-lock giveback).      |
//+------------------------------------------------------------------+
#property copyright "DTC research"
#property version   "1.00"
#property strict
#include <Trade/Trade.mqh>

enum ENTRY_TYPE { ENTRY_SWING = 0, ENTRY_PULLBACK = 1 };
enum ADX_RULE   { ADX_ANY = 0, ADX_LT30 = 1, ADX_GE25 = 2 };

input group "=== Common ==="
input double RiskPercent      = 0.25;   // risk per trade, % of equity
input double MaxSpreadPoints  = 80;     // skip entries when spread is wider
input int    SessionUTCOffset = 0;      // broker server time minus UTC, hours (e.g. 2 or 3)
input ulong  MagicBase        = 770000;

input group "=== Slot 1 ==="
input bool            S1_Enable   = true;
input ENUM_TIMEFRAMES S1_TF       = PERIOD_H1;
input ENTRY_TYPE      S1_Entry    = ENTRY_PULLBACK;
input int             S1_PbEMA    = 30;          // pullback touches this EMA (30/40/60)
input ENUM_TIMEFRAMES S1_Conf1    = PERIOD_CURRENT; // extra confluence TF (PERIOD_CURRENT = none)
input ENUM_TIMEFRAMES S1_Conf2    = PERIOD_CURRENT;
input ADX_RULE        S1_Adx      = ADX_LT30;
input int             S1_SessFrom = 7;           // UTC hour, -1 = no session filter
input int             S1_SessTo   = 20;
input double          S1_SL_ATR   = 2.0;
input bool            S1_SL_Adapt = true;        // SL x (0.7 + 0.6 * volatility percentile)
input double          S1_TP1_R    = 0.5;         // 0 = no TP1
input double          S1_TP1_Frac = 0.5;
input double          S1_Lock_R   = 0.25;        // stop moves to entry + lock R after TP1
input ENUM_TIMEFRAMES S1_RunTF    = PERIOD_H4;   // runner management timeframe
input double          S1_Trail    = 3.0;         // chandelier ATR multiple on RunTF, 0 = off
input bool            S1_Break    = false;       // exit when RunTF EMA stack breaks
input double          S1_GB_A     = 3.0;         // profit-lock activates at MFE >= A R (0 = off)
input double          S1_GB_G     = 0.35;        // max giveback fraction of peak

input group "=== Slot 2 ==="
input bool            S2_Enable   = true;
input ENUM_TIMEFRAMES S2_TF       = PERIOD_M5;
input ENTRY_TYPE      S2_Entry    = ENTRY_PULLBACK;
input int             S2_PbEMA    = 40;
input ENUM_TIMEFRAMES S2_Conf1    = PERIOD_M15;
input ENUM_TIMEFRAMES S2_Conf2    = PERIOD_CURRENT;
input ADX_RULE        S2_Adx      = ADX_ANY;
input int             S2_SessFrom = -1;
input int             S2_SessTo   = 24;
input double          S2_SL_ATR   = 4.0;
input bool            S2_SL_Adapt = true;
input double          S2_TP1_R    = 0.0;
input double          S2_TP1_Frac = 0.0;
input double          S2_Lock_R   = 0.0;
input ENUM_TIMEFRAMES S2_RunTF    = PERIOD_H4;
input double          S2_Trail    = 0.0;
input bool            S2_Break    = true;
input double          S2_GB_A     = 0.0;
input double          S2_GB_G     = 0.0;

input group "=== Slot 3 ==="
input bool            S3_Enable   = true;
input ENUM_TIMEFRAMES S3_TF       = PERIOD_M15;
input ENTRY_TYPE      S3_Entry    = ENTRY_PULLBACK;
input int             S3_PbEMA    = 40;
input ENUM_TIMEFRAMES S3_Conf1    = PERIOD_CURRENT;
input ENUM_TIMEFRAMES S3_Conf2    = PERIOD_CURRENT;
input ADX_RULE        S3_Adx      = ADX_ANY;
input int             S3_SessFrom = -1;
input int             S3_SessTo   = 24;
input double          S3_SL_ATR   = 1.5;
input bool            S3_SL_Adapt = true;
input double          S3_TP1_R    = 0.0;
input double          S3_TP1_Frac = 0.0;
input double          S3_Lock_R   = 0.0;
input ENUM_TIMEFRAMES S3_RunTF    = PERIOD_H4;
input double          S3_Trail    = 2.0;
input bool            S3_Break    = true;
input double          S3_GB_A     = 0.0;
input double          S3_GB_G     = 0.0;

//--- per-slot configuration and state
struct Slot
{
   bool            on;
   ENUM_TIMEFRAMES tf, conf1, conf2, runTF;
   int             entry, pbEMA, adxRule, sFrom, sTo;
   double          slATR, tp1R, tp1Frac, lockR, trail, gbA, gbG;
   bool            adapt, brk;
   ulong           magic;
   // state of the open trade
   double          risk;      // initial stop distance (price)
   double          entryPx, levelPx; // fill price, signal close (levels are measured from it)
   double          best, mfeR;
   bool            tp1Done;
   datetime        lastBar, lastRunBar;
};
Slot S[3];
CTrade trade;

//--- indicator handles cache (one per TF/period)
int hEMA[6][10];      // [ema index][tf slot index]
int hATR[10], hADX[10], hE20[10], hE50[10];
ENUM_TIMEFRAMES tfList[10];
int tfCount = 0;
const int EMA_LEN[6] = {30, 35, 40, 45, 50, 60};

int TfIndex(ENUM_TIMEFRAMES tf)
{
   for(int i = 0; i < tfCount; i++) if(tfList[i] == tf) return i;
   int i = tfCount++;
   tfList[i] = tf;
   for(int k = 0; k < 6; k++) hEMA[k][i] = iMA(_Symbol, tf, EMA_LEN[k], 0, MODE_EMA, PRICE_CLOSE);
   hATR[i] = iATR(_Symbol, tf, 14);
   hADX[i] = iADXWilder(_Symbol, tf, 14);
   hE20[i] = iMA(_Symbol, tf, 20, 0, MODE_EMA, PRICE_CLOSE);
   hE50[i] = iMA(_Symbol, tf, 50, 0, MODE_EMA, PRICE_CLOSE);
   return i;
}

double Buf(int handle, int shift, int buffer = 0)
{
   double v[1];
   if(CopyBuffer(handle, buffer, shift, 1, v) != 1) return EMPTY_VALUE;
   return v[0];
}

// EMA stack on the closed bar `shift`: +1 bull, -1 bear, 0 mixed
int Stack(ENUM_TIMEFRAMES tf, int shift)
{
   int i = TfIndex(tf);
   double e[6];
   for(int k = 0; k < 6; k++) { e[k] = Buf(hEMA[k][i], shift); if(e[k] == EMPTY_VALUE) return 0; }
   bool bull = true, bear = true;
   for(int k = 0; k < 5; k++) { if(!(e[k] > e[k + 1])) bull = false; if(!(e[k] < e[k + 1])) bear = false; }
   return bull ? 1 : (bear ? -1 : 0);
}

// HTF trend on previous closed bar: EMA20 vs EMA50 -> +1 / -1
int HtfDir(ENUM_TIMEFRAMES tf)
{
   int i = TfIndex(tf);
   double f = Buf(hE20[i], 1), s = Buf(hE50[i], 1);
   if(f == EMPTY_VALUE || s == EMPTY_VALUE) return 0;
   return f > s ? 1 : -1;
}

// volatility percentile of ATR/close over ~40 days of bars on tf
double VolPct(ENUM_TIMEFRAMES tf)
{
   int i = TfIndex(tf);
   int n = (int)MathMin(4000, MathMax(50, 40 * 86400 / PeriodSeconds(tf)));
   double atr[], cl[];
   if(CopyBuffer(hATR[i], 0, 1, n, atr) != n) return 0.5;
   if(CopyClose(_Symbol, tf, 1, n, cl) != n) return 0.5;
   double cur = atr[n - 1] / cl[n - 1];
   int below = 0;
   for(int k = 0; k < n; k++) if(atr[k] / cl[k] <= cur) below++;
   return (double)below / n;
}

bool InSession(const Slot &s)
{
   if(s.sFrom < 0) return true;
   MqlDateTime t; TimeToStruct(TimeCurrent() - SessionUTCOffset * 3600, t);
   return t.hour >= s.sFrom && t.hour < s.sTo;
}

bool NewBar(ENUM_TIMEFRAMES tf, datetime &last)
{
   datetime b = iTime(_Symbol, tf, 0);
   if(b != last) { last = b; return true; }
   return false;
}

// entry signal on the last closed bar of s.tf: +1 long, -1 short, 0 none
int Signal(Slot &s)
{
   int st1 = Stack(s.tf, 1), st2 = Stack(s.tf, 2);
   int dir = 0;
   if(s.entry == ENTRY_SWING)
   {
      // first bar of a swing where filters agree (flag reset when the stack breaks)
      static bool usedL[3], usedS[3];
      int id = (int)(s.magic - MagicBase);
      if(st1 != 1) usedL[id] = false;
      if(st1 != -1) usedS[id] = false;
      if(st1 == 1 && !usedL[id]) dir = 1;
      if(st1 == -1 && !usedS[id]) dir = -1;
      if(dir != 0 && Filters(s, dir)) { if(dir == 1) usedL[id] = true; else usedS[id] = true; return dir; }
      return 0;
   }
   // pullback: stack aligned, bar dips into EMA(pb) and closes back beyond EMA30 in trend direction
   int i = TfIndex(s.tf);
   int pbk = s.pbEMA == 40 ? 2 : (s.pbEMA == 60 ? 5 : 0);
   double ePb = Buf(hEMA[pbk][i], 1), e30 = Buf(hEMA[0][i], 1);
   double o = iOpen(_Symbol, s.tf, 1), h = iHigh(_Symbol, s.tf, 1), l = iLow(_Symbol, s.tf, 1), c = iClose(_Symbol, s.tf, 1);
   if(st1 == 1 && l <= ePb && c > e30 && c > o) dir = 1;
   if(st1 == -1 && h >= ePb && c < e30 && c < o) dir = -1;
   if(dir != 0 && Filters(s, dir)) return dir;
   return 0;
}

bool Filters(Slot &s, int dir)
{
   if(HtfDir(PERIOD_H4) != dir || HtfDir(PERIOD_D1) != dir) return false;
   if(s.conf1 != PERIOD_CURRENT && Stack(s.conf1, 1) != dir) return false;
   if(s.conf2 != PERIOD_CURRENT && Stack(s.conf2, 1) != dir) return false;
   double adx = Buf(hADX[TfIndex(s.tf)], 1);
   if(s.adxRule == ADX_LT30 && !(adx < 30)) return false;
   if(s.adxRule == ADX_GE25 && !(adx >= 25)) return false;
   if(!InSession(s)) return false;
   if((SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point > MaxSpreadPoints) return false;
   return true;
}

double LotsForRisk(double stopDist)
{
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0 || stopDist <= 0) return 0;
   double money = AccountInfoDouble(ACCOUNT_EQUITY) * RiskPercent / 100.0;
   double lots = money / (stopDist / ts * tv);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), mn = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), mx = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   lots = MathFloor(lots / step) * step;
   return MathMax(mn, MathMin(mx, lots));
}

bool GetPos(const Slot &s, ulong &ticket, int &dir, double &vol, double &sl)
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong t = PositionGetTicket(k);
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == (long)s.magic)
      {
         ticket = t; vol = PositionGetDouble(POSITION_VOLUME); sl = PositionGetDouble(POSITION_SL);
         dir = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1;
         return true;
      }
   }
   return false;
}

void OpenTrade(Slot &s, int dir)
{
   int i = TfIndex(s.tf);
   double atr = Buf(hATR[i], 1);
   if(atr == EMPTY_VALUE || atr <= 0) return;
   double risk = atr * s.slATR * (s.adapt ? (0.7 + 0.6 * VolPct(s.tf)) : 1.0);
   double level = iClose(_Symbol, s.tf, 1);
   double sl = level - dir * risk;
   double lots = LotsForRisk(risk);
   if(lots <= 0) return;
   trade.SetExpertMagicNumber(s.magic);
   bool ok = dir == 1 ? trade.Buy(lots, _Symbol, 0, sl, 0, "DTC") : trade.Sell(lots, _Symbol, 0, sl, 0, "DTC");
   if(ok)
   {
      s.risk = risk; s.levelPx = level; s.entryPx = trade.ResultPrice();
      s.best = s.entryPx; s.mfeR = 0; s.tp1Done = (s.tp1R <= 0);
   }
}

void Manage(Slot &s)
{
   ulong t; int dir; double vol, sl;
   if(!GetPos(s, t, dir, vol, sl)) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double px = dir == 1 ? bid : ask;
   s.best = dir == 1 ? MathMax(s.best, px) : MathMin(s.best, px);
   s.mfeR = MathMax(s.mfeR, (px - s.entryPx) * dir / s.risk);
   trade.SetExpertMagicNumber(s.magic);
   double newSL = sl;
   // TP1 partial
   if(!s.tp1Done && (px - s.levelPx) * dir >= s.tp1R * s.risk)
   {
      double part = MathFloor(vol * s.tp1Frac / SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP)) * SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      if(part >= SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN)) trade.PositionClosePartial(t, part);
      s.tp1Done = true;
      double lk = s.entryPx + dir * s.lockR * s.risk;
      if((dir == 1 && lk > newSL) || (dir == -1 && lk < newSL)) newSL = lk;
   }
   // profit-lock giveback
   if(s.gbA > 0 && s.mfeR >= s.gbA)
   {
      double lk = s.entryPx + dir * (1.0 - s.gbG) * s.mfeR * s.risk;
      if((dir == 1 && lk > newSL) || (dir == -1 && lk < newSL)) newSL = lk;
   }
   // runner management on runner-TF bar close
   if(NewBar(s.runTF, s.lastRunBar))
   {
      if(s.trail > 0)
      {
         double atrR = Buf(hATR[TfIndex(s.runTF)], 1);
         double ns = s.best - dir * s.trail * atrR;
         if((dir == 1 && ns > newSL) || (dir == -1 && ns < newSL)) newSL = ns;
      }
      if(s.brk && Stack(s.runTF, 1) != dir) { trade.PositionClose(t); return; }
   }
   if(MathAbs(newSL - sl) > _Point)
   {
      double stopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
      if((dir == 1 && newSL < bid - stopLevel) || (dir == -1 && newSL > ask + stopLevel))
         trade.PositionModify(t, NormalizeDouble(newSL, _Digits), 0);
   }
}

void Load(int k, bool on, ENUM_TIMEFRAMES tf, int en, int pb, ENUM_TIMEFRAMES c1, ENUM_TIMEFRAMES c2, int adx, int sf, int stt,
          double slk, bool ad, double r1, double f1, double lk, ENUM_TIMEFRAMES rt, double tr, bool br, double ga, double gg)
{
   S[k].on = on; S[k].tf = tf; S[k].entry = en; S[k].pbEMA = pb; S[k].conf1 = c1; S[k].conf2 = c2; S[k].adxRule = adx;
   S[k].sFrom = sf; S[k].sTo = stt; S[k].slATR = slk; S[k].adapt = ad; S[k].tp1R = r1; S[k].tp1Frac = f1; S[k].lockR = lk;
   S[k].runTF = rt; S[k].trail = tr; S[k].brk = br; S[k].gbA = ga; S[k].gbG = gg; S[k].magic = MagicBase + k;
   S[k].lastBar = 0; S[k].lastRunBar = 0; S[k].tp1Done = true;
   TfIndex(tf); TfIndex(rt); TfIndex(PERIOD_H4); TfIndex(PERIOD_D1);
   if(c1 != PERIOD_CURRENT) TfIndex(c1);
   if(c2 != PERIOD_CURRENT) TfIndex(c2);
}

int OnInit()
{
   Load(0, S1_Enable, S1_TF, S1_Entry, S1_PbEMA, S1_Conf1, S1_Conf2, S1_Adx, S1_SessFrom, S1_SessTo, S1_SL_ATR, S1_SL_Adapt,
        S1_TP1_R, S1_TP1_Frac, S1_Lock_R, S1_RunTF, S1_Trail, S1_Break, S1_GB_A, S1_GB_G);
   Load(1, S2_Enable, S2_TF, S2_Entry, S2_PbEMA, S2_Conf1, S2_Conf2, S2_Adx, S2_SessFrom, S2_SessTo, S2_SL_ATR, S2_SL_Adapt,
        S2_TP1_R, S2_TP1_Frac, S2_Lock_R, S2_RunTF, S2_Trail, S2_Break, S2_GB_A, S2_GB_G);
   Load(2, S3_Enable, S3_TF, S3_Entry, S3_PbEMA, S3_Conf1, S3_Conf2, S3_Adx, S3_SessFrom, S3_SessTo, S3_SL_ATR, S3_SL_Adapt,
        S3_TP1_R, S3_TP1_Frac, S3_Lock_R, S3_RunTF, S3_Trail, S3_Break, S3_GB_A, S3_GB_G);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   for(int k = 0; k < 3; k++)
   {
      if(!S[k].on) continue;
      Manage(S[k]);
      if(NewBar(S[k].tf, S[k].lastBar))
      {
         ulong t; int d; double v, sl;
         if(GetPos(S[k], t, d, v, sl)) continue;          // one position per slot
         int sig = Signal(S[k]);
         if(sig != 0) OpenTrade(S[k], sig);
      }
   }
}
//+------------------------------------------------------------------+
