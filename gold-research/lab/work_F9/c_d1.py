exec(open('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/common.py').read())
print(pd.Series(F.d1_stack.values[f9]).value_counts())
for J in [B,3692]:
  for sl in ['F8','F9','F10','F11']:
    rows=np.where((S.slot==sl)&(lab.TIME>=lab.D0))[0]; y=np.asarray(R_[rows,J]); x=F.d1_stack.values[rows]
    q=lab.TIME[rows].tz_localize(None).to_period('Q').astype(str)
    t=pd.DataFrame({'y':y,'x':x,'q':q}).pivot_table(index='x',columns='q',values='y',aggfunc='mean').round(2)
    print(J,sl,pd.Series(y).groupby(x).agg(['mean','count']).round(3).to_dict()); 
    if sl=='F9': print(t)
# causal rule: skip d1_stack value whose past (pooled fade or F9) shrunk mean < 0
for J,ch in [(B,None),(3692,3692)]:
  for pool,rows in [('F9',f9),('fade',fade)]:
    y=np.asarray(R_[rows,J]); kn=np.asarray(X_[rows,J]); x=F.d1_stack.values[rows]
    m=lab.M1[rows]; ms=lab._ms(); take=np.ones(len(rows),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m>=a)&(m<b); tr=kn<a
        for v in [-1,0,1]:
            s=tr&(x==v); mu=(y[s].sum()+10*y[tr].mean())/(s.sum()+10) if tr.sum()>30 else 1
            take[te&(x==v)]=mu>0 if tr.sum()>30 else True
    T=np.ones(N,bool); T[rows]=take
    show(f'J={J} causal d1_stack rule pool={pool}',ch,T)
  T=np.ones(N,bool); T[f9]=F.d1_stack.values[f9]>=0; show(f'J={J} IN-SAMPLE fixed skip d1_stack<0',ch,T)
  T=np.ones(N,bool); T[f9]=F.d1_stack.values[f9]>0; show(f'J={J} IN-SAMPLE fixed skip d1_stack<=0',ch,T)
