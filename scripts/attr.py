import pathlib; exec(open(pathlib.Path(__file__).parent / 'gen.py').read().split("def stats(s):")[0])
import numpy as np, pandas as pd
S=np.expm1(R)                      # simple daily returns by holding
B=np.expm1(bench)
end=days[-1]
W={"1M":21,"3M":63,"YTD":int((days>=pd.Timestamp("2026-01-01")).sum()),"1Y":252,"Since start":len(days)-1}
rows=[];summ=[]
for k,n in W.items():
    s=S.iloc[-n:]
    # drifting weights from start of window (buy-and-hold within the window)
    w0=w.values.copy(); val=w0.copy(); contrib=np.zeros(len(w0)); pv=1.0; wsum=np.zeros(len(w0))
    for i in range(n):
        wt=w0; wsum+=wt
        r=s.iloc[i].values
        pr=np.expm1(port.iloc[-n+i])          # same daily portfolio return as the growth chart
        raw=wt*r; raw=raw*(pr/raw.sum()) if abs(raw.sum())>1e-12 else raw
        contrib+=raw*pv          # contribution in portfolio-return units, compounding the base
        pv*=1+pr
        val=val*(1+r)
    pret=pv-1; bret=np.prod(1+B.iloc[-n:].values)-1
    for j,t in enumerate(w.index):
        rows.append(dict(window=k,ticker=t,name=df.set_index('ticker').name[t],theme=df.set_index('ticker').theme[t],
            avgWeight=round(wsum[j]/n,5),assetReturn=round(np.prod(1+s.iloc[:,j].values)-1,5),contribution=round(contrib[j],6)))
    summ.append(dict(window=k,days=n,start=s.index[0].strftime('%Y-%m-%d'),end=end.strftime('%Y-%m-%d'),portReturn=round(pret,5),benchReturn=round(bret,5),excess=round(pret-bret,5)))
    assert abs(contrib.sum()-pret)<1e-9
a=pd.DataFrame(rows); s=pd.DataFrame(summ)
a.to_csv('attribution.csv',index=False); s.to_csv('attrsummary.csv',index=False)
print(s); print(a[a.window=='3M'].sort_values('contribution').to_string())
