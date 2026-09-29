exec(open("adapt.py").read().split('row("fixed 2%"')[0])
def simk(R, N=100, frac=0.5, mx=5, mn=1, cap=15, fdd=0.2, use_dd=True, start=0, med=False):
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set(); hist = []
    for t, typ, i in EV:
        if TI[i] < start: continue
        if typ == 0:
            if i in open_: eq += open_.pop(i) * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
            hist.append(R[i])   # every resolved signal (taken or not) is market information
            continue
        if SL[i] in busy: continue
        h = np.array(hist[-N:])
        if len(h) < N // 2: rp = mn
        else:
            m = np.median(h) if med else h.mean(); v = h.var()
            k = max(0.0, m / v) if v > 0 else 0.0   # Kelly fraction of equity per 1R
            rp = np.clip(frac * k * 100, mn, mx)
        if use_dd: rp = mn + (rp - mn) * max(0.0, 1 - (1 - eq / peak) / fdd)
        room = eq * cap / 100 - sum(v for j, v in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(eq * rp / 100, room); busy.add(SL[i])
    return eq - 1, mdd
def rowk(name, **kw):
    a = simk(R0, **kw); b = simk(Rw, **kw); c = simk(Rc, **kw); d = simk(R0, start=s26, **kw); e = simk(Rw, start=s26, **kw)
    ws = [simk(Rw, start=s, **kw) for s in starts]
    print(f"{name:26s} full {a[0]*100:+8,.0f}%/{a[1]*100:2.0f}% | weak {b[0]*100:+5,.0f}%/{b[1]*100:2.0f}% | cost$2 {c[0]*100:+6,.0f}%/{c[1]*100:2.0f}% | "
          f"26-02+ {d[0]*100:+4.0f}%/{d[1]*100:2.0f}% weak {e[0]*100:+4.0f}% | worstDD(weak) {max(w[1] for w in ws)*100:2.0f}%", flush=True)
for N in (100, 300):
    for frac in (0.25, 0.5):
        for dd in (True, False):
            rowk(f"kelly N{N} x{frac} dd{int(dd)}", N=N, frac=frac, use_dd=dd)
