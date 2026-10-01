exec(open('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/common.py').read())
J=B
for pool,rows in [('F9',f9),('fade',fade)]:
    y=np.asarray(R_[rows,J]); kn=np.asarray(X_[rows,J]); x=F.d1_stack.values[rows]; m=lab.M1[rows]; ms=lab._ms()
    print(pool)
    for a,mo in zip(ms[:-1],lab.MONTHS[:-1]):
        tr=kn<a; print(' ',mo.strftime('%Y-%m'),tr.sum(),[f"{y[tr&(x==v)].mean():+.2f}({(tr&(x==v)).sum()})" for v in [-1,0,1]])
