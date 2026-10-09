"""Prefix universe audit; keep adjusted-price vintage fixed and truncate share/loan/event inputs."""
import ast,json
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/'audit/independent_check.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['read','timeline']],type_ignores=[]),'audit','exec'))
cut='20201231'
cl={p.stem:{str(d):float(v) for d,v in json.loads(p.read_text()).get('closes',[]) if v and '20160101'<=str(d)<=cut} for p in sorted((ROOT/'price-data').glob('*.json')) if p.stem.isdigit()}
C=pd.DataFrame(cl).sort_index();sizes=[]
for shorten in [False,True]:
 size=pd.DataFrame(np.nan,index=C.index,columns=C.columns)
 for c in C:
  t=timeline(c,cut if shorten else None)
  if not t:continue
  k=np.searchsorted([d for d,_ in t],C.index,side='right')-1;n=np.array([n for _,n in t]);size[c]=np.where(k>=0,n[np.maximum(k,0)],np.nan)*C[c]
 sizes.append(size)
A=sizes[0].rank(axis=1,ascending=False)<=200;B=sizes[1].rank(axis=1,ascending=False)<=200
mask=A!=B;short={}
for c in C:
 b=read(Path('short-data')/(c+'.json'));cols=b.get('cols',[])
 if '공매도비중' in cols:
  k=cols.index('공매도비중');short[c]={str(r[0]):float(r[k]) for r in b.get('rows',[]) if r[k] is not None}
S=-pd.DataFrame(short).reindex(index=C.index,columns=C.columns).rolling(20,min_periods=15).mean();selection_changes=[]
for i,d in enumerate(C.index):
 if d<'20170201' or C.index[i-1][:6]==d[:6]:continue
 a=S.loc[d].where(A.loc[d]).dropna();b=S.loc[d].where(B.loc[d]).dropna()
 if len(a)<50 or len(b)<50:continue
 x=set(a.sort_values(ascending=False).index[:20]);y=set(b.sort_values(ascending=False).index[:20])
 if x!=y:selection_changes.append({'decision_date':d,'full_only':sorted(x-y),'prefix_only':sorted(y-x)})
r={'cutoff':cut,'current_adjusted_price_vintage_held_fixed':True,'universe_membership_changed_cells':int(mask.sum().sum()),'universe_changed_days':int(mask.any(axis=1).sum()),'F5_month_selection_changed_count':len(selection_changes),'examples':selection_changes}
out=ROOT/'audit/independent-20261010/prefix_universe.json';out.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='examples'}))
