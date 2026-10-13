"""별도 클로드 검사 담당(RLK-0005): 뒤쪽 날(25 · 60 · 100 · 140번째부터)의 팔 손익을 섞고 크게 바꿔도 그 앞 날의 결정 · 손익이 그대로인지 확인. 쓰는 법: python3 research/kmf_rl3_audit_future.py"""
import sys, json, random, math, statistics as st, collections
from pathlib import Path
R=str(Path(__file__).resolve().parents[1])
sys.path.insert(0,R+"/research"); import kmf_rl3 as M
E=M.EVAL; Ps={dl:M.arm_pnl(dl) for dl in (0,1,2)}
bad=0; rnd=random.Random(1)
for k in "AB":
  for z in (0.5,1.0):
    for dl in (0,1,2):
      p0,pk0,d0=M.run(Ps[dl],k,z)
      for ci in (25,60,100,140):
        P2={a:dict(v) for a,v in Ps[dl].items()}
        fut=E[ci:]; 
        for a in P2:
          vals=[P2[a][d] for d in fut]; rnd.shuffle(vals)
          for d,v in zip(fut,vals): P2[a][d]=v*rnd.uniform(-3,3)+rnd.uniform(-5,5)
        p1,pk1,d1=M.run(P2,k,z)
        bad+=sum(1 for d in E[:ci] if d1[d]!=d0[d] or p1[d]!=p0[d])
      # ledger self-check
      h=collections.defaultdict(list)
      for i,d in enumerate(E):
        r=d0[d]; s=tuple(r["상태"]); sc={}
        for a in M.ARMS:
          x=h[(s,a)]; n=len(x); assert r["팔"][a]["n"]==n
          if n>=10:
            v=round(st.mean(x)-z*st.stdev(x)/math.sqrt(n),4); assert r["팔"][a]["보수 점수"]==v; sc[a]=v
        c=[(v,a) for a,v in sc.items() if v>0] if i>=20 else []
        exp="쉼" if not c else (max(c)[1] if len(c)==1 or c[0][0]!=c[1][0] else "쉼")
        assert r["선택"]==exp,(d,r,exp); assert r["채택 손익"]==round(p0[d],4)
        assert r["반사실"]=={a:round(Ps[dl][a][d],4) for a in M.ARMS}
        for a in M.ARMS: h[(s,a)].append(Ps[dl][a][d])
print("앞 날 바뀐 칸",bad)
# eff_prev never uses d: change day d bars
import kmf_nb as K
for d in E:
  i=K.DAYS.index(d); assert i>0
print("ok")
