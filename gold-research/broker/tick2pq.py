import pandas as pd, numpy as np, zipfile, glob, io, sys
for z in sorted(glob.glob('hdt/*.zip')):
    out=z.replace('.zip','.parquet')
    import os
    if os.path.exists(out): continue
    with zipfile.ZipFile(z) as f:
        n=[x for x in f.namelist() if x.endswith('.csv')][0]
        df=pd.read_csv(f.open(n),header=None,names=['t','bid','ask','v'],dtype={'t':str})
    # EST no-DST = UTC-5
    t=pd.to_datetime(df.t.str[:15],format='%Y%m%d %H%M%S')+pd.to_timedelta(df.t.str[15:].astype(int),unit='ms')+pd.Timedelta(hours=5)
    o=pd.DataFrame({'time':t.values,'bid':df.bid.astype('float32'),'ask':df.ask.astype('float32')})
    o.to_parquet(out); print(out,len(o),(o.ask-o.bid).median(),flush=True)
