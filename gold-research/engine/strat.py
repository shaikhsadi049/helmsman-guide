"""Signal / stop / exit builders for DTC variants."""
import numpy as np
import pandas as pd
import engine as E

COST_RT = 0.34  # USD per oz round trip: ~0.30 spread + 2x2 ticks slippage


class Feat:
    def __init__(self, df, htf_rules=("1h", "4h", "1D")):
        self.df = df
        c = df.close
        self.emas = {n: E.ema(c, n) for n in (20, 30, 35, 40, 45, 50, 60)}
        e = self.emas
        self.bull = ((e[30] > e[35]) & (e[35] > e[40]) & (e[40] > e[45]) & (e[45] > e[50]) & (e[50] > e[60])).values
        self.bear = ((e[30] < e[35]) & (e[35] < e[40]) & (e[40] < e[45]) & (e[45] < e[50]) & (e[50] < e[60])).values
        self.atr = E.atr(df, 14).values
        a, pdi, mdi = E.adx(df, 14)
        self.adx = a.values
        self.htf = {}
        for r in htf_rules:
            try:
                self.htf[r] = E.htf_bull(df, r).values
            except Exception:
                pass
        self.hour = df.index.hour.values
        self.o, self.h, self.l, self.c = (df.open.values, df.high.values, df.low.values, df.close.values)
        self._swing = {}

    def swing(self, n):
        if n not in self._swing:
            self._swing[n] = (self.df.low.rolling(n).min().values, self.df.high.rolling(n).max().values)
        return self._swing[n]


def prev(a):
    b = np.roll(a, 1)
    b[0] = False
    return b


def filters(F, adx_min=0, htf=(), sess=None, dir_=1):
    ok = np.ones(len(F.c), bool)
    if adx_min > 0:
        ok &= F.adx >= adx_min
    for r in htf:
        ok &= F.htf[r] if dir_ == 1 else ~F.htf[r]
    if sess is not None:
        a, b = sess
        ok &= (F.hour >= a) & (F.hour < b)
    return ok


def signals(F, entry="flip_alt", adx_min=0, htf=(), sess=None, pb_ema=30, orig_atr_filter=True):
    bull, bear = F.bull, F.bear
    fl = filters(F, adx_min, htf, sess, 1)
    fs = filters(F, adx_min, htf, sess, -1)
    n = len(bull)
    if entry == "flip_alt":            # original DTC: flip + alternate + ATR>0.5
        raw_l = bull & ~prev(bull) & fl
        raw_s = bear & ~prev(bear) & fs
        if orig_atr_filter:
            raw_l &= F.atr > 0.5
            raw_s &= F.atr > 0.5
        L = np.zeros(n, bool); S = np.zeros(n, bool); st = 0
        for i in range(n):
            if raw_l[i] and st != 1:
                L[i] = True; st = 1
            elif raw_s[i] and st != -1:
                S[i] = True; st = -1
        return L, S
    if entry == "flip":                # flip bar only, no alternation rule
        return bull & ~prev(bull) & fl, bear & ~prev(bear) & fs
    if entry == "swing":               # first bar per swing where stack + filters agree
        L = np.zeros(n, bool); S = np.zeros(n, bool); ul = us = False
        cl = bull & fl; cs = bear & fs
        for i in range(n):
            if not bull[i]: ul = False
            if not bear[i]: us = False
            if cl[i] and not ul:
                L[i] = True; ul = True
            elif cs[i] and not us:
                S[i] = True; us = True
        return L, S
    if entry == "pullback":            # trend stack + price dips into EMA zone and closes back beyond EMA30
        e = F.emas[pb_ema].values
        e30 = F.emas[30].values
        L = bull & fl & (F.l <= e) & (F.c > e30) & (F.c > F.o)
        S = bear & fs & (F.h >= e) & (F.c < e30) & (F.c < F.o)
        return L, S
    raise ValueError(entry)


def stops(F, mode="pct", val=0.25, swing_n=8, buf=0.2):
    c = F.c
    if mode == "pct":
        d = c * val / 100
        return d, d
    if mode == "atr":
        d = F.atr * val
        return d, d
    if mode == "swing":
        lo, hi = F.swing(swing_n)
        dl = c - lo + buf * F.atr
        ds = hi - c + buf * F.atr
        dl = np.where(dl > 0.2 * F.atr, dl, F.atr * 1.5)
        ds = np.where(ds > 0.2 * F.atr, ds, F.atr * 1.5)
        return dl, ds
    raise ValueError(mode)


EXITS = {
    "orig4":       dict(tp_r=[1, 2, 3, 4], tp_frac=[.25, .25, .25, .25], be_leg=0, trail=0, brk=False),
    "orig4_be":    dict(tp_r=[1, 2, 3, 4], tp_frac=[.25, .25, .25, .25], be_leg=1, trail=0, brk=False),
}


def exit_cfg(name):
    if name in EXITS:
        return EXITS[name]
    kind, *p = name.split(":")
    if kind == "tp":                   # single TP at R
        return dict(tp_r=[float(p[0])], tp_frac=[1.0], be_leg=0, trail=0, brk=False)
    if kind == "tp_brk":               # single TP, or earlier exit on trend break
        return dict(tp_r=[float(p[0])], tp_frac=[1.0], be_leg=0, trail=0, brk=True)
    if kind == "brk":                  # no TP; exit when stack breaks
        return dict(tp_r=[999.0], tp_frac=[1.0], be_leg=0, trail=0, brk=True)
    if kind == "trail":                # no TP; ATR chandelier trail
        return dict(tp_r=[999.0], tp_frac=[1.0], be_leg=0, trail=float(p[0]), brk=False)
    if kind == "half":                 # half at R1 + BE, runner by trail (m) or trend break (m=0)
        r1, m = float(p[0]), float(p[1])
        return dict(tp_r=[r1, 999.0], tp_frac=[.5, .5], be_leg=1, trail=m, brk=(m == 0))
    if kind == "scale":                # R1 part f, rest at R2, BE after first
        r1, f, r2 = float(p[0]), float(p[1]), float(p[2])
        return dict(tp_r=[r1, r2], tp_frac=[f, 1 - f], be_leg=1, trail=0, brk=False)
    raise ValueError(name)


def backtest(F, entry="flip_alt", adx_min=0, htf=(), sess=None, pb_ema=30, orig_atr_filter=True,
             sl="pct", sl_val=0.25, swing_n=8, exit="orig4", reverse=True, cost=COST_RT, mask=None):
    L, S = signals(F, entry, adx_min, htf, sess, pb_ema, orig_atr_filter)
    if mask is not None:
        L = L & mask; S = S & mask
    dl, ds = stops(F, sl, sl_val, swing_n)
    x = exit_cfg(exit)
    tr = E.run(F.o, F.h, F.l, F.c, L, S, F.bull, F.bear, dl, ds,
               np.array(x["tp_r"], float), np.array(x["tp_frac"], float), x["be_leg"], x["trail"], F.atr,
               x["brk"], reverse, cost)
    return tr
