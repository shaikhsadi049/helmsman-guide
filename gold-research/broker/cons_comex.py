import pickle, pandas as pd, numpy as np
exec(open("eq_comex.py").read().split("TODAY =")[0])
TD = pickle.load(open("tick_dyn.pkl", "rb"))
def dyn(slot, spec, adx):
    d = TD[(slot, spec)]; return pd.DataFrame(dict(t=d.t, R=d.R * (d.w if adx else 1)))
parts = [taken("S1","today"), dyn("S2","A3",True), dyn("S3","A3",False), dyn("S4","B",True), taken("S5","today"),
         dyn("S6","A3",False).assign(R=lambda x: x.R*.5), taken("S7","recommended").assign(R=lambda x: x.R*.5)]
parts += [taken(f,"recommended") for f in ("F8","F9","F10")] + [taken("F11","today").assign(R=lambda x: x.R*.5)]
print("consensus on COMEX", rep(pd.concat(parts)))
