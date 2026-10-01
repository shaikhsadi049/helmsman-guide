import pandas as pd, numpy as np, glob
# 2024 warm-up from HistData M1 bid (volume unknown -> filled later), 2025+ from bid ticks
m=pd.read_csv('hd/DAT_ASCII_XAUUSD_M1_2024.csv',sep=';',header=None,names=['t','open','high','low','close','volume'])
m.index=pd.to_datetime(m.t,format='%Y%m%d %H%M%S')+pd.Timedelta(hours=5); m=m.drop(columns='t')
parts=[m[m.index<'2025-01-01']]; spr=[]
for f in sorted(glob.glob('hdt/*.parquet')):
    t=pd.read_parquet(f); t['m']=t.time.dt.floor('1min'); t['s']=t.ask-t.bid
    g=t.groupby('m').agg(open=('bid','first'),high=('bid','max'),low=('bid','min'),close=('bid','last'),volume=('bid','size'),spread=('s','median'))
    parts.append(g[['open','high','low','close','volume']]); spr.append(g.spread); print(f,len(g),flush=True)
out=pd.concat(parts).astype('float64'); out=out[~out.index.duplicated()].sort_index()
v=out.volume.copy(); med=v[v>0].groupby(v[v>0].index.hour).median()
z=v<=0; out.loc[z,'volume']=med.reindex(out.index[z].hour).values   # 2024 warm-up: typical tick count by hour
out.index=pd.DatetimeIndex(out.index).tz_localize('UTC'); out.to_parquet('m1_bid.parquet')
s=pd.concat(spr); s.index=pd.DatetimeIndex(s.index).tz_localize('UTC'); s=s[~s.index.duplicated()].sort_index(); s.to_frame('spread').to_parquet('m1_spread.parquet')
print(out.index[0],out.index[-1],len(out)); print(s.describe())
