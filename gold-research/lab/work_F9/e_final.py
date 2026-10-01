exec(open('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/common.py').read())
import json
ch=adaptive_exit()
def P(j): return {k:v for k,v in lab.P[j].items() if k!='kind'}
mb,rb,Rb=lab.evaluate('F9'); mr,rr,Rr=lab.evaluate('F9',ch); mi,ri,Ri=lab.evaluate('F9',3695)
T=np.ones(N,bool); T[f9]=F.d1_stack.values[f9]>=0; mi2,_,_=lab.evaluate('F9',3692,T)
def mon(rr,R): t=lab.TIME[rr].tz_localize(None).to_period('M'); return pd.Series(R,index=t).groupby(level=0).sum()
tab=pd.DataFrame({'base_n':pd.Series(1,index=lab.TIME[rb].tz_localize(None).to_period('M')).groupby(level=0).sum(),'base_R':mon(rb,Rb),'rec_n':pd.Series(1,index=lab.TIME[rr].tz_localize(None).to_period('M')).groupby(level=0).sum(),'rec_R':mon(rr,Rr),'IS_R':mon(ri,Ri)}).fillna(0).round(2)
print(tab.to_string())
r9=f9[lab.TIME[f9]>=lab.D0]; mm=lab.TIME[r9].tz_localize(None).to_period('M')
print(pd.Series([str(P(j)) for j in ch[r9]],index=mm).groupby(level=0).first().to_string())
tab.to_csv('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/monthly.csv')
clean=lambda m:{k:(v.item() if hasattr(v,'item') else v) for k,v in m.items()}
json.dump(dict(base=clean(mb),rec=clean(mr),IS=clean(mi),IS_d1=clean(mi2)),open('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/final_metrics.json','w'),indent=1)
print(mr); print(mi); print(mi2)
