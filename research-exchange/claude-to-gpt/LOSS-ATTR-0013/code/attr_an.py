import csv, json, sys
from collections import defaultdict
S=sys.argv[1]
A=list(csv.DictReader(open(S+"/F_attr.csv")))
L=["1d","15m","basket","engine","inverse"]
K={r["date"]:r["종가"] for r in json.load(open("market-data/index_KOSPI.json"))["rows"]}
KD=sorted(K)
def kret(d):
    import bisect
    i=bisect.bisect_left(KD,d)
    return K[KD[i]]/K[KD[i-1]]-1 if i>0 and KD[i]==d else None
rows=[]
for r in A:
    n0=float(r["NAV전"])
    x={l:float(r[l])/n0 for l in L}
    rows.append(dict(d=r["날"],tot=sum(x.values()),k=kret(r["날"]),E=float(r["E"]),held=float(r["든것"]),**x))
yrs=len(rows)/245
print("== 갈래별 기여(계좌 대비 하루 손익 합 ÷ 년, 비용 뺀 값)")
for l in L: print(f"  {l}: 연 {sum(r[l] for r in rows)/yrs*100:+.2f}%p")
print("== 해마다 갈래 기여(%p, 단순 합)")
for y in range(2017,2027):
    rs=[r for r in rows if r["d"].startswith(str(y))]
    print(" ",y," · ".join(f"{l} {sum(r[l] for r in rs)*100:+.1f}" for l in L), f"| 합 {sum(r['tot'] for r in rs)*100:+.1f}")
print("== 가장 나쁜 날 15")
for r in sorted(rows,key=lambda r:r["tot"])[:15]:
    print(f"  {r['d']} 계좌 {r['tot']*100:+.2f}% · 코스피 {r['k']*100 if r['k'] is not None else float('nan'):+.2f}% · 든 것 {r['held']*100:.0f}% · E {r['E']:.2f} · "+" ".join(f"{l} {r[l]*100:+.2f}" for l in L if abs(r[l])>5e-4))
# 달
M=defaultdict(lambda: defaultdict(float))
for r in rows:
    for l in L+["tot"]: M[r["d"][:6]][l]+=r[l]
print("== 가장 나쁜 달 10(갈래 단순 합 %p)")
for m,v in sorted(M.items(),key=lambda x:x[1]["tot"])[:10]:
    km=[r["k"] for r in rows if r["d"].startswith(m) and r["k"] is not None]
    p=1
    for x in km: p*=1+x
    print(f"  {m} 계좌 {v['tot']*100:+.1f} · 코스피 {(p-1)*100:+.1f} · "+" ".join(f"{l} {v[l]*100:+.1f}" for l in L if abs(v[l])>5e-4))
# 공통점: 시장 급락일
bad=[r for r in rows if r["tot"]<-0.015]
print(f"== 계좌 −1.5% 넘게 잃은 날 {len(bad)}일 · 그중 코스피도 −1% 넘게 빠진 날 {sum(1 for r in bad if r['k'] is not None and r['k']<-0.01)}일 · 여러 갈래(2개 이상)가 함께 잃은 날 {sum(1 for r in bad if sum(1 for l in L if r[l]<-0.002)>=2)}일")
for l in L:
    print(f"   {l}이 그날 손실의 절반 넘게 낸 날 {sum(1 for r in bad if r[l] < 0.5*r['tot'])}일")
kd=[r for r in rows if r["k"] is not None and r["k"]<-0.02]
print(f"== 코스피 −2% 넘게 빠진 날 {len(kd)}일 · 그날 계좌 평균 {sum(r['tot'] for r in kd)/len(kd)*100:+.2f}% · 갈래 평균 "+" ".join(f"{l} {sum(r[l] for r in kd)/len(kd)*100:+.2f}" for l in L))
ku=[r for r in rows if r["k"] is not None and r["k"]>0.02]
print(f"== 코스피 +2% 넘게 오른 날 {len(ku)}일 · 그날 계좌 평균 {sum(r['tot'] for r in ku)/len(ku)*100:+.2f}%")
# 상관
import statistics as st
print("== 갈래 하루 손익 상관(둘 다 움직인 날)")
for i,a in enumerate(L):
    for b in L[i+1:]:
        xs=[(r[a],r[b]) for r in rows if r[a]!=0 and r[b]!=0]
        if len(xs)>30: print(f"  {a}-{b} {st.correlation([x for x,_ in xs],[y for _,y in xs]):+.2f}({len(xs)}일)")
# 코스피와 상관(베타)
for l in L:
    xs=[(r["k"],r[l]) for r in rows if r["k"] is not None and r[l]!=0]
    if len(xs)>30:
        kx=[x for x,_ in xs]; ly=[y for _,y in xs]
        b=st.covariance(kx,ly)/st.variance(kx)
        print(f"  {l} 코스피 상관 {st.correlation(kx,ly):+.2f} · 기울기 {b:+.2f}")
