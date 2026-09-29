exec(open("adapt.py").read().split('row("fixed 2%"')[0])
def simb(R, w_dd=1, w_tr=0, w_k=0, mx=5, mn=1, cap=15, fdd=0.2, N=300, kfrac=0.5, start=0, gate_dd=True, fixed=None):
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set(); hist = []
    for t, typ, i in EV:
        if TI[i] < start: continue
        if typ == 0:
            if i in open_: eq += open_.pop(i) * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
            hist.append(R[i]); continue
        if SL[i] in busy: continue
        if fixed: rp = fixed
        else:
            xdd = max(0.0, 1 - (1 - eq / peak) / fdd)
            h = np.array(hist[-N:]); kx = 0.0
            if len(h) >= N // 2 and h.var() > 0: kx = np.clip((kfrac * max(0, h.mean() / h.var()) * 100 - mn) / (mx - mn), 0, 1)
            parts = [(w_dd, xdd), (w_tr, DT[i]), (w_k, kx)]
            x = sum(w * v for w, v in parts) / sum(w for w, _ in parts)
            if gate_dd: x *= xdd if w_dd == 0 else 1
            rp = mn + (mx - mn) * x
        room = eq * cap / 100 - sum(v for j, v in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(eq * rp / 100, room); busy.add(SL[i])
    return eq - 1, mdd
res = []
def rowb(name, **kw):
    sc = {"full": simb(R0, **kw), "weak": simb(Rw, **kw), "cost$2": simb(Rc, **kw), "26+": simb(R0, start=s26, **kw), "26+weak": simb(Rw, start=s26, **kw)}
    ws = [simb(Rw, start=s, **kw) for s in starts]
    worst_ret = min(v[0] for v in sc.values()); worst_dd = max([v[1] for v in sc.values()] + [w[1] for w in ws])
    print(f"{name:32s} " + " | ".join(f"{k} {v[0]*100:+7,.0f}%/{v[1]*100:2.0f}%" for k, v in sc.items()) + f" || worst ret {worst_ret*100:+4.0f}% worst DD {worst_dd*100:2.0f}%", flush=True)
rowb("fixed 2%", fixed=2); rowb("fixed 1.5%", fixed=1.5)
rowb("dd only (dd*edge~)", w_dd=1)
rowb("dd+trend", w_dd=1, w_tr=1)
rowb("dd+kelly", w_dd=1, w_k=1)
rowb("dd+trend+kelly", w_dd=1, w_tr=1, w_k=1)
rowb("(trend+kelly) x dd", w_dd=0, w_tr=1, w_k=1)
rowb("kelly x dd", w_dd=0, w_k=1)
rowb("trend x dd", w_dd=0, w_tr=1)
for mx in (3, 4):
    rowb(f"dd+trend+kelly max{mx}", w_dd=1, w_tr=1, w_k=1, mx=mx)
    rowb(f"(trend+kelly) x dd max{mx}", w_dd=0, w_tr=1, w_k=1, mx=mx)
