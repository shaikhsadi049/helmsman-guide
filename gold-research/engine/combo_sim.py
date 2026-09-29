import numpy as np, pandas as pd
A_ = pd.read_parquet("../combo_trades.parquet")
def prep(df):
    SL = df.slot.values; TI = df.t_in.values; TO = df.t_out.values; TL = df.t_lock.values; DT = df.d_trend.values; MRk = (df.kind == "mr").values
    EV = sorted([(a, 1, i) for i, a in enumerate(TI)] + [(b, 0, i) for i, b in enumerate(TO)])
    return SL, TI, TO, TL, DT, MRk, EV
def sim(df, R, mx=5, mn=1, fdd=0.2, cap=15, mr_mode="inv", start=0, fixed=None, P=None):
    SL, TI, TO, TL, DT, MRk, EV = P if P is not None else prep(df)
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set(); n = 0; curve = []
    for t, typ, i in EV:
        if TI[i] < start: continue
        if typ == 0:
            if i in open_: eq += open_.pop(i) * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak); curve.append((i, eq))
            continue
        if SL[i] in busy: continue
        xdd = max(0.0, 1 - (1 - eq / peak) / fdd)
        if fixed: rp = fixed
        else:
            tr = DT[i]
            if MRk[i]: tr = (1 - tr) if mr_mode == "inv" else 0.5 if mr_mode == "half" else tr
            rp = mn + (mx - mn) * xdd * tr
        room = eq * cap / 100 - sum(v for j, v in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(eq * rp / 100, room); busy.add(SL[i]); n += 1
    return eq - 1, mdd, n, curve
if __name__ == "__main__":
    starts_m = pd.date_range("2025-01-01", "2026-04-01", freq="MS", tz="UTC")
    def row(name, df, **kw):
        df = df.reset_index(drop=True); P = prep(df)
        R0 = df.R.values; Rw = np.where(R0 > 0, R0 * .5, R0); Rc = R0 - 1.66 / df.risk.values
        s26 = df.t_in.values[np.searchsorted(df.time.values, np.datetime64(pd.Timestamp("2026-02-01", tz="UTC")))]
        a = sim(df, R0, P=P, **kw); b = sim(df, Rw, P=P, **kw); c = sim(df, Rc, P=P, **kw); d = sim(df, R0, start=s26, P=P, **kw); e = sim(df, Rw, start=s26, P=P, **kw)
        ws = [sim(df, Rw, start=df.t_in.values[np.searchsorted(df.time.values, np.datetime64(m))], P=P, **kw)[1] for m in starts_m]
        # months negative
        cv = pd.DataFrame(a[3], columns=["i", "eq"]); cv["m"] = pd.DatetimeIndex(df.time.values[cv.i.values]).tz_localize(None).to_period("M") if df.time.dt.tz is None else df.time.dt.tz_localize(None).dt.to_period("M").values[cv.i.values]
        me = cv.groupby("m").eq.last(); mret = me.pct_change().fillna(me.iloc[0] - 1)
        print(f"{name:34s} trades/yr {a[2]/1.55:4.0f} | full {a[0]*100:+7,.0f}%/{a[1]*100:2.0f}% | weak {b[0]*100:+5,.0f}%/{b[1]*100:2.0f}% | cost$2 {c[0]*100:+6,.0f}%/{c[1]*100:2.0f}% | "
              f"26-02+ {d[0]*100:+4.0f}%/{d[1]*100:2.0f}% weak {e[0]*100:+4.0f}% | worstDD {max(ws)*100:2.0f}% | losing months {(mret<0).sum()}/{len(mret)}", flush=True)
    tr = A_[A_.kind == "trend"]
    for mx in (5, 3):
        print(f"--- max {mx}")
        row("trend S1-S6 only", tr, mx=mx)
        row("trend + 4 MR (MR risk ~ 1-trend)", A_, mx=mx, mr_mode="inv")
        row("trend + 4 MR (MR risk ~ trend)", A_, mx=mx, mr_mode="same")
        row("trend + 4 MR (MR risk half)", A_, mx=mx, mr_mode="half")
        for j in range(4):
            row(f"trend + MR{j+1} only (inv)", A_[(A_.kind == "trend") | (A_.slot == 10 + j)], mx=mx, mr_mode="inv")
    print("--- MR alone")
    row("4 MR alone, fixed 2%", A_[A_.kind == "mr"], fixed=2)
