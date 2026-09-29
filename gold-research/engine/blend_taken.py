exec(open("adapt.py").read().split('row("fixed 2%"')[0])
def simt(R, mx=5, mn=1, cap=15, fdd=0.2, N=100, kfrac=0.5, start=0, taken_only=True, neutral=0.5, minn=None):
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set(); hist = []
    minn = minn or N // 2
    for t, typ, i in EV:
        if TI[i] < start: continue
        if typ == 0:
            if i in open_: eq += open_.pop(i) * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak); hist.append(R[i])
            elif not taken_only: hist.append(R[i])
            continue
        if SL[i] in busy: continue
        xdd = max(0.0, 1 - (1 - eq / peak) / fdd)
        h = np.array(hist[-N:]); kx = neutral
        if len(h) >= minn and h.var() > 0: kx = np.clip((kfrac * max(0, h.mean() / h.var()) * 100 - mn) / (mx - mn), 0, 1)
        rp = mn + (mx - mn) * xdd * (DT[i] + kx) / 2
        room = eq * cap / 100 - sum(v for j, v in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(eq * rp / 100, room); busy.add(SL[i])
    return eq - 1, mdd
def rowt(name, **kw):
    sc = {"full": simt(R0, **kw), "weak": simt(Rw, **kw), "cost$2": simt(Rc, **kw), "26+": simt(R0, start=s26, **kw), "26+weak": simt(Rw, start=s26, **kw)}
    ws = [simt(Rw, start=s, **kw) for s in starts]
    print(f"{name:26s} " + " | ".join(f"{k} {v[0]*100:+7,.0f}%/{v[1]*100:2.0f}%" for k, v in sc.items()) + f" || worst DD any start {max([v[1] for v in sc.values()] + [w[1] for w in ws])*100:2.0f}%", flush=True)
rowt("all signals N300", N=300, taken_only=False, neutral=0.0)
for N in (30, 50, 100, 200):
    for neu in (0.0, 0.5):
        rowt(f"taken N{N} neutral{neu}", N=N, neutral=neu, minn=min(20, N))
