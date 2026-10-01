from common import *
from scipy.stats import spearmanr
for f in ["h4_er30","h1_z20","m15_ret12","day_rng_atr"]:
    print("==",f)
    for s in ["F8","F9","F10","F11"]:
        rows=slot_rows(s); y=RF[li_(rows),73]; x=F[f].values[rows]; q=T[rows].tz_localize(None).to_period("Q").astype(str).values
        b=pd.qcut(x,3,labels=False); mt=pd.Series(y).groupby(b).mean().round(2).values
        lowq=[round(y[(q==k)&(b==0)].mean()-y[(q==k)&(b>0)].mean(),2) for k in np.unique(q)]
        print(s,"n",len(rows),"IC",round(spearmanr(x,y)[0],3),"terciles",mt,"low-minus-rest by Q",lowq)
