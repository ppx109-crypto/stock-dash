import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import nr_engine as E

cal=['20120102','20120103','20120104']
ds=[cal[0],cal[2]]
def runner():
    return E.Runner(cal,{'069500':(ds,np.array([100.,100.]))},'B',{'N':120,'X':40,'b':.015},cash=10000,start=cal[0])
results={}
r=runner(); r.pending=[{'code':'069500','side':'buy','value':1000.,'dec':cal[0],'why':'fixture','new':True}]
r.step(cal[1],False); kept=len(r.pending)==1
r.step(cal[2],False)
results['buy_retry_preserved']=kept and len(r.acc.fills)==1 and r.acc.fills[0]['decision_at']==cal[0]
r=runner();r.acc.buy('p','069500',100.,cal[0],cal[0],qty=10);r.pending=[{'code':'069500','side':'sell','qty':None,'dec':cal[0],'why':'fixture'}]
r.step(cal[1],False);kept=len(r.pending)==1
r.step(cal[2],False)
results['sell_retry_preserved']=kept and not r.held() and len(r.acc.fills)==2
r=runner();retry={'code':'069500','side':'buy','value':1000.,'dec':cal[0],'why':'fixture','new':True};r.pending=[retry]
fresh=dict(retry,dec=cal[1]);m=r.merge_retries([fresh])
results['duplicate_buy_not_created']=len(m)==1 and m[0]['dec']==cal[0]
sell={'code':'069500','side':'sell','qty':None,'dec':cal[1],'why':'new liquidation'}
m=r.merge_retries([sell]);results['new_sell_supersedes_retry']=m==[sell]
r=runner();r.pending=[retry];r.month_base=20000.;r.cur_month='201201'
r.step(cal[1],False)
results['month_stop_cancels_missing_buy']=not r.pending and r.notes['retry_buy_cancelled_month_stop']==1
r=runner();fresh=[retry];results['no_retry_path_identical']=r.merge_retries(fresh) is fresh
out={'all_pass':all(results.values()),'n':len(results),'results':results}
Path(__file__).with_name('retry-checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
assert out['all_pass']
