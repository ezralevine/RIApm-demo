import numpy as np, pandas as pd, json
rng=np.random.default_rng(42)
H=[ # ticker,name,class,sector,theme,country,shares,cost,price,beta,smb,hml,mom,vol
("NVDA","NVIDIA","Equity","Semiconductors","AI compute","US",120,62.0,182.0,1.7,-0.3,-0.6,0.5,0.50),
("AVGO","Broadcom","Equity","Semiconductors","AI compute","US",40,140.0,345.0,1.3,-0.3,-0.3,0.4,0.38),
("TSM","Taiwan Semiconductor","Equity","Semiconductors","AI compute","Taiwan",80,110.0,290.0,1.2,-0.3,-0.1,0.3,0.34),
("ASML","ASML Holding","Equity","Semiconductor Equipment","AI compute","Netherlands",12,690.0,1010.0,1.2,-0.3,-0.2,0.2,0.36),
("VRT","Vertiv","Equity","Electrical Equipment","Cooling & power","US",90,78.0,168.0,1.6,0.1,-0.2,0.5,0.48),
("ETN","Eaton","Equity","Electrical Equipment","Cooling & power","Ireland",30,290.0,372.0,1.1,-0.1,0.0,0.3,0.27),
("GEV","GE Vernova","Equity","Electrical Equipment","Cooling & power","US",18,310.0,610.0,1.3,0.0,-0.1,0.5,0.40),
("FCX","Freeport-McMoRan","Equity","Metals & Mining","Copper","US",150,41.0,44.5,1.4,0.2,0.4,0.0,0.38),
("SCCO","Southern Copper","Equity","Metals & Mining","Copper","US",35,95.0,128.0,1.2,0.1,0.3,0.1,0.33),
("EQIX","Equinix","Equity","Data Center REIT","Data centers","US",14,790.0,845.0,0.8,-0.2,0.2,-0.1,0.24),
("DLR","Digital Realty","Equity","Data Center REIT","Data centers","US",40,148.0,171.0,0.9,-0.1,0.2,0.0,0.27),
("MSFT","Microsoft","Equity","Software","Hyperscalers","US",30,370.0,520.0,1.0,-0.4,-0.4,0.2,0.24),
("GOOGL","Alphabet","Equity","Interactive Media","Hyperscalers","US",50,140.0,255.0,1.1,-0.4,-0.2,0.3,0.30),
("VTI","Vanguard Total Stock Market ETF","Equity","Broad Market","Core","US",60,240.0,330.0,1.0,0.0,0.0,0.0,0.17),
("VXUS","Vanguard Total Intl Stock ETF","Equity","Broad Market","Core","International",120,58.0,72.0,0.9,0.1,0.2,0.0,0.16),
("BND","Vanguard Total Bond Market ETF","Fixed Income","Bonds","Ballast","US",180,73.0,74.2,0.05,0.0,0.0,0.0,0.06),
("SGOV","iShares 0-3M Treasury ETF","Cash","Treasury Bills","Ballast","US",150,100.3,100.5,0.0,0,0,0,0.005),
]
cols="ticker name assetClass sector theme country shares cost price beta smb hml mom vol".split()
df=pd.DataFrame(H,columns=cols)
df["value"]=df.shares*df.price; df["costBasis"]=df.shares*df.cost
df["gain"]=df.value-df.costBasis; df["gainPct"]=df.gain/df.costBasis
tot=df.value.sum(); df["weight"]=df.value/tot
# 2y daily sim, ending at current price, factor-driven
days=pd.bdate_range(end="2026-10-23",periods=504)
n=len(days)
mkt=rng.normal(0.11/252,0.17/np.sqrt(252),n)
fs={k:rng.normal(0,0.08/np.sqrt(252),n) for k in["smb","hml","mom"]}
rets={}
for _,r in df.iterrows():
    idio=max(r.vol**2-(r.beta*0.17)**2,0.0001)**0.5
    x=r.beta*mkt+r.smb*fs["smb"]+r.hml*fs["hml"]+r.mom*fs["mom"]+rng.normal(0,idio/np.sqrt(252),n)
    tgt=np.log(r.price/r.cost)*0.9/n  # drift to roughly match gains
    x=x-x.mean()+tgt
    rets[r.ticker]=x
R=pd.DataFrame(rets,index=days)
w=df.set_index("ticker").weight
port=(R*w).sum(axis=1); bench=pd.Series(mkt-mkt.mean()+0.12/252,index=days)
pv=tot*np.exp(port.cumsum()-port.sum()); bv=np.exp(bench.cumsum()); bv=bv/bv.iloc[0]*pv.iloc[0]
def stats(s):
    ann=s.mean()*252; v=s.std()*np.sqrt(252); cum=np.exp(s.cumsum()); dd=(cum/cum.cummax()-1).min()
    return dict(annReturn=ann,annVol=v,sharpe=(ann-0.04)/v,maxDrawdown=dd)
ps=stats(port); bs=stats(bench)
# regression on factors
X=np.column_stack([np.ones(n),bench.values-0.04/252,fs["smb"],fs["hml"],fs["mom"]]); y=port-0.04/252
b,*_=np.linalg.lstsq(X,y,rcond=None); res=y-X@b; r2=1-res.var()/y.var()
se=np.sqrt(np.diag(res.var()*np.linalg.inv(X.T@X)))
factors=[dict(factor=f,loading=round(b[i],3),tStat=round(b[i]/se[i],2)) for i,f in enumerate(["Alpha (ann.)","Market","Size (SMB)","Value (HML)","Momentum"])]
factors[0]["loading"]=round(b[0]*252,4)
te=(port-bench).std()*np.sqrt(252)
# monthly returns
m=pd.DataFrame({"portfolio":port,"benchmark":bench}).resample("ME").sum().apply(np.expm1)
hist=pd.DataFrame({"date":pv.index.strftime("%Y-%m-%d"),"portfolio":pv.round(0).values,"benchmark":bv.round(0).values}).iloc[::5]
dd=(pv/pv.cummax()-1)
ddh=pd.DataFrame({"date":dd.index.strftime("%Y-%m-%d"),"drawdown":dd.round(4).values}).iloc[::5]
# risk contribution
cov=R.cov()*252; wv=w.values; pvar=wv@cov.values@wv
rc=wv*(cov.values@wv)/pvar
df["riskContribution"]=rc
df["annVol"]=R.std().values*np.sqrt(252)
hold=df[["ticker","name","assetClass","sector","theme","country","shares","cost","price","value","costBasis","gain","gainPct","weight","beta","annVol","riskContribution"]].round(4)
out=dict(asOf="2026-10-23",totalValue=round(tot,2),totalCost=round(df.costBasis.sum(),2),
 portfolio={k:round(v,4) for k,v in ps.items()},benchmark={k:round(v,4) for k,v in bs.items()},
 beta=round(b[1],3),trackingError=round(te,4),r2=round(r2,3),top5=round(df.weight.nlargest(5).sum(),4))
hold.to_csv("holdings.csv",index=False); hist.to_csv("history.csv",index=False); ddh.to_csv("drawdown.csv",index=False)
m.index=m.index.strftime("%Y-%m"); m.round(4).reset_index(names="month").to_csv("monthly.csv",index=False)
pd.DataFrame(factors).to_csv("factors.csv",index=False)
json.dump(out,open("summary.json","w"),indent=1)
print(json.dumps(out,indent=1)); print(hold[["ticker","weight","gainPct","riskContribution"]]); print(pd.DataFrame(factors))
print(df.groupby("theme").weight.sum().sort_values())
