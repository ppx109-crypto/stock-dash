import json, sys
D, OUT = sys.argv[1], sys.argv[2]
W = json.load(open(D + '/pool_wf_out.json')); C = json.load(open(D + '/pool_wf_out_candidates.json'))
rep = json.load(open(OUT))
dd = W['걸어가기 날별']; days = sorted(dd); pick = W['걸어가기 고른 판(달별)']
pan = lambda d: '%s/%s/%s' % (pick[d[:6]]['판'], pick[d[:6]]['중재'], pick[d[:6]]['멈춤'])
ex = {}
ex['−14.99 이하 날'] = [dict(날=d, 손익=round(dd[d], 4), 판=pan(d)) for d in days if dd[d] <= -14.99]
ex['위 5일'] = [dict(날=d, 손익=round(dd[d], 4), 판=pan(d)) for d in sorted(days, key=lambda d: -dd[d])[:5]]
# 겹치지 않는 낙폭 구간(고점 → 회복 전 바닥) 모두 구해 깊은 순 3개
segs = []; cum = 0; peak = 0; pd = None; low = 0; ld = None
for d in days:
    cum += dd[d]
    if cum >= peak:
        if low < 0: segs.append(dict(고점날=pd, 바닥날=ld, 낙폭=round(low, 4), 회복날=d))
        peak = cum; pd = d; low = 0; ld = None
    elif cum - peak < low: low = cum - peak; ld = d
if low < 0: segs.append(dict(고점날=pd, 바닥날=ld, 낙폭=round(low, 4), 회복날=None))
segs.sort(key=lambda s: s['낙폭'])
for s in segs[:3]: s['쓰인 판'] = sorted({pan(d) for d in days if s['고점날'] < d <= s['바닥날']})
ex['낙폭 구간 깊은 순 3개(겹침 없음)'] = segs[:3]
# 6자리 동률로 갈린 창
tie = {}
for wn, w in rep['1 고르기 다시']['windows'].items():
    b = w.get('경계', {})
    if b.get('비 근접(1e-6 안) 판 수'):
        tie[wn] = dict(고른=w['다시 고른 판'], 동률=b['비 근접 판'],
                       갈린_잣대='중재 사전순' if b['비 근접 판'][0][0] == w['다시 고른 판']['판'] else '판 이름 사전순')
ex['6자리 동률(비·합 같음)로 이름·중재 순서에서 갈린 창'] = tie
rep['보충'] = ex
json.dump(rep, open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(ex, ensure_ascii=False, indent=0))
