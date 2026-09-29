exec(open("adapt.py").read().split('row("fixed 2%"')[0])
def simw(R, mode, mx=5, mn=1, cap=15, fdd=0.2, N=300, kfrac=0.5, start=0, fixed=None, measure_from=None):
    """mode: 'dd*edge' (current EA), 'tr+k all' (Kelly on all signals, warm), 'kelly all', 'fixed'.
    measure_from: run from the beginning but report return/DD after this entry index (already running)."""
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set(); hist = []; eq0 = None; pk2 = None; mdd2 = 0
    for t, typ, i in EV:
        live = TI[i] >= start
        if typ == 0:
            if i in open_:
                eq += open_.pop(i) * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
                if pk2 is not None: pk2 = max(pk2, eq); mdd2 = max(mdd2, 1 - eq / pk2)
            hist.append(R[i]); continue
        if not live: continue
        if measure_from is not None and eq0 is None and TI[i] >= measure_from: eq0 = eq; pk2 = eq
        if SL[i] in busy: continue
        xdd = max(0.0, 1 - (1 - eq / peak) / fdd)
        if mode == "fixed": rp = fixed
        elif mode == "dd*edge": rp = mn + (mx - mn) * xdd * (0.5 + 0.5 * np.clip((ED[i] - 0.73) / 1.87, 0, 1))
        else:
            h = np.array(hist[-N:]); kx = 0.0
            if len(h) >= N // 2 and h.var() > 0: kx = np.clip((kfrac * max(0, h.mean() / h.var()) * 100 - mn) / (mx - mn), 0, 1)
            x = xdd * ((DT[i] + kx) / 2 if mode == "tr+k" else kx if mode == "k" else DT[i])
            rp = mn + (mx - mn) * x
        room = eq * cap / 100 - sum(v for j, v in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(eq * rp / 100, room); busy.add(SL[i])
    if measure_from is not None: return eq / eq0 - 1, mdd2
    return eq - 1, mdd
def roww(name, **kw):
    sc = {"full": simw(R0, **kw), "weak": simw(Rw, **kw), "cost$2": simw(Rc, **kw),
          "new@26-02": simw(R0, start=s26, **kw), "new@26-02 weak": simw(Rw, start=s26, **kw),
          "running,26-02+": simw(R0, measure_from=s26, **kw), "running,26-02+ weak": simw(Rw, measure_from=s26, **kw)}
    ws = [simw(Rw, start=s, **kw) for s in starts]
    print(f"{name:14s} " + " | ".join(f"{k} {v[0]*100:+6,.0f}%/{v[1]*100:2.0f}%" for k, v in sc.items()) + f" || worstDD {max([v[1] for v in sc.values()] + [w[1] for w in ws])*100:2.0f}%", flush=True)
for mx in (5, 3):
    print(f"--- max {mx}")
    roww("dd*edge", mode="dd*edge", mx=mx)
    roww("trend x dd", mode="tr", mx=mx)
    roww("kelly x dd", mode="k", mx=mx)
    roww("(tr+k) x dd", mode="tr+k", mx=mx)
print("--- fixed"); roww("fixed 2%", mode="fixed", fixed=2); roww("fixed 1.5%", mode="fixed", fixed=1.5)
