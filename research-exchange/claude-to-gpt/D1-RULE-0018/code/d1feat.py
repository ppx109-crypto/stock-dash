import json, math, statistics as st, bisect
from pathlib import Path
L=json.load(open('/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/z055_d1_raw.json'))
cache={}
def ser(c):
    if c not in cache:
        b=json.loads(Path(f'price-data/{c}.json').read_text()) if Path(f'price-data/{c}.json').exists() else {'closes':[]}
        rows=sorted((str(d),float(v)) for d,v in b.get('closes') or [] if v)
        cache[c]=([d for d,_ in rows],[v for _,v in rows])
    return cache[c]
rows=[]
for c,b,e,p,s in L:
    ds,cs=ser(c)
    i=bisect.bisect_right(ds,b)-1
    if i<61 or ds[i]!=b: continue
    r=[cs[j]/cs[j-1]-1 for j in range(i-19,i+1)]
    f=dict(r60=cs[i]/cs[i-60]-1, r20=cs[i]/cs[i-20]-1, r5=cs[i]/cs[i-5]-1, sd20=st.pstdev(r), maxup20=max(r), ma20gap=cs[i]/(sum(cs[i-19:i+1])/20)-1)
    rows.append(dict(c=c,b=b,p=p,s=s,contrib=p*s,**f))
front=[x for x in rows if x['b']<'20210101']; back=[x for x in rows if x['b']>='20210101']
print('특징 계산된 매매: 앞',len(front),'뒤',len(back))
def table(data,name):
    print(f'== {name}')
    for k in ('r60','r20','r5','sd20','maxup20','ma20gap'):
        xs=sorted(data,key=lambda x:x[k]); n=len(xs); q=[xs[i*n//5:(i+1)*n//5] for i in range(5)]
        print(f'  {k:8s} '+' | '.join(f'Q{i+1} 평균 {st.mean(x["p"] for x in g):+5.1f} · −8%↓ {sum(1 for x in g if x["p"]<-8):2d} · 경계 {g[-1][k]:.3f}' for i,g in enumerate(q)))
table(front,'앞 반(2017~2020) — 특징 5분위별 매매 손익(%) · 크게 잃은 수(−8% 아래)')
