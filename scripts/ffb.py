import pathlib; exec(open(pathlib.Path(__file__).parent / 'gen.py').read().split("def stats(s):")[0])
import numpy as np, pandas as pd
X=np.column_stack([np.ones(n),bench.values-0.04/252,fs["smb"],fs["hml"],fs["mom"]])
yb=bench.values-0.04/252
bb,*_=np.linalg.lstsq(X,yb,rcond=None)
f=pd.read_csv('factors.csv')
bl=[bb[0]*252]+list(bb[1:])
f["benchLoading"]=np.round(bl,3)+0.0
f["activeLoading"]=(f.loading-f.benchLoading).round(3)
f.to_csv('factors.csv',index=False); print(f)
