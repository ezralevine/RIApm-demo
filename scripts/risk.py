import numpy as np, pandas as pd
h=pd.read_csv('holdings.csv').set_index('ticker'); b=pd.read_csv('benchmark.csv')
bh=b[b.dimension=='holding'].set_index('group').benchWeight
w=h.weight; aw=w-bh.reindex(w.index).fillna(0)
F=[ # name, group, vol
("Market (beta)","Style",.16),("Size (SMB)","Style",.06),("Value (HML)","Style",.07),("Momentum (UMD)","Style",.09),
("United States","Country",.04),("Taiwan","Country",.18),("Netherlands","Country",.10),("Ireland","Country",.09),("Intl developed","Country",.06),("Emerging ex-Taiwan","Country",.09),
("Information technology","Sector",.09),("Industrials","Sector",.06),("Materials","Sector",.09),("Real estate","Sector",.08),("Communication services","Sector",.08),("Financials","Sector",.07),("Health care","Sector",.07),("Consumer","Sector",.06),("Energy","Sector",.13),("Utilities","Sector",.07),
("TWD","Currency",.06),("EUR","Currency",.08),("JPY","Currency",.10),("GBP","Currency",.08),("Other FX","Currency",.07),
("Copper","Commodity",.22),("Crude oil","Commodity",.30),("Gold","Commodity",.15),
("Interest rates","Macro & other",.06),("Credit spread","Macro & other",.04),("Liquidity","Macro & other",.03),
]
names=[f[0] for f in F]; idx={n:i for i,n in enumerate(names)}; K=len(F)
X=pd.DataFrame(0.0,index=w.index,columns=names)
sector={"NVDA":"Information technology","AVGO":"Information technology","TSM":"Information technology","ASML":"Information technology","MSFT":"Information technology",
"GOOGL":"Communication services","VRT":"Industrials","ETN":"Industrials","GEV":"Industrials","FCX":"Materials","SCCO":"Materials","EQIX":"Real estate","DLR":"Real estate"}
country={"TSM":"Taiwan","ASML":"Netherlands","ETN":"Ireland"}
acwiSec={"Information technology":.26,"Financials":.17,"Industrials":.11,"Consumer":.15,"Health care":.09,"Communication services":.09,"Energy":.035,"Materials":.035,"Utilities":.026,"Real estate":.02}
for t,r in h.iterrows():
    X.loc[t,"Market (beta)"]=r.beta; X.loc[t,"Size (SMB)"]=r.smb if 'smb' in r else 0
for t in w.index:
    if t in sector:
        X.loc[t,sector[t]]=1; X.loc[t,country.get(t,"United States")]=1
    if t=="TSM": X.loc[t,"TWD"]=1
    if t=="ASML": X.loc[t,"EUR"]=1
    if t=="ETN": X.loc[t,"EUR"]=.3
    if t in("FCX","SCCO"): X.loc[t,"Copper"]=1.2 if t=="FCX" else 1.0; X.loc[t,"Gold"]=.2 if t=="FCX" else 0
    if t in("VRT","ETN","GEV"): X.loc[t,"Copper"]=.1; X.loc[t,"Interest rates"]=-.2
    if t in("EQIX","DLR"): X.loc[t,"Interest rates"]=.6; X.loc[t,"Credit spread"]=.3
    if t=="VRT": X.loc[t,"Liquidity"]=.4
    if t=="VTI":
        X.loc[t,"United States"]=1
        for s,v in acwiSec.items(): X.loc[t,s]=v
        X.loc[t,"Crude oil"]=.03
    if t=="VXUS":
        for c,v in {"Intl developed":.72,"Taiwan":.06,"Emerging ex-Taiwan":.22}.items(): X.loc[t,c]=v
        for c,v in {"EUR":.30,"JPY":.15,"GBP":.09,"TWD":.06,"Other FX":.40}.items(): X.loc[t,c]=v
        for s,v in acwiSec.items(): X.loc[t,s]=v
        X.loc[t,"Crude oil"]=.04
    if t=="BND": X.loc[t,"Interest rates"]=1; X.loc[t,"Credit spread"]=.25
# style loadings from the sample (size/value/mom)
sty=pd.DataFrame({ "NVDA":(-.3,-.6,.5),"AVGO":(-.3,-.3,.4),"TSM":(-.3,-.1,.3),"ASML":(-.3,-.2,.2),"VRT":(.1,-.2,.5),"ETN":(-.1,0,.3),"GEV":(0,-.1,.5),"FCX":(.2,.4,0),"SCCO":(.1,.3,.1),"EQIX":(-.2,.2,-.1),"DLR":(-.1,.2,0),"MSFT":(-.4,-.4,.2),"GOOGL":(-.4,-.2,.3)},index=["Size (SMB)","Value (HML)","Momentum (UMD)"]).T
for t,r in sty.iterrows(): X.loc[t,r.index]=r.values
X.loc["BND","Market (beta)"]=.05; X.loc["SGOV","Market (beta)"]=0
port=(X.T*w).sum(axis=1)
# benchmark exposures: 85% ACWI, 10% bonds, 5% cash
bench=pd.Series(0.0,index=names)
bench["Market (beta)"]=.85+.10*.05
for s,v in acwiSec.items(): bench[s]=.85*v
for c,v in {"United States":.64,"Taiwan":.02,"Netherlands":.011,"Ireland":.013,"Intl developed":.25,"Emerging ex-Taiwan":.066}.items(): bench[c]=.85*v
for c,v in {"EUR":.11,"JPY":.05,"GBP":.03,"TWD":.02,"Other FX":.15}.items(): bench[c]=.85*v
bench["Copper"]=.85*.035*.5; bench["Crude oil"]=.85*.035*.8; bench["Gold"]=.85*.01
bench["Interest rates"]=.10+.85*.02*.6; bench["Credit spread"]=.10*.25
act=port-bench
vol=np.array([f[2] for f in F]); C=np.eye(K)
def corr(a,b_,r): C[idx[a],idx[b_]]=C[idx[b_],idx[a]]=r
corr("Copper","Materials",.5); corr("TWD","Taiwan",.5); corr("Momentum (UMD)","Information technology",.3)
corr("Interest rates","Real estate",.35); corr("Crude oil","Energy",.6); corr("EUR","Intl developed",.3)
corr("Value (HML)","Information technology",-.3); corr("Size (SMB)","Market (beta)",.1)
Sig=np.outer(vol,vol)*C
x=act.values; fv=x@Sig@x
spec_vol={t:(0.30 if t in sector else 0.0) for t in w.index}
spec_vol.update({"NVDA":.32,"VRT":.35,"GEV":.30,"TSM":.22,"MSFT":.18,"GOOGL":.20,"EQIX":.16,"DLR":.18,"ETN":.18,"FCX":.24,"SCCO":.22,"ASML":.24,"AVGO":.26,"VTI":.01,"VXUS":.015,"BND":.01,"SGOV":0})
sv=sum((aw[t]*spec_vol[t])**2 for t in w.index)
te=np.sqrt(fv+sv)
contrib=x*(Sig@x)/te
rows=[dict(factor=n,group=F[i][1],portExposure=round(port[n],4),benchExposure=round(bench[n],4),activeExposure=round(x[i],4),factorVol=F[i][2],teContribution=round(contrib[i],5),pctOfTE=round(contrib[i]/te,4)) for i,n in enumerate(names)]
rows.append(dict(factor="Stock-specific",group="Specific",portExposure="",benchExposure="",activeExposure="",factorVol="",teContribution=round(sv/te,5),pctOfTE=round(sv/te**2,4)))
df=pd.DataFrame(rows); df.to_csv('riskmodel.csv',index=False)
print("TE",round(te,4),"factor share",round(fv/te**2,3))
print(df.groupby('group').pctOfTE.sum().sort_values())
print(df.sort_values('pctOfTE').tail(8)[['factor','activeExposure','pctOfTE']])
print(df.pctOfTE.sum(), df.teContribution.sum())
