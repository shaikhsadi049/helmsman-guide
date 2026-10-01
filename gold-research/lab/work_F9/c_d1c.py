exec(open('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/common.py').read())
import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/bt')
day=1440
for J,ch in [(B,None),(3692,3692)]:
  for pool,rows in [('F9',f9),('fade',fade)]:
    for W in [90,180,270]:
        y=np.asarray(R_[rows,J]); kn=np.asarray(X_[rows,J]); x=F.d1_stack.values[rows]; m=lab.M1[rows]; ms=lab._ms(); take=np.ones(len(rows),bool)
        for a,b in zip(ms[:-1],ms[1:]):
            te=(m>=a)&(m<b); tr=(kn<a)&(m>=a-W*day)   # approx (1m bars incl. weekends? idx is trading minutes)
            if tr.sum()<20: continue
            for v in [-1,0,1]:
                s=tr&(x==v); mu=(y[s].sum()+5*y[tr].mean())/(s.sum()+5)
                take[te&(x==v)]=mu>0
        T=np.ones(N,bool); T[rows]=take
        show(f'J={J} rolling{W}d d1_stack rule pool={pool}',ch,T)
