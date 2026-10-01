from h import *
def blend(a,b,w):
    r = w*R1[:,a]+(1-w)*R1[:,b]; x = np.maximum(X1[:,a],X1[:,b])
    idx=np.where(in25)[0]; tk=greedy(idx,x[idx]); ii=idx[tk]; return ii, r[ii]
L=[1200,1208,1232,1240,1248,1272,1254,1238, 2400,2440]; RR=[1320,1328,1352,1280,1288,1324,1326,2520,2480]
out=[]
for a in L:
    for b in RR:
        for w in (0.3,0.5,0.7):
            ii,r=blend(a,b,w); m=lab.metrics(r,T[ii]); out.append(dict(lock=pname(a),run=pname(b),a=a,b=b,w=w,**{k:m[k] for k in ("n","sumR","maxDD_R","ret_dd","months_pos","weeks_pos_pct","eq_R2","ulcer_R","top5days_pct")}))
D=pd.DataFrame(out); D.to_csv("E2_blends.csv"); pd.set_option('display.width',250)
k70=D[(D.a<2400)&(D.b<2400)]
print(k70.groupby('w')[['sumR','maxDD_R','ret_dd','eq_R2','ulcer_R','top5days_pct']].describe(percentiles=[.1,.5,.9]).T.round(2).to_string())
print("share of k70 blends with sumR>26.6 & maxDD<=1.6:", ((k70.sumR>26.6)&(k70.maxDD_R<=1.6)).mean(), " ret_dd>23.9:", (k70.ret_dd>23.87).mean())
print(D[(D.a==1200)|(D.a==1248)].sort_values(['a','b','w']).to_string())
