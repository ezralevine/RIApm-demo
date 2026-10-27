import pathlib; exec(open(pathlib.Path(__file__).parent / 'gen.py').read().split("def stats(s):")[0])  # rebuild identical daily series (seed 42)
import numpy as np, pandas as pd
P=pd.DataFrame({"portfolio":np.expm1(port),"benchmark":np.expm1(bench)},index=days)
rf=0.04/252
def m(s,b):
    dn=s[s<0]; q=s.quantile(0.05)
    up=b>0; dnb=b<0
    return {
     "Annualized volatility":(s.std()*np.sqrt(252),"pct"),
     "Downside deviation":(np.sqrt((np.minimum(s-rf,0)**2).mean())*np.sqrt(252),"pct"),
     "Sortino ratio":((s.mean()-rf)*252/(np.sqrt((np.minimum(s-rf,0)**2).mean())*np.sqrt(252)),"num"),
     "1-day VaR (95%)":(q,"pct"),
     "1-day CVaR (95%)":(s[s<=q].mean(),"pct"),
     "Worst day":(s.min(),"pct"),
     "Best day":(s.max(),"pct"),
     "Up days":((s>0).mean(),"pct"),
     "Upside capture":(s[up].mean()/b[up].mean(),"pct"),
     "Downside capture":(s[dnb].mean()/b[dnb].mean(),"pct"),
     "Vol, last 3 months":(s.iloc[-63:].std()*np.sqrt(252),"pct"),
    }
mp=m(P.portfolio,P.benchmark); mb=m(P.benchmark,P.benchmark)
rows=[dict(metric=k,portfolio=round(v[0],5),benchmark=round(mb[k][0],5),unit=v[1]) for k,v in mp.items()]
pd.DataFrame(rows).to_csv('volstats.csv',index=False)
r=P.rolling(63).std()*np.sqrt(252)
r=r.dropna().iloc[::5].round(4); r.index=r.index.strftime('%Y-%m-%d'); r.reset_index(names='date').to_csv('rollingvol.csv',index=False)
d=P.round(5); d.index=d.index.strftime('%Y-%m-%d'); d.reset_index(names='date').to_csv('dailyreturns.csv',index=False)
print(pd.DataFrame(rows)); print(len(r))
