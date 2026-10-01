"""Rule generator: yields (family, name, formula, L_full, S_full) on the FULL history of a timeframe (cut to table rows later)."""
import numpy as np, pandas as pd, talib
import engine as E
def osc_list(o, h, l, c, v):
    out = {}
    for n in (2, 5, 14, 30): out[f"RSI({n})"] = talib.RSI(c, n)
    for n in (14, 30): out[f"CCI({n})"] = talib.CCI(h, l, c, n); out[f"WILLR({n})"] = talib.WILLR(h, l, c, n); out[f"MFI({n})"] = talib.MFI(h, l, c, v, n)
    for n in (10, 30): out[f"ROC({n})"] = talib.ROC(c, n); out[f"CMO({n})"] = talib.CMO(c, n)
    k, d = talib.STOCH(h, l, c, 14, 3, 0, 3, 0); out["STOCH(14,3,3).k"] = k
    fk, fd = talib.STOCHRSI(c, 14, 5, 3, 0); out["STOCHRSI(14,5,3).k"] = fk
    out["ULTOSC(7,14,28)"] = talib.ULTOSC(h, l, c, 7, 14, 28)
    m, s, hst = talib.MACD(c, 12, 26, 9); out["MACD(12,26,9).hist"] = hst; out["MACD(12,26,9).line"] = m
    out["PPO(12,26)"] = talib.PPO(c, 12, 26); out["TRIX(15)"] = talib.TRIX(c, 15); out["APO(12,26)"] = talib.APO(c, 12, 26)
    out["AROONOSC(14)"] = talib.AROONOSC(h, l, 14); out["AROONOSC(50)"] = talib.AROONOSC(h, l, 50)
    out["BOP"] = pd.Series(talib.BOP(o, h, l, c)).rolling(5).mean().values
    out["ADX(14)*sign(DI)"] = talib.ADX(h, l, c, 14) * np.sign(talib.PLUS_DI(h, l, c, 14) - talib.MINUS_DI(h, l, c, 14))
    out["LINEARREG_SLOPE(20)/ATR"] = talib.LINEARREG_SLOPE(c, 20) / talib.ATR(h, l, c, 14)
    out["(C-EMA50)/ATR"] = (c - talib.EMA(c, 50)) / talib.ATR(h, l, c, 14)
    out["(C-EMA200)/ATR"] = (c - talib.EMA(c, 200)) / talib.ATR(h, l, c, 14)
    out["Z(C,20)"] = (c - talib.SMA(c, 20)) / talib.STDDEV(c, 20)
    out["OBV slope(20)"] = talib.LINEARREG_SLOPE(talib.OBV(c, v), 20)
    out["ADOSC(3,10)"] = talib.ADOSC(h, l, c, v, 3, 10)
    out["HT_DCPHASE"] = talib.HT_DCPHASE(c)
    return out
MAS = {"EMA": talib.EMA, "SMA": talib.SMA, "WMA": talib.WMA, "DEMA": talib.DEMA, "TEMA": talib.TEMA, "KAMA": talib.KAMA, "T3": lambda x, n: talib.T3(x, n), "TRIMA": talib.TRIMA}
def generate(T):
    o, h, l, c, v = T.o, T.h, T.l, T.c, T.v
    # ---- F1 oscillator thresholds on market-adaptive levels (rolling percentile of the indicator itself)
    for name, x in osc_list(o, h, l, c, v).items():
        p = E.prank(x, 500)
        for lv in (0.8, 0.9, 0.95):
            up, dn = E.cross_up(p, lv), E.cross_dn(p, 1 - lv)
            yield "osc_mom", f"{name} pct>{lv}", f"LONG when pctrank500({name}) crosses above {lv}; SHORT when it crosses below {1-lv:.2f}", up, dn
            yield "osc_rev", f"{name} pct<{1-lv:.2f}", f"LONG when pctrank500({name}) crosses below {1-lv:.2f}; SHORT when it crosses above {lv}", dn, up
    # ---- F2 moving-average crosses and price-MA crosses
    for mname, f in MAS.items():
        for a, b in ((5, 20), (10, 30), (20, 50), (50, 200), (9, 21), (13, 48)):
            fa, fb = f(c, a), f(c, b); x = fa - fb
            yield "ma_cross", f"{mname}({a})x{mname}({b})", f"LONG when {mname}({a}) crosses above {mname}({b}); SHORT on cross below", E.cross_up(x, 0), E.cross_dn(x, 0)
        for n in (20, 50, 100):
            x = c - f(c, n)
            yield "price_ma", f"C x {mname}({n})", f"LONG when close crosses above {mname}({n}); SHORT on cross below", E.cross_up(x, 0), E.cross_dn(x, 0)
    sar = talib.SAR(h, l, 0.02, 0.2); x = c - sar
    yield "ma_cross", "PSAR flip", "LONG when close crosses above Parabolic SAR(0.02,0.2); SHORT on cross below", E.cross_up(x, 0), E.cross_dn(x, 0)
    # ---- F3 channels: breakouts and fades
    atr = talib.ATR(h, l, c, 14)
    for n in (10, 20, 55, 100):
        hh = pd.Series(h).rolling(n).max().shift(1).values; ll = pd.Series(l).rolling(n).min().shift(1).values
        yield "chan_brk", f"Donchian({n}) breakout", f"LONG when close > highest high of previous {n} bars; SHORT when close < lowest low", c > hh, c < ll
        yield "chan_fade", f"Donchian({n}) false break", f"SHORT when high > prev-{n} high but close back below it; LONG mirror", (l < ll) & (c > ll), (h > hh) & (c < hh)
    for n, k in ((20, 2.0), (20, 2.5), (50, 2.0)):
        up_, mid, lo_ = talib.BBANDS(c, n, k, k, 0)
        yield "chan_brk", f"Bollinger({n},{k}) breakout", f"LONG when close crosses above upper band BB({n},{k}); SHORT below lower", E.cross_up(c - up_, 0), E.cross_dn(c - lo_, 0)
        yield "chan_fade", f"Bollinger({n},{k}) re-entry", f"LONG when close crosses back above lower band BB({n},{k}); SHORT when back below upper", E.cross_up(c - lo_, 0), E.cross_dn(c - up_, 0)
    for n, k in ((20, 1.5), (20, 2.5)):
        mid = talib.EMA(c, n); up_ = mid + k * atr; lo_ = mid - k * atr
        yield "chan_brk", f"Keltner({n},{k}) breakout", f"LONG when close crosses above EMA{n}+{k}ATR; SHORT below EMA{n}-{k}ATR", E.cross_up(c - up_, 0), E.cross_dn(c - lo_, 0)
        yield "chan_fade", f"Keltner({n},{k}) re-entry", f"LONG when close crosses back above EMA{n}-{k}ATR; SHORT back below EMA{n}+{k}ATR", E.cross_up(c - lo_, 0), E.cross_dn(c - up_, 0)
    # squeeze release: BB width in the lowest 20% of its last 500, then a close outside the band
    up_, mid, lo_ = talib.BBANDS(c, 20, 2, 2, 0); bw = E.prank((up_ - lo_) / mid, 500); sq = pd.Series(bw < 0.2).rolling(10).max().values.astype(bool)
    yield "squeeze", "Squeeze release BB(20,2)", "after BB(20,2) width was in the lowest 20% (rank over 500 bars) in the last 10 bars: LONG close crosses above upper band, SHORT below lower", sq & E.cross_up(c - up_, 0), sq & E.cross_dn(c - lo_, 0)
    nr = (h - l) <= pd.Series(h - l).rolling(7).min().values
    hh1 = np.r_[np.nan, h[:-1]]; ll1 = np.r_[np.nan, l[:-1]]; nr1 = np.r_[False, nr[:-1]]
    yield "squeeze", "NR7 breakout", "previous bar had the narrowest range of 7: LONG when close > its high, SHORT when close < its low", nr1 & (c > hh1), nr1 & (c < ll1)
    # ---- F4 candlestick patterns (TA-Lib): +100 bullish / -100 bearish
    for fn in talib.get_function_groups()["Pattern Recognition"]:
        x = getattr(talib, fn)(o, h, l, c)
        if (x != 0).sum() < 30: continue
        yield "candle", fn, f"LONG when {fn} = +100 (bullish), SHORT when -100 (bearish)", x > 0, x < 0
        yield "candle_rev", fn + " (inverse)", f"LONG when {fn} = -100, SHORT when +100 (fade the pattern)", x < 0, x > 0
def gates(T):
    """causal context gates; each returns (long_ok, short_ok) on table rows"""
    ema = lambda n: (lambda b: talib.EMA(b.close.values, n))
    h4f = T.htf("4h", ema(20)); h4s = T.htf("4h", ema(50)); d1f = T.htf("1D", ema(20)); d1s = T.htf("1D", ema(50))
    def stack(b):
        c = b.close.values; e = [talib.EMA(c, n) for n in (30, 35, 40, 45, 50, 60)]
        bu = np.all([e[i] > e[i + 1] for i in range(5)], axis=0); be = np.all([e[i] < e[i + 1] for i in range(5)], axis=0)
        return bu.astype(float) - be.astype(float)
    h4st = T.htf("4h", stack)
    atrr = E.prank(talib.ATR(T.h, T.l, T.c, 14), 500)[T.pos]
    adx = talib.ADX(T.h, T.l, T.c, 14)[T.pos]
    sess = (T.hour >= 7) & (T.hour < 20); one = np.ones(len(T.B), bool)
    return {"none": (one, one), "H4trend": (h4f > h4s, h4f < h4s), "D1trend": (d1f > d1s, d1f < d1s),
            "H4+D1trend": ((h4f > h4s) & (d1f > d1s), (h4f < h4s) & (d1f < d1s)), "H4flat": (h4st == 0, h4st == 0),
            "session": (sess, sess), "volHigh": (atrr > 0.5, atrr > 0.5), "volLow": (atrr <= 0.5, atrr <= 0.5),
            "ADX>25": (adx > 25, adx > 25), "ADX<20": (adx < 20, adx < 20)}
