# POOL-0002 독립 감사(agentP) — 공개 출력만 읽음
import json, sys, itertools, collections
D = sys.argv[1]
OUT = sys.argv[2]
W = json.load(open(D + '/pool_wf_out.json'))
C = json.load(open(D + '/pool_wf_out_candidates.json'))
EPS = 1e-9
TIE = 1e-6  # 후보 표 소수 6자리 반올림 → 이보다 가까우면 경계로 적음
BOTS = W['후보 봇']
rep = {}

# ---------- 1. 창마다 후보 수 · 고르기 · 탈락 사유 ----------
def reasons(r):
    out = []
    if not r['합'] > 0: out.append('합 ≤ 0')
    if not r['최악'] >= -15 - EPS: out.append('최악 < −15')
    if not r['MDD'] >= -15 - EPS: out.append('MDD < −15')
    return out

def select(cands):
    q = [r for r in cands if r['합'] > 0 and r['최악'] >= -15 - EPS and r['MDD'] >= -15 - EPS]
    if not q:
        return None, dict(fallback=True)
    m = max(r['월 양수율'] for r in q)
    g1 = [r for r in q if r['월 양수율'] == m]
    g2 = [r for r in g1 if r['위5 몫'] <= 0.35]
    applied = bool(g2)
    g = g2 if g2 else g1
    g.sort(key=lambda r: (-r['비'], -r['합'], r['판'], r['중재'], r['멈춤']))
    return g[0], dict(fallback=False, qualified=len(q), g1=len(g1), g2=len(g2), applied35=applied,
                      maxpos=m, top=g[:3], group=g, q=q)

s1 = dict(windows={}, mismatch=0, examples=[])
for wn, v in C.items():
    cands = v['후보']
    prio = v['봇 우선순위(창 안 비)']
    info = {}
    info['후보 수'] = len(cands)
    # 판 조합 · 중재 · 멈춤 모두 다른지(1,023 × 2 × 2)
    keys = set()
    name_order_bad = 0
    for r in cands:
        bots = r['판'].split('+')
        keys.add((frozenset(bots), r['중재'], r['멈춤']))
        if bots != sorted(bots, key=prio.index): name_order_bad += 1
    info['고유 (봇 집합·중재·멈춤)'] = len(keys)
    info['판 이름이 창 우선순위 순서가 아닌 수'] = name_order_bad
    info['봇 우선순위 집합 = 후보 봇 10개'] = sorted(prio) == sorted(BOTS)
    # 탈락 사유
    bad_reason = [r for r in cands if sorted(reasons(r)) != sorted(r['탈락'])]
    info['탈락 사유 불일치'] = len(bad_reason)
    info['탈락 사유 불일치 예시'] = bad_reason[:3]
    # 고르기
    pick, meta = select(cands)
    rec = v['고른 판']
    if pick is None:
        mine = dict(판='P2T+P2R', 중재='prio', 멈춤='real')
    else:
        mine = dict(판=pick['판'], 중재=pick['중재'], 멈춤=pick['멈춤'])
    same = (mine['판'] == rec['판'] and mine['중재'] == rec['중재'] and mine['멈춤'] == rec['멈춤'])
    info['다시 고른 판'] = mine
    info['기록 고른 판'] = rec
    info['같음'] = same
    info['대체 판 사용(기록/다시)'] = [v['대체 판 사용'], meta['fallback']]
    if not meta['fallback']:
        info['자격 판 수'] = meta['qualified']
        info['1순위 무리 수(월 양수율 최대)'] = meta['g1']
        info['월 양수율 최대'] = meta['maxpos']
        info['위5 ≤ 0.35 판 수'] = meta['g2']
        info['35% 조건 적용(기록/다시)'] = [rec.get('35% 조건 적용'), meta['applied35']]
        if rec.get('35% 조건 적용') != meta['applied35']: same = False
        info['위 3판(비 순)'] = [{k: t[k] for k in ('판', '중재', '멈춤', '합', 'MDD', '최악', '월 양수율', '위5 몫', '비')} for t in meta['top']]
        # 동률 · 경계 점검
        border = {}
        q = meta['q']; g1 = meta['g1']
        border['자격 경계 판 수'] = sum(1 for r in cands if abs(r['MDD'] + 15) < TIE or abs(r['최악'] + 15) < TIE or abs(r['합']) < TIE)
        # 경계 판 중 월 양수율 최대 무리에 들 수 있는 것(이 판들이 1순위·결과를 바꿀 수 있는지)
        bset = [r for r in cands if abs(r['MDD'] + 15) < TIE or abs(r['최악'] + 15) < TIE]
        # 경계 판을 모두 넣거나 모두 뺐을 때 결과
        alt_in = [r for r in cands if (r['합'] > 0 and r['최악'] >= -15 - TIE and r['MDD'] >= -15 - TIE)]
        alt_out = [r for r in cands if (r['합'] > 0 and r['최악'] >= -15 + TIE and r['MDD'] >= -15 + TIE)]
        def pickname(lst):
            p, m2 = select(lst)
            return None if p is None else (p['판'], p['중재'], p['멈춤'])
        border['경계 판 모두 자격 · 고른 판'] = pickname(alt_in)
        border['경계 판 모두 탈락 · 고른 판'] = pickname(alt_out)
        border['위5 경계 판 수(|위5−0.35| < 1e-6, 1순위 무리)'] = sum(1 for r in q if r['월 양수율'] == meta['maxpos'] and abs(r['위5 몫'] - 0.35) < TIE)
        # 1순위 경계: 월 양수율 최대와 1e-6 안에 다른 값
        border['월 양수율 근접 다른 값'] = sorted({r['월 양수율'] for r in q if 0 < meta['maxpos'] - r['월 양수율'] < TIE})
        grp = meta['group']
        if len(grp) > 1:
            border['1·2위 비 차'] = grp[0]['비'] - grp[1]['비']
            border['비 근접(1e-6 안) 판 수'] = sum(1 for r in grp[1:] if grp[0]['비'] - r['비'] < TIE)
            border['비 근접 판'] = [(r['판'], r['중재'], r['멈춤'], r['비'], r['합']) for r in grp[1:] if grp[0]['비'] - r['비'] < TIE][:5]
        info['경계'] = border
    if not same:
        s1['mismatch'] += 1
        if len(s1['examples']) < 3: s1['examples'].append(dict(창=wn, 기록=rec, 다시=mine))
    s1['windows'][wn] = info
rep['1 고르기 다시'] = s1

# 고른 판 창 성적 = 후보 표 행?
s1b = dict(mismatch=0, examples=[])
for m, v in W['걸어가기 고른 판(달별)'].items():
    cw = C['A ' + m]
    row = [r for r in cw['후보'] if r['판'] == v['판'] and r['중재'] == v['중재'] and r['멈춤'] == v['멈춤']]
    if len(row) != 1:
        s1b['mismatch'] += 1; s1b['examples'].append(dict(달=m, 문제='후보 행 없음')); continue
    r = row[0]; cs = v['창 성적']
    diffs = {k: (cs[k], r[k]) for k in ('합', 'MDD', '최악', '월 양수율', '위5 몫', '비') if abs(cs[k] - r[k]) > 5e-7}
    if diffs:
        s1b['mismatch'] += 1
        if len(s1b['examples']) < 3: s1b['examples'].append(dict(달=m, 차=diffs))
rep['1b 고른 판 창 성적 = 후보 표 행'] = s1b

# ---------- 2. 달별 고른 판 = A 창 고른 판 · 창 끝 < 그 달 첫날 ----------
daily = W['걸어가기 날별']
days = sorted(daily)
s2 = dict(mismatch=0, examples=[], rows={})
for m, v in W['걸어가기 고른 판(달별)'].items():
    cw = C['A ' + m]
    rec = cw['고른 판']
    same = (rec['판'] == v['판'] and rec['중재'] == v['중재'] and rec['멈춤'] == v['멈춤'])
    first = min(d for d in days if d[:6] == m)
    end = cw['창'][1]
    prev_days = [d for d in days if d < first]
    ok_end = end < first
    # 창 끝이 그 달 앞 마지막 평가 날인지(장부 범위 안에서만 확인 가능)
    last_prev = prev_days[-1] if prev_days else None
    tight = (last_prev == end) if last_prev else None
    row = dict(같은판=same, 창=cw['창'], 달첫날=first, 창끝_lt_첫날=ok_end, 창끝_eq_앞달마지막날=tight)
    s2['rows'][m] = row
    if not (same and ok_end and (tight in (True, None))):
        s2['mismatch'] += 1
        if len(s2['examples']) < 3: s2['examples'].append(dict(달=m, **row))
# 창 날 수 연속성: 창 n+1 날 수 − 창 n 날 수 = 장부에서 그 달 날 수
months = sorted(W['걸어가기 고른 판(달별)'])
cnt_m = collections.Counter(d[:6] for d in days)
s2['날 수 연속'] = []
for a, b in zip(months, months[1:]):
    da = C['A ' + a]['창'][2]; db = C['A ' + b]['창'][2]
    s2['날 수 연속'].append([a, b, db - da, cnt_m[a], db - da == cnt_m[a]])
    if db - da != cnt_m[a]: s2['mismatch'] += 1
s2['창 시작 모두 20260108'] = all(C[k]['창'][0] == '20260108' for k in C)
s2['A202604 창 날 수 + 장부 날 수'] = C['A 202604']['창'][2] + len(days)
s2['장부 날 수'] = len(days)
s2['장부 첫·끝'] = [days[0], days[-1]]
# B 창: 반 나누기 판 = B 창 고른 판
b = C['B 앞 반']['고른 판']; hb = W['반 나누기']
s2['B 고른 판 = 반 나누기 판'] = (b['판'] == hb['판'] and b['중재'] == hb['중재'] and b['멈춤'] == hb['멈춤'])
if not s2['B 고른 판 = 반 나누기 판']: s2['mismatch'] += 1
rep['2 달별 판 · 창 밖 자료'] = s2

# ---------- 3. 날별 장부로 성적 다시 셈 ----------
def stats(dd, months_eval, min_days=5):
    ds = sorted(dd)
    tot = sum(dd[d] for d in ds)
    cum = 0.0; peak = 0.0; mdd = 0.0; peak_d = None; best = None
    peak_nz = None  # 고점을 첫날 누적부터 잡는 판(0 포함 안 함)
    mdd2 = 0.0; pk2 = None
    for d in ds:
        cum += dd[d]
        if cum > peak: peak = cum; peak_d = d
        dd_ = cum - peak
        if dd_ < mdd: mdd = dd_; best = (peak_d, d)
        pk2 = cum if pk2 is None else max(pk2, cum)
        mdd2 = min(mdd2, cum - pk2)
    worst = min(dd[d] for d in ds)
    mon = collections.defaultdict(float); mc = collections.Counter()
    for d in ds: mon[d[:6]] += dd[d]; mc[d[:6]] += 1
    ev = [m for m in months_eval if mc[m] >= min_days]
    pos = sum(1 for m in ev if mon[m] > 0)
    top5 = sorted((dd[d] for d in ds), reverse=True)[:5]
    share = sum(top5) / tot if tot > 0 else None
    return dict(합=tot, MDD=mdd, MDD_고점0제외=mdd2, 최악=worst, 월양수=f'{pos}/{len(ev)}', 월양수율=pos / len(ev),
                위5몫=share, 비=tot / max(1, abs(mdd)), 낙폭구간=best, 월별=dict(mon))

ms = ['2026%02d' % i for i in range(4, 11)]
A = stats(daily, ms)
rec = W['걸어가기 성적(4~10월)']
cmp_keys = [('합', '합'), ('MDD', 'MDD'), ('최악', '최악'), ('월양수율', '월 양수율'), ('위5몫', '위5 몫'), ('비', '비')]
s3 = dict(mismatch=0, examples=[])
def cmpd(mine, rec, tag):
    out = {}
    for a, b in cmp_keys:
        out[b] = [mine[a], rec[b], abs(mine[a] - rec[b]) <= 1e-9 * max(1, abs(rec[b]))]
        if not out[b][2]:
            s3['mismatch'] += 1
            if len(s3['examples']) < 3: s3['examples'].append(dict(어디=tag, 칸=b, 다시=mine[a], 기록=rec[b]))
    out['월 양수'] = [mine['월양수'], rec['월 양수'], mine['월양수'] == rec['월 양수']]
    if not out['월 양수'][2]: s3['mismatch'] += 1
    return out
s3['4~10월'] = cmpd(A, rec, '4~10월')
s3['MDD 고점 0 제외 판'] = A['MDD_고점0제외']
six = {d: x for d, x in daily.items() if d[:6] <= '202609'}
S6 = stats(six, ms[:6])
s3['완료 6달'] = cmpd(S6, W['완료 6달(4 ~ 9월) 성적'], '완료 6달')
# 월별
mm = {}
for m in ms:
    r = W['월별(걸어가기)'].get(m)
    ok = r is not None and abs(A['월별'].get(m, 0) - r) < 1e-9
    mm[m] = [A['월별'].get(m), r, ok]
    if not ok: s3['mismatch'] += 1
s3['월별'] = mm
# 조건 · 판정
ctl = W['대조(같은 날)']
thr = max(ctl['P2']['비'], ctl['v12a']['비'])
pos_n = int(A['월양수'].split('/')[0])
cond = {'① 월 양수 ≥ 6/7': pos_n >= 6, '② MDD ≥ −15': A['MDD'] >= -15 - EPS, '③ 최악 ≥ −15': A['최악'] >= -15 - EPS,
        '④ 위 5일 몫 ≤ 35%': A['위5몫'] is not None and A['위5몫'] <= 0.35, '⑤ 비 ≥ 대조 최대': A['비'] >= thr}
s3['⑤ 문턱(대조 P2·v12a 비 최대)'] = thr
s3['조건(다시/기록)'] = {k: [cond[k], W['조건'].get(k)] for k in cond}
for k in cond:
    if cond[k] != W['조건'].get(k):
        s3['mismatch'] += 1
        if len(s3['examples']) < 3: s3['examples'].append(dict(어디='조건', 칸=k, 다시=cond[k], 기록=W['조건'].get(k)))
verdict = '지지' if all(cond.values()) else '지지 안 됨'
s3['판정(다시/기록)'] = [verdict, W['판정']]
if verdict != W['판정']: s3['mismatch'] += 1
# 대조별 증분 합 = 걸어가기 합 − 대조 합(대조 날별 장부 비공개 → 합 차만 확인)
s3['증분 합 = 걸어가기 합 − 대조 합'] = {k: [A['합'] - ctl[k]['합'], W['대조별 증분 95%(보고만)'][k]['증분 합'],
                                    abs(A['합'] - ctl[k]['합'] - W['대조별 증분 95%(보고만)'][k]['증분 합']) < 1e-9] for k in ctl}
for k, v in s3['증분 합 = 걸어가기 합 − 대조 합'].items():
    if not v[2]: s3['mismatch'] += 1
# 대조 성적 내부 일관: 비 = 합/max(1,|MDD|)
s3['대조 비 내부 일관'] = {}
for grp in ('대조(같은 날)', '대조(뒤 반)', '대조 완료 6달'):
    for k, v in W[grp].items():
        ok = abs(v['비'] - v['합'] / max(1, abs(v['MDD']))) < 1e-9
        s3['대조 비 내부 일관'][grp + ' ' + k] = ok
        if not ok: s3['mismatch'] += 1
rep['3 날별 장부 성적 다시 셈'] = s3

# ---------- 4. 후보 평가 횟수 ----------
n = sum(len(v['후보']) for v in C.values())
rep['4 후보 평가 횟수'] = dict(기록=W['후보 평가 횟수'], 곱=4092 * 8, 후보표합=n, 판수=W['판 수'], 고른창수=W['고른 창 수'],
                          불일치=int(not (W['후보 평가 횟수'] == 4092 * 8 == n and W['판 수'] == 4092 and W['고른 창 수'] == 8 == len(C))))

# ---------- 5. H8 진단(기록만) ----------
h8 = dict(달별=[], 바뀐횟수=0)
prev = None
for m in months:
    v = W['걸어가기 고른 판(달별)'][m]
    bots = v['판'].split('+')
    row = dict(달=m, 봇=bots, 봇수=len(bots), 중재=v['중재'], 멈춤=v['멈춤'], 창우선순위=C['A ' + m]['봇 우선순위(창 안 비)'])
    if prev:
        ov = set(bots) & set(prev['봇'])
        row['앞 달과 겹친 봇 수'] = len(ov)
        row['빠진 봇'] = sorted(set(prev['봇']) - set(bots)); row['들어온 봇'] = sorted(set(bots) - set(prev['봇']))
        row['봇 구성 바뀜'] = set(bots) != set(prev['봇'])
        row['판 전체(구성·중재·멈춤) 바뀜'] = (set(bots) != set(prev['봇']) or v['중재'] != prev['중재'] or v['멈춤'] != prev['멈춤'])
        h8['바뀐횟수'] += int(row['봇 구성 바뀜'])
    h8['달별'].append(row); prev = row
h8['판 전체 바뀐 횟수'] = sum(1 for r in h8['달별'][1:] if r['판 전체(구성·중재·멈춤) 바뀜'])
h8['봇별 쓰인 달 수'] = dict(collections.Counter(b for r in h8['달별'] for b in r['봇']))
h8['멈춤 mtm 고른 달 수'] = sum(1 for r in h8['달별'] if r['멈춤'] == 'mtm')
# 창별 우선순위 변화: 앞 창과 순서 다른 자리 수
pr = []
ks = ['A ' + m for m in months]
for a, b in zip(ks, ks[1:]):
    pa = C[a]['봇 우선순위(창 안 비)']; pb = C[b]['봇 우선순위(창 안 비)']
    pr.append(dict(창=[a, b], 자리바뀐수=sum(1 for x, y in zip(pa, pb) if x != y), 순위변동={x: pa.index(x) - pb.index(x) for x in pa if pa.index(x) != pb.index(x)}))
h8['창별 우선순위 변화'] = pr
# 가장 깊은 낙폭 구간
pk, tr = A['낙폭구간']
m_of = lambda d: W['걸어가기 고른 판(달별)'][d[:6]]
seg = []
cum = 0.0
for d in days:
    cum += daily[d]
    if pk < d <= tr:
        p = m_of(d); seg.append(dict(날=d, 손익=round(daily[d], 4), 누적=round(cum, 4), 판=p['판'], 중재=p['중재'], 멈춤=p['멈춤']))
cpk = sum(daily[d] for d in days if d <= pk)
# 회복 날
rec_d = None; cum = 0.0
for d in days:
    cum += daily[d]
    if d > tr and cum >= cpk - 1e-12: rec_d = d; break
h8['가장 깊은 낙폭'] = dict(고점날=pk, 고점누적=cpk, 바닥날=tr, 낙폭=A['MDD'], 날수=len(seg), 회복날=rec_d, 구간=seg)
# 낙폭 2 ~ 3위(겹치지 않는 구간)
rep['5 H8 진단(기록만)'] = h8

rep['요약 불일치 수'] = {'1 고르기': s1['mismatch'] + s1b['mismatch'] + sum(w['탈락 사유 불일치'] for w in s1['windows'].values()),
                     '2 달별 판·창 밖': s2['mismatch'], '3 성적·조건·판정': s3['mismatch'], '4 평가 횟수': rep['4 후보 평가 횟수']['불일치']}
json.dump(rep, open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(rep['요약 불일치 수'], ensure_ascii=False))
