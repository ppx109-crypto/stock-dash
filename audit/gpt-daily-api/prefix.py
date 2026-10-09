import json,math,bisect,hashlib
from pathlib import Path
import numpy as np
allv=[];prefix=[];entries={};L=json.loads(Path('audit/inputs/z055_d1_raw.json').read_text());want={(r[0],r[1]) for r in L};eligible=[]
for p in sorted(Path('price-data').glob('*.json')):
    z=json.loads(p.read_text());x=sorted((str(d),float(v)) for d,v in z.get('closes',[]) if v)
    if len(x)<=180:continue
    ds=[d for d,v in x];cs=np.array([v for d,v in x]);rr=100*(cs[1:]/cs[:-1]-1)
    vol=np.std(np.lib.stride_tricks.sliding_window_view(rr,20),axis=1,ddof=1)
    ema=np.full(len(cs),np.nan);ema[179]=sum(cs[:180])/180
    for i in range(180,len(cs)):ema[i]=cs[i]*2/181+ema[i-1]*(1-2/181)
    for i in range(120,len(cs)-5):
        v=float(vol[i-20]);allv.append(v)
        if ds[i]<='20201231':prefix.append(v)
        if i>=184 and cs[i]/cs[i-60]-1>=.2 and (ema[i]/ema[i-5]-1)*100>=1.46 and '20170101'<=ds[i]<='20201231':eligible.append((p.stem,ds[i],v))
        if (p.stem,ds[i]) in want:entries[(p.stem,ds[i])]=(v,(ema[i]/ema[i-5]-1)*100 if i>=184 else None,(cs[i]/cs[i-60]-1)*100)
a=np.array(allv);b=np.array(prefix);full=float(np.partition(a,int(len(a)*.4))[int(len(a)*.4)]);past=float(np.partition(b,int(len(b)*.4))[int(len(b)*.4)])
changed=[dict(code=c,day=d,vol=v,full_pass=v<=full,prefix_pass=v<=past) for c,d,v in eligible if (v<=full)!=(v<=past)]
entrychanged=[]
for (c,d),(v,s,r60) in entries.items():
    if d<='20201231' and s is not None and s>=1.46 and r60>=20 and (v<=full)!=(v<=past):entrychanged.append(dict(code=c,day=d,full_pass=v<=full,prefix_pass=v<=past))
r={'cutoff':'20201231','full_vol_n':len(allv),'prefix_vol_n':len(prefix),'full_calm40':full,'prefix_calm40':past,'price_files':len(list(Path('price-data').glob('*.json'))),'trend_price_gate_flip_n':len(changed),'supplied_entry_trend_branch_flip_n':len(entrychanged),'supplied_entry_flips':entrychanged,'examples':changed[:10],'scope':'Same frozen adjusted-price vintage, price trend branch only, no rank/flow/alignment/target gate; not regenerated trade list.'}
Path('audit/gpt-daily-api/prefix-results.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
