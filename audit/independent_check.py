"""Read-only independent arithmetic/data audit. No repo strategy imports or APIs."""
import json, hashlib, csv, sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'audit/independent-20261010'
OUT.mkdir(exist_ok=True)
def read(p):
    return json.loads((ROOT/p).read_text()) if (ROOT/p).exists() else {}
def metrics(r):
    r=pd.Series(r).astype(float)
    nav=(1+r).cumprod(); peak=np.maximum.accumulate(np.r_[1.,nav.values])[1:]
    months=(1+r).groupby(r.index.astype(str).str[:6]).prod()-1
    mv=months.values+1
    return dict(days=len(r),cagr_pct=100*(nav.iloc[-1]**(245/len(r))-1),
                worst_day_pct=100*r.min(),worst_month_pct=100*months.min(),
                worst_2month_pct=100*(min(mv[:-1]*mv[1:])-1) if len(mv)>1 else None,
                mdd_pct=100*min(nav.values/peak-1),total_pct=100*(nav.iloc[-1]-1))
def periods(r):
    return {k:metrics(r[(r.index>=lo)&(r.index<hi)]) for k,lo,hi in
      [('train','20170201','20210101'),('validation','20210101','20230101'),
       ('reused_2023_onward','20230101','20260917')]}

# Hash every public input actually read; no secret/account files accessed.
inputs={}
for folder in ['price-data','share-data','short-data','loan-data','event-data','volume-data']:
    ps=sorted((ROOT/folder).glob('*.json'))
    h=hashlib.sha256()
    for p in ps:h.update(p.name.encode());h.update(p.read_bytes())
    inputs[folder]={'files':len(ps),'sha256_ordered_filename_bytes':h.hexdigest()}

# Recalculate every submitted account NAV CSV, not just the chosen result.
navs=[]
for p in sorted(ROOT.glob('research-exchange/**/*.csv')):
    f=pd.read_csv(p,dtype={'날':str})
    if 'NAV' not in f or '날' not in f:continue
    s=pd.Series(f.NAV.values,index=f['날'])
    r=s/s.shift(1)-1;r.iloc[0]=s.iloc[0]/1e8-1
    # 예비 is a subset of 현금, not an additional asset (z093.py:461).
    parts=[c for c in ['현금','일봉','분봉15','바구니','엔진','인버스'] if c in f]
    diff=(f.NAV-f[parts].sum(axis=1)).abs() if len(parts)==6 else None
    navs.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
      'rows':len(f),'duplicate_dates':int(f['날'].duplicated().sum()),
      'dates_sorted':bool(f['날'].is_monotonic_increasing),'negative_nav_rows':int((f.NAV<=0).sum()),
      'max_account_components_residual_won':float(diff.max()) if diff is not None else None,
      'front':metrics(r[(r.index>='20170201')&(r.index<='20201231')]),
      'back':metrics(r[(r.index>='20210101')&(r.index<='20260916')]) if (r.index>='20210101').any() else None})

cl={}
for p in sorted((ROOT/'price-data').glob('*.json')):
    if not p.stem.isdigit():continue
    cl[p.stem]={str(d):float(v) for d,v in json.loads(p.read_text()).get('closes',[]) if v and '20160101'<=str(d)<='20260916'}
C=pd.DataFrame(cl).sort_index(); days=list(C.index); codes=list(C.columns)
R=C.pct_change(fill_method=None)

# Independently implement the published adjusted-share estimator, including its
# retrospective fallback, to reproduce rather than silently change the rule.
def timeline(c,cut=None):
    raw=sorted((str(d),int(n)) for d,n in read(Path('share-data')/(c+'.json')).get('날',[]) if n and (not cut or str(d)<=cut))
    if not raw:return []
    med=float(np.median([n for _,n in raw]));fixed=[(d,n/1000 if n/med>=300 else n*1000 if n/med<=1/300 else n) for d,n in raw]
    lr={str(r['date']):float(r['종가']) for r in read(Path('loan-data')/(c+'.json')).get('rows',[]) if r.get('종가') and (not cut or str(r['date'])<=cut)}
    ac={str(d):float(v) for d,v in read(Path('price-data')/(c+'.json')).get('closes',[]) if v and (not cut or str(d)<=cut)}
    both=sorted(set(lr)&set(ac)); factors=[]
    for d,n in fixed:
        k=np.searchsorted(both,d)
        if both and d<both[0]:q=both[0]
        elif k<len(both) and pd.Timestamp(both[k])<=pd.Timestamp(d)+pd.Timedelta(days=20):q=both[k]
        else:factors=[];break
        factors.append(lr[q]/ac[q])
    if len(factors)==len(fixed):return [(d,int(round(n*f))) for (d,n),f in zip(fixed,factors)]
    bonus=sorted(str(r.get('date')) for r in read(Path('event-data')/(c+'.json')).get('rows',[]) if '무상' in str(r.get('title','')) and (not cut or str(r.get('date'))<=cut))
    fs=[1.]*len(fixed)
    for i in range(len(fixed)-1,0,-1):
        d0,n0=fixed[i-1];d1,n1=fixed[i];x=n1/n0
        fs[i-1]=fs[i]*(x if x>=1.8 or x<=.55 or (1.2<=x<1.8 and any(d0<b<=d1 for b in bonus)) else 1)
    return [(d,int(round(n*f))) for (d,n),f in zip(fixed,fs)]

size=pd.DataFrame(np.nan,index=C.index,columns=C.columns)
for c in codes:
    t=timeline(c)
    if not t:continue
    k=np.searchsorted([d for d,_ in t],days,side='right')-1
    shares=np.array([n for _,n in t]);size[c]=np.where(k>=0,shares[np.maximum(k,0)],np.nan)*C[c]
inside=size.rank(axis=1,ascending=False)<=200
short={}
for c in codes:
    b=read(Path('short-data')/(c+'.json'));cols=b.get('cols',[])
    if '공매도비중' in cols:
        j=cols.index('공매도비중');short[c]={str(r[0]):float(r[j]) for r in b.get('rows',[]) if r[j] is not None}
S=pd.DataFrame(short).reindex(index=C.index,columns=C.columns)
score=-S.rolling(20,min_periods=15).mean()
adv={}
for c in codes:
    b=read(Path('volume-data')/(c+'.json'))
    a=pd.Series({str(r[0]):float(r[2]) for r in b.get('날',[]) if len(r)>2 and r[2]},dtype=float).sort_index()
    adv[c]=a.rolling(20,min_periods=10).mean().shift(1)
tax={2017:.0025,2018:.0025,2019:.0025,2020:.0025,2021:.0025,2022:.0025,2023:.0020,2024:.0018}
def cost(c,d,sell=False,n=5e6):
    a=adv[c];v=a.get(d,np.nan)
    if not np.isfinite(v) or v<=0:
        h=a[a.index<=d];v=h.iloc[-1] if len(h) else np.nan
    impact=.1*np.sqrt(n/v) if np.isfinite(v) and v>0 else .002
    return .00065+impact+(tax.get(int(d[:4]),.0015) if sell else 0)

# Published factor accounting is daily equal-weight returns, not constant shares.
months=[i for i,d in enumerate(days) if d>='20170201' and days[i-1][:6]!=d[:6] and i+1<len(days)]
def factor(sc,N):
    daily=pd.Series(0.,index=C.index);prev=set();selections=[];deferred=0
    for m,i in enumerate(months):
        s=sc.loc[days[i]].where(inside.loc[days[i]]).dropna()
        if len(s)<50:continue
        top=list(s.sort_values(ascending=False).index[:N]);j0=i+1;j1=months[m+1]+1 if m+1<len(months) else len(days)-1
        daily.iloc[j0]-=sum(cost(c,days[j0],n=1e8/N)/N for c in set(top)-prev)+sum(cost(c,days[j0],True,n=1e8/N)/N for c in prev-set(top))
        for c in top:
            v=R.at[days[j0],c];a=j0+1 if abs(v)<.295 or not np.isfinite(v) else j0+2
            deferred+=a==j0+2
            daily.iloc[a:j1+1]+=R[c].iloc[a:j1+1].fillna(0).clip(-.5,1).values/N
        selections.append({'decision':days[i],'entry':days[j0],'codes':top});prev=set(top)
    return daily, selections,int(deferred)
fr,selection,deferred=factor(score,20)
br,_,_=factor(pd.DataFrame(1.,index=C.index,columns=C.columns).where(C.notna()),200)

# Independently form DART basket events without any forward-return labels.
react=R.sub(R.where(inside).median(axis=1),axis=0);events=[]
for c in codes:
    rows=sorted((str(r['date']),r.get('kind')) for r in read(Path('event-data')/(c+'.json')).get('rows',[]) if r.get('date'))
    last={}
    for d,kind in rows:
        if d<'20170101' or kind not in ('자사주취득','무상증자'):continue
        j=int(np.searchsorted(days,d))
        if j+1>=len(days) or not inside.at[days[j],c] or (kind in last and j-last[kind]<20):continue
        last[kind]=j
        if np.isfinite(react.at[days[j],c]) and (kind=='무상증자' or react.at[days[j],c]<-.02):events.append((j,c,kind))
events.sort(key=lambda x:(x[1],x[0],x[2]))
def basket(slots):
    want=defaultdict(list)
    for j,c,_ in events:want[j+1].append(c)
    held={};cash=1.;eq=[];tr=[];deferred=0
    for i,d in enumerate(days):
        for c in list(held):
            k,p0,m,cb=held[c]
            if i-k<20 or (abs(R.at[d,c])>=.295 and i+1<len(days)):continue
            del held[c];p=C.at[d,c];p=p if pd.notna(p) else p0;cs=cost(c,d,True,n=1e8/slots)
            cash+=m*p/p0*(1-cs);tr.append([c,days[k],d,p/p0*(1-cs)*(1-cb)-1])
        value=cash+sum(m*(C.at[d,c]/p if pd.notna(C.at[d,c]) else 1) for c,(k,p,m,cb) in held.items())
        for c in want[i]:
            p=C.at[d,c]
            if len(held)>=slots or c in held or pd.isna(p):continue
            if abs(R.at[d,c])>=.295:
                deferred+=1
                if i+1<len(days):want[i+1].append(c)
                continue
            m=min(value/slots,cash)
            if m<=0:break
            cb=cost(c,d,n=1e8/slots);cash-=m;held[c]=(i,p,m*(1-cb),cb)
        eq.append(cash+sum(m*(C.at[d,c]/p if pd.notna(C.at[d,c]) else 1) for c,(k,p,m,cb) in held.items()))
    eq=pd.Series(eq,index=C.index);r=eq.pct_change();r.iloc[0]=eq.iloc[0]-1
    return r,tr,deferred
dr5,tr5,df5=basket(5);dr8,tr8,df8=basket(8)

# Prefix causality test of features and retrospective share estimator separately.
cut_tests=[]
for cut in ['20201231','20220615','20231231']:
    shortened=-S.loc[:cut].rolling(20,min_periods=15).mean()
    diff=(shortened-score.loc[:cut]).abs().to_numpy()
    changed=[]
    for c in codes:
        full={d:n for d,n in timeline(c) if d<=cut};prefix=dict(timeline(c,cut))
        changes=[d for d in full if full[d]!=prefix.get(d)]
        if changes:changed.append({'code':c,'changed_receipt_rows':len(changes),'first':changes[0]})
    cut_tests.append({'cutoff':cut,'short_feature_max_diff':float(np.nanmax(diff)),
      'adjusted_share_changed_codes':len(changed),'examples':changed[:10]})

result={'scope':'Independent reproduction of historical z054 numerical contract; all submitted NAV CSV arithmetic on PR140 snapshot. Not all-strategy raw-ledger validation.',
 'input_sha':'2d43aa8d26deeeb30d52c2aed6906dbdc798885d','public_inputs':inputs,'nav_csvs':navs,
 'raw_reproduction':{'price_codes':len(codes),'days':len(days),'date_end':days[-1],
 'F5':periods(fr),'baseline':periods(br),'F5_deferred':deferred,
 'basket_events':len(events),'D5':periods(dr5),'D8':periods(dr8),
 'D5_trades':len(tr5),'D8_trades':len(tr8),'D5_deferred':df5,'D8_deferred':df8},
 'cut_tests':cut_tests,
 'limitations':['Historical source snapshot differs from unpublished original caches; current-vintage data is not historical available_at proof.',
 'Published perf2 tax schedule reproduced for comparison only, not endorsed.',
 'F5 published daily equal-weight accounting implies weight restoration without recording daily rebalancing trades/costs; not constant-quantity monthly holdings.',
 'Missing prices filled with zero returns or entry price as in published contracts; delist/suspension realizations not independently proven.',
 'Current survivor universe, receipt-date-only DART, missing original publication timestamps/revision vintages.',
 'Submitted NAV decomposition equality does not prove quantity/cash ledger, executions, or point-in-time signals.',
 'No provider API refresh performed: GitHub Actions secrets cannot be decrypted by current connector.']}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
pd.DataFrame({'date':C.index,'F5_return':fr,'D5_return':dr5,'D8_return':dr8,'baseline_return':br}).to_csv(OUT/'raw_reproduction_returns.csv',index=False)
(OUT/'F5_selections.json').write_text(json.dumps(selection,ensure_ascii=False))
print(json.dumps({'nav_files':len(navs),'max_residual':max(x['max_account_components_residual_won'] or 0 for x in navs),'raw':result['raw_reproduction'],'cuts':cut_tests},ensure_ascii=False,indent=2))
