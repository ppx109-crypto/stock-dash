import csv, json, hashlib, math, sys
from pathlib import Path
from datetime import date
import numpy as np

root=Path(__file__).resolve().parent
res=json.loads((root/'evidence/results.json').read_text())
manifest=json.loads((root/'manifest.json').read_text())
checks={'manifest_files':len(manifest['files']), 'manifest_hashes_ok':all(hashlib.sha256((root/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in manifest['files']), 'metrics':[], 'mismatches':[], 'fill_checks':[]}
def calc(rows,lo,hi):
    ix=[i for i,r in enumerate(rows) if lo<=r['date']<=hi]
    i0,i1=ix[0],ix[-1]
    base=float(rows[i0-1]['nav_norm']) if i0 else 1.
    seg=[base]+[float(rows[i]['nav_norm']) for i in ix]
    day=[b/a-1 for a,b in zip(seg,seg[1:])]
    peak=seg[0];dd=[];mon={}
    for i,v,rr in zip(ix,seg[1:],day):
        peak=max(peak,v);dd.append(v/peak-1)
        k=rows[i]['date'][:6];mon[k]=mon.get(k,1.)*(1.+rr)
    yrs=(date.fromisoformat(rows[i1]['date'][:4]+'-'+rows[i1]['date'][4:6]+'-'+rows[i1]['date'][6:])-date.fromisoformat(rows[i0]['date'][:4]+'-'+rows[i0]['date'][4:6]+'-'+rows[i0]['date'][6:])).days/365.25
    return {'CAGR':(seg[-1]/base)**(1/yrs)*100-100,'MDD_daily':min(dd+[0.])*100,'worst_day':min(day)*100,'worst_month':(min(mon.values())-1)*100,'day_breach_-15':sum(x<-.15-1e-12 for x in day),'month_breach_-15':sum(x<.85-1e-12 for x in mon.values()),'cash_ratio_avg_pct':sum(float(rows[i]['cash_ratio']) for i in ix)/len(ix)*100}
periods=[('Train 2012-01~2018-12','20120102','20181228'),('Validation 2019-01~2022-12','20190102','20221229'),('진단 2023-01~2026-09(이미 봄)','20230102','20260930'),('전체','00000000','99999999')]
for p in sorted((root/'evidence').glob('nav_*.csv')):
    rows=list(csv.DictReader(p.open()))
    tag=p.stem.removeprefix('nav_')
    reports={'Train 2012-01~2018-12':res['train'][tag.removeprefix('train_')]['report']} if tag.startswith('train_') else res[tag]['report']
    for name,lo,hi in periods:
        if name not in reports:continue
        got=calc(rows,lo,hi);expected=reports[name]
        checks['metrics'].append({'dataset':tag,'period':name,**{k:round(v,4) for k,v in got.items()}})
        for k,v in got.items():
            tol=.055 if k=='cash_ratio_avg_pct' else .011
            if abs(v-expected[k])>tol:checks['mismatches'].append([tag,name,k,v,expected[k]])
for p in sorted((root/'evidence').glob('fills_*.csv')):
    rows=list(csv.DictReader(p.open()));success=[r for r in rows if r['status'] in ('FILLED','REDUCED')]
    checks['fill_checks'].append({'file':p.name,'rows':len(rows),'not_after_decision':sum(r['fill_at']<=r['decision_at'] for r in success),'unexpected_cost_bp':sum(abs(float(r['cost_bp'])-(13 if '_x2_' in p.name else 6.5))>1e-6 for r in success),'statuses':sorted(set(r['status'] for r in rows))})
# Adversarial fixture for the explicit missing-price retry contract, no market data.
sys.path.insert(0,str(root/'code'))
import nr_engine as E
cal=['20120102','20120103','20120104'];ds=['20120102','20120104']
r=E.Runner(cal,{'069500':(ds,np.array([100.,100.]))},'B',{'N':120,'X':40,'b':.015},cash=10000,start=cal[0])
r.pending=[{'code':'069500','side':'buy','value':1000.,'dec':cal[0],'why':'missing-price fixture','new':True}]
r.step(cal[1],False)
after_missing=len(r.pending)
r.step(cal[2],False)
checks['missing_price_fixture']={'retry_count':r.notes.get('buy_retry_no_price',0),'pending_after_missing':after_missing,'fills_when_price_returns':len(r.acc.fills),'contract_holds':after_missing==1 and len(r.acc.fills)==1,'historical_B3_retry_counts':{k:{n:v for n,v in row['notes'].items() if 'retry_no_price' in n} for k,row in res.items() if k.startswith('full_')}}
(root/'independent-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in checks.items() if k!='metrics'},ensure_ascii=False,indent=2))
