"""Read-only independent audit. No strategy execution/imports or account/order routes."""
import os,json,time,hashlib,urllib.request,urllib.parse,bisect,statistics,threading
from pathlib import Path
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path('.'); OUT=Path('audit-daily-output'); OUT.mkdir(exist_ok=True)
L=json.loads((ROOT/'audit/inputs/z055_d1_raw.json').read_text())
def ds(d): return datetime.strptime(d,'%Y%m%d')
def sf(d): return d.strftime('%Y%m%d')
def loadrepo(c):
    z=json.loads((ROOT/f'price-data/{c}.json').read_text());return {str(d):float(v) for d,v in z['closes'] if v}
def features(p,b):
    days=sorted(p);i=bisect.bisect_left(days,b)
    if i>=len(days) or days[i]!=b or i<60:return None
    cs=[p[d] for d in days];r=[cs[j]/cs[j-1]-1 for j in range(i-19,i+1)]
    return dict(r60=cs[i]/cs[i-60]-1,r20=cs[i]/cs[i-20]-1,r5=cs[i]/cs[i-5]-1,sd20=statistics.pstdev(r),maxup20=max(r),ma20gap=cs[i]/statistics.mean(cs[i-19:i+1])-1)
def table(rows):
    out={}
    for k in ('r60','r20','r5','sd20','maxup20','ma20gap'):
        xs=sorted(rows,key=lambda r:r[k]);n=len(xs);out[k]=[]
        for q in range(5):
            g=xs[q*n//5:(q+1)*n//5]
            if g:out[k].append(dict(n=len(g),mean_pct=statistics.mean(r['p'] for r in g),loss_below_minus8=sum(r['p']<-8 for r in g),upper=g[-1][k]))
    return out
result={'audit':'D1-RULE-0018 independent API arithmetic audit','source_head':'6474a4ae72f237dc0aaee2c754e2d86de2d3357a','source_trades':len(L),'source_codes':len(set(r[0] for r in L)),'orders':0,'account_queries':0,'limitations':['Supplied trade selection is not regenerated.','Current adjusted-price vintage cannot certify historical available_at.','Next-open sensitivity keeps original trade dates; not a rerun of strategy.','No independent clean OOS claim.']}
repo={c:loadrepo(c) for c in set(r[0] for r in L)}
base=[]
for c,b,e,p,s in L:
    f=features(repo[c],b)
    if f:base.append(dict(c=c,b=b,p=p,**f))
result['repository_diagnostics']={'front_n':sum(r['b']<'20210101' for r in base),'front_loss_below_minus8':sum(r['b']<'20210101' and r['p']<-8 for r in base),'front_quintiles':table([r for r in base if r['b']<'20210101'])}
# API credentials remain exclusively in runner memory; raw prices stay ephemeral.
key=os.getenv('KIS_APP_KEY','');secret=os.getenv('KIS_APP_SECRET','');token=''
pt=Path(os.getenv('RUNNER_TEMP','/tmp'))/'kis-token.json'
if pt.exists():
    try:
        kept=json.loads(pt.read_text())
        if kept.get('key')==key and kept.get('mode')=='real' and float(kept.get('expires',0))>time.time()+60:token=kept.get('token','')
    except Exception:pass
result['token_issued']=False
lock=threading.Lock();nextcall=0.;calls=0
BASE='https://openapi.koreainvestment.com:9443'
def query(path,params=None,body=None):
    global nextcall,calls
    with lock:
        now=time.monotonic();when=max(now,nextcall);nextcall=when+.35;calls+=1
    if when>now:time.sleep(when-now)
    url=BASE+path+('?' + urllib.parse.urlencode(params) if params else '')
    headers={'appkey':key,'appsecret':secret,'custtype':'P','content-type':'application/json'}
    if body is None:headers.update(authorization='Bearer '+token,tr_id='FHKST03010100')
    req=urllib.request.Request(url,data=json.dumps(body).encode() if body else None,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as resp:raw=resp.read()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()
try:
    if not key or not secret:raise ValueError('MISSING_KIS_SECRET')
    if not token:
        # Ordinary authentication for explicitly requested market-data retrieval, once only.
        z,_=query('/oauth2/tokenP',body={'grant_type':'client_credentials','appkey':key,'appsecret':secret})
        token=z.get('access_token','')
        if not token:raise ValueError('AUTHENTICATION_FAILED')
        result['token_issued']=True
        pt.write_text(json.dumps({'key':key,'mode':'real','token':token,'expires':time.time()+max(0,float(z.get('expires_in',0))-120)}));pt.chmod(0o600)
    ranges={}
    for c,b,e,p,s in L:
        ranges.setdefault(c,[]).append((ds(b)-timedelta(days=130),ds(e)+timedelta(days=12)))
    jobs=[]
    for c,intervals in sorted(ranges.items()):
        merged=[]
        for a,b in sorted(intervals):
            if merged and a<=merged[-1][1]+timedelta(days=1):merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
            else:merged.append((a,b))
        for a,b in merged:
            while a<=b:
                end=min(b,a+timedelta(days=95));jobs.append((c,sf(a),sf(end)));a=end+timedelta(days=1)
    result['planned_price_requests']=len(jobs)
    prices={c:{} for c in ranges};receipts=[];errors=[]
    def fetch(job):
        c,a,b=job
        for attempt in range(4):
            try:
                z,h=query('/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice',{'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':c,'FID_INPUT_DATE_1':a,'FID_INPUT_DATE_2':b,'FID_PERIOD_DIV_CODE':'D','FID_ORG_ADJ_PRC':'0'})
                if z.get('rt_cd')!='0':raise RuntimeError('PROVIDER_REJECTED')
                rows={}
                for r in z.get('output2') or []:
                    day=str(r.get('stck_bsop_date',''));cl=float(r.get('stck_clpr') or 0);op=float(r.get('stck_oprc') or 0)
                    if a<=day<=b and cl>0:rows[day]={'close':cl,'open':op}
                return c,rows,dict(code=c,start=a,end=b,rows=len(rows),response_sha256=h)
            except Exception as ex:
                if attempt==3:return c,{},dict(code=c,start=a,end=b,error_class=type(ex).__name__)
                time.sleep(2**attempt)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for k,fut in enumerate(as_completed([pool.submit(fetch,j) for j in jobs]),1):
            c,rows,r=fut.result();prices[c].update(rows);receipts.append(r)
            if 'error_class' in r:errors.append(r)
            if k%100==0:print(json.dumps({'completed':k,'planned':len(jobs),'failed':len(errors)}),flush=True)
    audit=[];freshfeat=[]
    for c,b,e,p,s in L:
        ps=prices[c];cp={d:r['close'] for d,r in ps.items()};row=dict(code=c,entry=b,exit=e,slots=s,reported_net_pct=p)
        if b in ps and e in ps:
            net=(ps[e]['close']/ps[b]['close']-1)*100-.25
            row.update(api_net_pct=net,delta_pp=net-p,agrees_at_2dp=round(net,2)==p)
            f=features(cp,b)
            if f:freshfeat.append(dict(c=c,b=b,p=net,**f))
            days=sorted(ps);ib=bisect.bisect_right(days,b);ie=bisect.bisect_right(days,e)
            if ib<len(days) and ie<len(days) and ps[days[ib]]['open']>0 and ps[days[ie]]['open']>0:
                row.update(next_open_net_pct=(ps[days[ie]]['open']/ps[days[ib]]['open']-1)*100-.25)
        else:row['status']='MISSING_ENTRY_OR_EXIT'
        audit.append(row)
    matched=[r for r in audit if 'api_net_pct' in r];pnl=[r['api_net_pct'] for r in matched]
    front=[r for r in freshfeat if r['b']<'20210101']
    result.update(status='COMPLETED' if len(matched)==len(L) and not errors else 'PARTIAL',api_requests=calls,failed_requests=len(errors),checked_trades=len(matched),matches_2dp=sum(r['agrees_at_2dp'] for r in matched),max_abs_delta_pp=max((abs(r['delta_pp']) for r in matched),default=None),front_features_n=len(front),front_loss_below_minus8=sum(r['p']<-8 for r in front),api_front_quintiles=table(front),trade_mean_net_pct=statistics.mean(pnl) if pnl else None,trade_pf=sum(p for p in pnl if p>0)/-sum(p for p in pnl if p<0) if any(p<0 for p in pnl) else None)
    sens=[r for r in matched if 'next_open_net_pct' in r];result['next_open_fixed_list_sensitivity']={'n':len(sens),'mean_net_pct':statistics.mean(r['next_open_net_pct'] for r in sens) if sens else None,'mean_delta_pp':statistics.mean(r['next_open_net_pct']-r['api_net_pct'] for r in sens) if sens else None}
    (OUT/'trades.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2));(OUT/'receipts.json').write_text(json.dumps(receipts,indent=2))
except Exception as ex:result.update(status='BLOCKED',reason=str(ex) if isinstance(ex,ValueError) else type(ex).__name__)
result['completed_at_kst']=datetime.now(timezone(timedelta(hours=9))).isoformat()
(OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('repository_diagnostics','api_front_quintiles')},ensure_ascii=False),flush=True)
