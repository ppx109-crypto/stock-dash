import json,sys,functools
D=sys.argv[1]; OUT=sys.argv[2]
T=json.load(open(D+'/trend_out.json'));R=json.load(open(D+'/rev_out.json'));C=json.load(open(D+'/combine_out.json'))
E=1e-9; res={}
def stats(days):  # days: list of (date,pnl) sorted
    s=sum(p for _,p in days); cum=0;pk=0;mdd=0
    for _,p in days:
        cum+=p;pk=max(pk,cum);mdd=min(mdd,cum-pk)
    worst=min([p for _,p in days]+[0.0]) if days else 0.0
    worst_raw=min(p for _,p in days)
    mon={}
    for d,p in days: mon.setdefault(d[:6],[]).append(p)
    ms=[m for m,v in mon.items() if len(v)>=5]; mp=sum(1 for m in ms if sum(mon[m])>0)
    top5=sum(sorted([p for _,p in days],reverse=True)[:5])
    return {"합":s,"MDD":mdd,"최악":worst_raw,"월 양수율":mp/len(ms) if ms else 0,"월 양수":f"{mp}/{len(ms)}",
            "위5 몫":top5/s if s!=0 else None,"비":s/max(1,abs(mdd)),"거래 날":sum(1 for _,p in days if p!=0),"_달별":{m:sum(v) for m,v in mon.items()}}
SEG={"고르기 1~6월":("20260101","20260630"),"참고 7~8월":("20260701","20260831"),"참고 9~10월":("20260901","20261031"),"참고 7~10월":("20260701","20261031"),"전체":("00000000","99999999")}
def seg(daily,k,dates=None):
    a,b=SEG[k]; return [(d,daily[d]) for d in sorted(daily) if a<=d<=b and (dates is None or d in dates)]
def cmp(rec,calc,tol=1e-6):
    bad={}
    for k,v in rec.items():
        c=calc.get(k)
        if isinstance(v,(int,float)) and not isinstance(v,bool):
            if c is None or abs(v-c)>tol: bad[k]=(v,c)
        elif v!=c: bad[k]=(v,c)
    return bad
# 4) 날짜
dates=sorted(C['결합 날별']); res['4 날짜']={"결합 날 수":len(dates),"첫":dates[0],"끝":dates[-1],
  "회귀 날별 같음":sorted(R['고른 판 날별'])==dates,"추세 날 수":len(T['고른 판 날별']),
  "추세에만 있는 날":{d:T['고른 판 날별'][d] for d in sorted(set(T['고른 판 날별'])-set(dates))},
  "결합에 있는데 추세에 없는 날":sorted(set(dates)-set(T['고른 판 날별']))}
# 1) 고르기
def pick(tab,n_exp,recpick):
    names=[r['판'] for r in tab]; o={"후보 수":len(tab),"기대":n_exp,"이름 중복":len(names)-len(set(names))}
    reason_bad=[]
    for r in tab:
        exp=[]
        if not r['합']>0: exp.append('합 ≤ 0')
        if r['최악']< -15-E: exp.append('최악 < −15')
        if r['MDD']< -15-E: exp.append('MDD < −15')
        if exp!=r['탈락'] and set(exp)!=set(r['탈락']): reason_bad.append((r['판'],r['탈락'],exp))
        # 비/월양수율 일관성
        mp,mn=map(int,r['월 양수'].split('/'))
        if abs(r['월 양수율']-mp/mn)>1e-6 or abs(r['비']-r['합']/max(1,abs(r['MDD'])))>1e-5: reason_bad.append((r['판'],'비·율 불일치'))
    o['탈락 사유 불일치']=len(reason_bad); o['탈락 예시']=reason_bad[:5]
    el=[r for r in tab if r['합']>0 and r['최악']>=-15-E and r['MDD']>=-15-E]
    o['자격 수']=len(el)
    if not el: o['다시 고른 판']='(자격 없음→대조)'; return o
    mx=max(r['월 양수율'] for r in el); g=[r for r in el if r['월 양수율']>=mx-1e-9]
    g2=[r for r in g if (r['위5 몫'] is not None and r['위5 몫']<=0.35+E)] or g
    o['1순위 무리']=len(g); o['위5≤0.35 무리']=len([r for r in g if (r['위5 몫'] is not None and r['위5 몫']<=0.35+E)])
    g2s=sorted(g2,key=lambda r:(-r['비'],-r['합'],r['판']))
    o['다시 고른 판']=g2s[0]['판']; o['같음']=g2s[0]['판']==recpick
    o['상위 3']=[(r['판'],r['비'],r['합'],r['위5 몫']) for r in g2s[:3]]
    # 동률 경계: 6자리 반올림이라 1e-6 안 차이
    o['비 동률(1e-5 안)']=[r['판'] for r in g2s[1:] if abs(r['비']-g2s[0]['비'])<1e-5]
    o['경계 근처(자격·위5, ±1e-5)']=[(r['판'],r['MDD'],r['최악'],r['위5 몫']) for r in tab if abs(r['MDD']+15)<1e-5 or abs(r['최악']+15)<1e-5 or (r['위5 몫'] is not None and abs(r['위5 몫']-0.35)<1e-5)][:60]
    o['경계 근처 수']=len([1 for r in tab if abs(r['MDD']+15)<1e-5 or abs(r['최악']+15)<1e-5 or (r['위5 몫'] is not None and abs(r['위5 몫']-0.35)<1e-5)])
    return o
res['1 추세 고르기']=pick(T['후보 표'],192,T['고른 판'])
res['1 회귀 고르기']=pick(R['후보 표'],152,R['고른 판'])
# 후보 표의 고른 판 행 = 날별에서 다시 센 1~6월?
for nm,X in (('추세',T),('회귀',R)):
    row=[r for r in X['후보 표'] if r['판']==X['고른 판']][0]
    for lab,ds in (('183일만',set(dates)),('날별 전부',None)):
        c=stats(seg(X['고른 판 날별'],'고르기 1~6월',ds))
        res.setdefault('1 고른 판 행 대조',{})[nm+' '+lab]=cmp({k:v for k,v in row.items() if k not in('판','탈락')},c,1e-5)
# 2) 구간 성적
def segcheck(X,dk,rk,ds):
    o={}
    for k,v in X[rk].items():
        c=stats(seg(X[dk],k,ds)); b=cmp(v,c); o[k]=b if b else '일치'
    return o
for nm,X,pairs in (('추세',T,[('고른 판 날별','고른 판 성적'),('P2 본 날별','대조 P2 본')]),('회귀',R,[('고른 판 날별','고른 판 성적'),('P2R 날별','대조 P2R')])):
    for dk,rk in pairs:
        res.setdefault('2 구간 성적',{})[f'{nm} {rk} (183일)']=segcheck(X,dk,rk,set(dates))
        if nm=='추세': res['2 구간 성적'][f'{nm} {rk} (187일 전부)']=segcheck(X,dk,rk,None)
    res.setdefault('2 대조 날별 같음',{})[nm]=sum(1 for d in X[pairs[0][0]] if abs(X[pairs[0][0]][d]-X[pairs[1][0]][d])>1e-12)
# 3) combine
CD=C['결합 날별']
o={}
for k,v in C['결합 성적'].items():
    c=stats(seg(CD,k)); b=cmp(v,c); o[k]=b if b else '일치'
res['3 결합 성적']=o
c710=stats(seg(CD,'참고 7~10월')); mon={m:v for m,v in c710['_달별'].items()}
res['3 달별']={m:{"기록":C['7~10월 달별'].get(m),"다시":mon.get(m)} for m in sorted(set(mon)|set(C['7~10월 달별']))}
res['3 달별 불일치']=sum(1 for m,x in res['3 달별'].items() if x['기록'] is None or x['다시'] is None or abs(x['기록']-x['다시'])>1e-6)
# 대조 = P2 T+R 날별 합 (183일)
ctl={d:T['P2 본 날별'][d]+R['P2R 날별'][d] for d in dates}
cs=stats(seg(ctl,'참고 7~10월')); res['3 대조 다시(P2본+P2R)']={k:(C['대조 P2(T + R)']['참고 7~10월'][k],cs[k]) for k in ('합','MDD','최악','위5 몫','비')}
cond={"① 4달 중 양수 ≥ 3":sum(1 for m in mon.values() if m>0)>=3 and len(mon)==4,"② MDD ≥ −15":c710['MDD']>=-15-E,"③ 최악 ≥ −15":c710['최악']>=-15-E,
      "④ 위 5일 ≤ 35%":c710['위5 몫']<=0.35+E,"⑤ 비 ≥ P2":c710['비']>=C['대조 P2(T + R)']['참고 7~10월']['비']-E}
res['3 조건']={k:{"기록":C['참고 조건'][k],"다시":v} for k,v in cond.items()}
res['3 조건 불일치']=sum(1 for k,v in cond.items() if C['참고 조건'][k]!=v)
pj='참고 지지' if all(cond.values()) else '참고 지지 안 됨'
res['3 판정']={"기록":C['참고 판정'],"다시":pj}
# 날 나누기
TD=T['고른 판 날별'];RD=R['고른 판 날별'];cnt={"추세와 같음만":0,"회귀와 같음만":0,"둘 다 같음":0,"어느 것도 아님":[]}
for d in dates:
    a=abs(CD[d]-TD.get(d,float('nan')))<1e-9; b=abs(CD[d]-RD[d])<1e-9
    if a and b: cnt["둘 다 같음"]+=1
    elif a: cnt["추세와 같음만"]+=1
    elif b: cnt["회귀와 같음만"]+=1
    else: cnt["어느 것도 아님"].append((d,CD[d],TD.get(d),RD[d]))
cnt["어느 것도 아님 수"]=len(cnt["어느 것도 아님"]); cnt["어느 것도 아님"]=cnt["어느 것도 아님"][:10]
cnt["기록 추세 도는 날 수"]=C['추세 도는 날 수']
# 둘 다 0 이 아닌 날(겹침) 확인
cnt["추세·회귀 둘 다 0 아닌 날"]=[d for d in dates if TD.get(d,0)!=0 and RD[d]!=0][:20]
res['3 날 나누기']=cnt
json.dump(res,open(OUT,'w'),ensure_ascii=False,indent=1,default=str)
print(json.dumps(res,ensure_ascii=False,indent=1,default=str))
