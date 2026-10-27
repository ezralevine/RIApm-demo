import numpy as np, pandas as pd
rng=np.random.default_rng(7)
F=[("Northlight Growth Partners III","Growth equity",2019,50000,0.040),
("Harborview Buyout Fund VII","Buyout",2020,60000,0.035),
("Cedar Ridge Ventures II","Venture",2021,30000,0.030),
("Ironbridge Infrastructure Partners","Infrastructure",2021,40000,0.022),
("Alderpoint Secondaries IV","Secondaries",2022,35000,0.035),
("Quarry Hill Private Credit II","Private credit",2023,40000,0.024),
("Tidewater Data Center Co-Invest","Co-investment",2024,25000,0.030)]
Q=pd.period_range("2019Q1","2026Q3",freq="Q")
idx=np.cumprod(np.r_[1,1+np.random.default_rng(3).normal(0.026,0.04,len(Q)-1)])  # benchmark index for PME
callsched={"Private credit":[.3,.3,.2,.1],"Secondaries":[.35,.3,.15,.1],"Co-investment":[.85,.05]}
rows=[];funds=[]
def irr(cf,per=4):
    lo,hi=-0.9,2.0
    f=lambda r:sum(c/(1+r)**(i/per) for i,c in enumerate(cf))
    for _ in range(200):
        m=(lo+hi)/2
        if f(lo)*f(m)<=0: hi=m
        else: lo=m
    return m
for name,strat,vin,com,rq in F:
    start=Q.get_loc(pd.Period(f"{vin}Q2" if vin>2019 else "2019Q2","Q"))
    sched=callsched.get(strat,[.2,.25,.2,.15,.1])
    nav=0;called=0;dist=0;cf=[];bcall=bdist=0
    for i in range(start,len(Q)):
        age=(i-start)/4
        yr=int(age)
        call=com*sched[yr]/4*(1+rng.normal(0,.25)) if yr<len(sched) else 0
        call=max(0,min(call,com*0.95-called))
        if age<1.5: r=rq-0.02   # fees drag early: the J-curve
        else: r=rq+rng.normal(0,0.03 if strat in("Venture","Growth equity") else 0.012)
        nav=nav*(1+r)+call
        d=0
        dstart={"Private credit":.75,"Secondaries":1.5,"Infrastructure":2,"Co-investment":3}.get(strat,3.5)
        if age>=dstart: d=nav*({"Private credit":.035,"Infrastructure":.03}.get(strat,.055))*(1+rng.normal(0,.4)); d=max(0,d)
        nav-=d; called+=call; dist+=d
        rows.append(dict(quarter=str(Q[i]),fund=name,calls=round(call,2),distributions=round(d,2)))
        cf.append(d-call); bcall+=call*idx[-1]/idx[i]; bdist+=d*idx[-1]/idx[i]
    cf[-1]+=nav
    funds.append(dict(fund=name,strategy=strat,vintage=vin,commitment=com,called=round(called,2),distributed=round(dist,2),nav=round(nav,2),
        netIRR=round(irr(cf),4),ksPME=round((bdist+nav)/bcall,3),navDate="2026-09-30"))
f=pd.DataFrame(funds); c=pd.DataFrame(rows)
f.to_csv('pefunds.csv',index=False); c.to_csv('pecashflows.csv',index=False)
# projected calls next 4 quarters from remaining schedule
proj=[]
for _,r in f.iterrows():
    unf=r.commitment-r.called
    pace={"Co-investment":0,"Private credit":.35,"Secondaries":.3,"Venture":.25,"Infrastructure":.2,"Buyout":.18,"Growth equity":.15}[r.strategy]
    for k,q in enumerate(["2026Q4","2027Q1","2027Q2","2027Q3"]):
        proj.append(dict(quarter=q,fund=r.fund,projectedCall=round(unf*pace/4*(1-0.05*k),2)))
pd.DataFrame(proj).to_csv('pecalls.csv',index=False)
f["dpi"]=f.distributed/f.called; f["tvpi"]=(f.distributed+f.nav)/f.called; f["unfunded"]=f.commitment-f.called
print(f[["fund","vintage","commitment","called","distributed","nav","unfunded","dpi","tvpi","netIRR","ksPME"]].round(2).to_string())
print(f[["commitment","called","distributed","nav","unfunded"]].sum())
print(pd.DataFrame(proj).groupby('quarter').projectedCall.sum())
