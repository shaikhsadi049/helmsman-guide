from h import *
m,rr,R = lab.evaluate("S1"); print("lab.evaluate", fmt(m))
i, r = run(); print("local", fmt(lab.metrics(r, T[i])))
s = pd.Series(r, index=T[i].tz_localize(None))
mon = s.groupby(s.index.to_period("M")).agg(["count","sum","mean"]); mon["win%"]=s.groupby(s.index.to_period("M")).apply(lambda x:(x>0).mean()*100).round(0)
print(mon.round(2).to_string())
print(s.groupby(s.index.to_period("Q")).agg(["count","sum"]).round(2))
print("all signals 2025+:", in25.sum(), "taken", len(i))
eq=s.cumsum(); dd=eq.cummax()-eq; print("maxDD end", dd.idxmax(), "peak", eq[:dd.idxmax()].idxmax())
print("dist of R:", np.percentile(r,[5,25,50,75,95]).round(2), "top5 trades sum", np.sort(r)[-5:].round(2), r.sum())
# hold time
hold = (X1[i,BASE]-M[i])/60/24; print("hold days median/mean", np.median(hold), hold.mean())
