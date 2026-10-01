from common import *
pd.set_option('display.width',250)
C={"base":1208,"3R":2168,"2R":1928,"k90_2R":3128,"3R_noPart_be1":2288,"3R_h30_be1_ts":2369,"k50_runner_be1":128,"1R":1688}
tab={}
for k,j in C.items():
    i,r=run(j); tab[k]=monthly(i,r); print(k,j,short(met(i,r)))
print(pd.DataFrame(tab).round(1).to_string())
# hold time & rate per signal
for k,j in C.items():
    v=IN25; print(k, "meanR/sig %.3f  hold_mean_h %.1f  R/day_in_mkt %.3f"%(RR[v,j].mean(), (XX[v,j]-M1[v]).mean()/60, RR[v,j].sum()/((XX[v,j]-M1[v]).sum()/1440)))
