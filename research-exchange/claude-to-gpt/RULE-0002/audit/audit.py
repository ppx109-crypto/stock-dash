# RULE-0002 독립 감사: 공개 파일만 읽음(비공개 폴더 안 읽음). 실행: python3 -I audit.py
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE); BASE = os.path.dirname(R2); R1 = os.path.join(BASE, 'RULE-0001')
O = json.load(open(os.path.join(R2, 'rule2_out.json'), encoding='utf-8'))
T = json.load(open(os.path.join(R1, 'trend_out.json'), encoding='utf-8'))
RV = json.load(open(os.path.join(R1, 'rev_out.json'), encoding='utf-8'))
C1 = json.load(open(os.path.join(R1, 'combine_out.json'), encoding='utf-8'))
E = 1e-9; TOL = 1e-6
lines = []; npass = nfail = 0
def out(s=''): lines.append(str(s))
def chk(name, ok, detail=''):
    global npass, nfail
    if ok: npass += 1
    else: nfail += 1
    out(('PASS ' if ok else 'FAIL ') + name + ((' | ' + str(detail)) if detail != '' else ''))

# ---------- 1. 날 목록 ----------
DAYS = sorted(C1['결합 날별'])
SEL = [d for d in DAYS if d <= '20260630']; CHK = [d for d in DAYS if d >= '20260701']
out('== 1. 날 목록')
chk('183일', len(DAYS) == 183, f'{len(DAYS)}일 {DAYS[0]}~{DAYS[-1]}')
chk('첫날 0108 · 끝날 1012', DAYS[0] == '20260108' and DAYS[-1] == '20261012')
chk('rule2 결합 날별 날짜 = RULE-0001 결합 날짜', sorted(O['결합 날별']) == DAYS)
chk('rev P2R 날별 날짜 = 183일', sorted(RV['P2R 날별']) == DAYS)
extra = sorted(set(O['고른 판 날별']) - set(DAYS))
chk('고른 판 · P2 본 날별은 183일 포함', set(DAYS) <= set(O['고른 판 날별']) and set(DAYS) <= set(O['P2 본 날별']), f'183일 밖 날 {extra}')
out(f'   SEL {len(SEL)}일 · CHK {len(CHK)}일')
SEGS = {'고르기 1~6월': ('20260101', '20260630'), '참고 7~8월': ('20260701', '20260831'),
        '참고 9~10월': ('20260901', '20261031'), '참고 7~10월': ('20260701', '20261031'), '전체': ('0', '9')}

# ---------- 2. 성적 정의 ----------
def stats(daily, days):
    ps = [daily[d] for d in days]
    s = sum(ps); cum = pk = mdd = 0.0
    for p in ps:
        cum += p; pk = max(pk, cum); mdd = min(mdd, cum - pk)
    mon = {}
    for d in days: mon.setdefault(d[:6], []).append(daily[d])
    ms = [m for m, v in mon.items() if len(v) >= 5]; mp = sum(1 for m in ms if sum(mon[m]) > 0)
    top5 = sum(sorted(ps, reverse=True)[:5])
    return {'합': s, 'MDD': mdd, '최악': min(ps) if ps else 0.0, '월 양수율': mp / len(ms) if ms else 0.0,
            '월 양수': f'{mp}/{len(ms)}', '위5 몫': (top5 / s) if s > 0 else None, '비': s / max(1, abs(mdd)),
            '거래 날': sum(1 for p in ps if p != 0), '_달': {m: sum(v) for m, v in mon.items()}}
def segdays(k, base=DAYS):
    a, b = SEGS[k]; return [d for d in base if a <= d <= b]
def cmp(rep, calc):
    bad = {}
    for k, v in rep.items():
        c = calc.get(k)
        if v is None or c is None:
            if v != c: bad[k] = (v, c)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            if abs(v - c) > TOL: bad[k] = (v, c)
        elif v != c: bad[k] = (v, c)
    return bad
out('== 2. 구간 성적 다시 셈(183일 · 허용 1e-6)')
P2R = RV['P2R 날별']; G = O['고른 판 날별']; P2 = O['P2 본 날별']; CB = O['결합 날별']
CTRL = {d: P2[d] + P2R[d] for d in DAYS}  # 대조 P2(T+R) = P2 본 + P2R
for daily, rk, lab in ((CB, '결합(고른 추세 + P2R 날 나누기) 성적', '결합'), (CTRL, '대조 P2(T + R) 성적', '대조 P2(T+R)'),
                       (G, '추세만 성적', '고른 판(추세만)'), (P2, 'P2 추세 본 성적', 'P2 본')):
    for k, v in O[rk].items():
        b = cmp(v, stats(daily, segdays(k)))
        chk(f'{lab} · {k}', not b, b if b else '')
# 187일로 셌다면? (참고)
alt = cmp(O['추세만 성적']['전체'], stats(G, sorted(G)))
out(f'   참고: 고른 판 "전체"를 187일로 세면 차이 {sorted(alt) if alt else "없음"} → 보고는 183일 기준')
# 후보 표의 고른 판 · 출발 판 행 = 날별에서 다시 센 1~6월
for nm, daily in ((O['고른 판'], G), (O['출발(P2 본)'], P2)):
    row = [r for r in O['후보 표'] if r['판'] == nm][0]
    c = stats(daily, SEL)
    b = {k: (row[k], c[k]) for k in ('합', 'MDD', '최악', '월 양수율', '위5 몫', '비', '거래 날') if abs(row[k] - c[k]) > 1e-5}
    chk(f'후보 표 행 = 날별 1~6월 다시 셈 ({nm.split()[-3]})', not b, b if b else '')

# ---------- 3. P2 본 날별 = RULE-0001 ----------
out('== 3. P2 본 날별 대조')
m = max(abs(P2[d] - T['P2 본 날별'][d]) for d in DAYS)
chk('rule2 P2 본 날별 = RULE-0001 trend P2 본 날별(183일)', m <= 1e-12, f'최대 차 {m}')
m2 = max(abs(P2[d] - T['P2 본 날별'][d]) for d in set(P2) & set(T['P2 본 날별']))
out(f'   187일 전체 최대 차 {m2}')
dg = [d for d in DAYS if abs(G[d] - P2[d]) > 1e-12]
out(f'   고른 판(GB1) vs P2 본이 다른 날 {len(dg)}개: ' + ', '.join(f'{d}:{P2[d]:+.3f}->{G[d]:+.3f}' for d in dg))

# ---------- 4. 결합 ----------
out('== 4. 결합 = 추세 날이면 고른 판 · 아니면 P2R')
cls = {'둘 다 같음(모호)': [], '고른 판만 맞음': [], 'P2R만 맞음': [], '둘 다 아님': []}
for d in DAYS:
    eg = abs(CB[d] - G[d]) <= 1e-12; er = abs(CB[d] - P2R[d]) <= 1e-12
    cls['둘 다 같음(모호)' if eg and er else '고른 판만 맞음' if eg else 'P2R만 맞음' if er else '둘 다 아님'].append(d)
for k, v in cls.items(): out(f'   {k}: {len(v)}일')
chk('모든 날 결합 ∈ {고른 판, P2R}', not cls['둘 다 아님'], cls['둘 다 아님'][:10])
gnz_r = [d for d in cls['P2R만 맞음'] if G[d] != 0]
out(f'   고른 판 ≠ 0인데 결합이 P2R을 쓴 날: {len(gnz_r)}개 {gnz_r[:10]}')
pnz_g = [d for d in cls['고른 판만 맞음'] if P2R[d] != 0]
out(f'   P2R ≠ 0인데 결합이 고른 판을 쓴 날: {len(pnz_g)}개')
amb = cls['둘 다 같음(모호)']; amb0 = [d for d in amb if G[d] == 0 and P2R[d] == 0]
lo = len(cls['고른 판만 맞음']); hi = lo + len(amb)
chk('추세 도는 날 122가 가능 범위 안', lo <= O['추세 도는 날 수'] <= hi,
    f'확실 {lo} ~ 최대 {hi}(모호 {len(amb)}일 중 둘 다 0인 날 {len(amb0)}) · 보고 {O["추세 도는 날 수"]}')
chk('추세 도는 날 수 = RULE-0001(122)', O['추세 도는 날 수'] == C1['추세 도는 날 수'])
# RULE-0001 결합과의 차이 = 고른 판 vs P2 본 차이 날만이어야 함
C1d = C1['결합 날별']
dc = [d for d in DAYS if abs(CB[d] - C1d[d]) > 1e-12]
exp_dc = [d for d in DAYS if abs(CB[d] - C1d[d]) > 1e-12 or False]
okdc = all(abs((CB[d] - C1d[d]) - (G[d] - P2[d])) <= 1e-9 for d in dc) and set(dc) <= set(dg)
chk('RULE-0001 결합과 다른 날은 모두 GB 바뀐 날이며 차이 = 고른 판 − P2 본', okdc, f'다른 날 {dc}')
dg_not_in = [d for d in dg if d not in dc]
out(f'   GB로 바뀐 날 중 결합에 안 들어간 날(P2R 날로 판단): {dg_not_in}')
# RULE-0001 결합 자체 = P2 본/P2R 나누기, 같은 날 나누기를 쓰는지(추세 날 집합이 같은지) 일관성
incons = []
for d in DAYS:
    r1_trend = abs(C1d[d] - P2[d]) <= 1e-12; r1_rev = abs(C1d[d] - P2R[d]) <= 1e-12
    r2_trend = abs(CB[d] - G[d]) <= 1e-12; r2_rev = abs(CB[d] - P2R[d]) <= 1e-12
    if (r1_trend and not r1_rev) and (r2_rev and not r2_trend): incons.append(d)
    if (r1_rev and not r1_trend) and (r2_trend and not r2_rev): incons.append(d)
chk('RULE-0001 결합과 날 나누기가 어긋나는 확실한 날 없음', not incons, incons)

# ---------- 5. 단계 고르기 다시 하기 ----------
out('== 5. 단계 고르기(후보 표만으로)')
PARTS = ['V', 'AMIN', 'AMAX', 'PB', 'EM', 'LL', 'BL', 'P3', 'N', 'EC', 'GB', 'DEAD', 'DCAP']
def parse(n):
    d = {}
    for tok in n.split():
        for p in sorted(PARTS, key=len, reverse=True):
            if tok.startswith(p) and tok[len(p):].isdigit(): d[p] = int(tok[len(p):]); break
    return d
ALT = {'N': [30, 50, 70], 'DCAP': [7, 12]}
def neighbors(cur):
    c = parse(cur); res = []
    for p in PARTS:
        vals = ALT.get(p, [0, 1])
        for v in vals:
            if v != c[p]:
                nd = dict(c); nd[p] = v; res.append(' '.join(f'{q}{nd[q]}' for q in PARTS))
    return res
TAB = O['후보 표']; steps = sorted(set(r['단계'] for r in TAB)); LOG = {s['단계']: s for s in O['단계 기록']}
cur = O['출발(P2 본)']; near = []
for s in steps:
    rows = [r for r in TAB if r['단계'] == s]
    chk(f'단계 {s} 후보 15개', len(rows) == 15, len(rows))
    chk(f'단계 {s} 지금 판 = 기록', LOG[s]['지금 판'] == cur, (LOG[s]['지금 판'], cur))
    names = [r['판'] for r in rows]
    others = [n for n in names if n != cur]
    nb_ok = cur in names and sorted(others) == sorted(neighbors(cur))
    diffs = [sum(1 for p in PARTS if parse(n)[p] != parse(cur)[p]) for n in others]
    chk(f'단계 {s} 이웃 = 부품 하나씩 바꾼 14판(N 다른 두 값 · DCAP 반대)', nb_ok and all(x == 1 for x in diffs), diffs)
    for r in rows:
        el = r['합'] > 0 and r['최악'] >= -15 - E and r['MDD'] >= -15 - E
        if el != r['자격']: chk(f'단계 {s} 자격 표시 {r["판"]}', False, (r['자격'], el))
        if abs(r['비'] - r['합'] / max(1, abs(r['MDD']))) > 1e-5: chk(f'단계 {s} 비 정의 {r["판"]}', False)
        for k, lim in (('MDD', -15), ('최악', -15), ('위5 몫', 0.35)):
            if r[k] is not None and abs(r[k] - lim) < 1e-5 and abs(r[k] - lim) > 0: near.append((s, r['판'], k, r[k]))
    el = [r for r in rows if r['합'] > 0 and r['최악'] >= -15 - E and r['MDD'] >= -15 - E]
    if not el:
        pick = cur
    else:
        mx = max(r['월 양수율'] for r in el); g = [r for r in el if r['월 양수율'] >= mx - E]
        g2 = [r for r in g if r['위5 몫'] is not None and r['위5 몫'] <= 0.35 + E] or g
        g2 = sorted(g2, key=lambda r: (-r['비'], -r['합'], r['판'])); pick = g2[0]['판']
        out(f'   단계 {s}: 자격 {len(el)} · 월양수율 최대 무리 {len(g)} · 위5≤0.35 {len([r for r in g if r["위5 몫"] is not None and r["위5 몫"] <= 0.35 + E])} · 1등 {pick} 비 {g2[0]["비"]} · 2등 {g2[1]["판"] if len(g2) > 1 else "-"} 비 {g2[1]["비"] if len(g2) > 1 else "-"}')
        ties = [r['판'] for r in g2[1:] if abs(r['비'] - g2[0]['비']) < 1e-5]
        if ties: out(f'   단계 {s}: 비 1e-5 안 동률 {ties} → 합 · 이름으로 갈림')
        # 동률 무리 중 1등과 이름 외엔 같은(완전 같은 성적) 판
        same = [r['판'] for r in g2[1:] if all(abs(r[k] - g2[0][k]) < 1e-9 for k in ('합', 'MDD', '비'))]
        if same: out(f'   단계 {s}: 1등과 성적이 완전히 같은 판(이름 순서로만 밀림) {same}')
    chk(f'단계 {s} 다시 고른 판 = 기록', pick == LOG[s]['고른 판'], (pick, LOG[s]['고른 판']))
    if pick == cur:
        chk(f'단계 {s}에서 멈춤(1등 = 지금 판) · 이후 단계 없음', s == steps[-1]); break
    cur = pick
chk('최종 고른 판 = 마지막 단계 고른 판', O['고른 판'] == cur, (O['고른 판'], cur))
chk('8단계 이하', len(steps) <= 8)
uniq = len(set(r['판'] for r in TAB))
chk('평가한 고유 판 수 = 후보 표 고유 판', uniq == O['평가한 고유 판 수'], (uniq, O['평가한 고유 판 수']))
out(f'   경계(−15 · 0.35)에서 1e-5 안이지만 같지 않은 값: {near if near else "없음"}')
eq15 = sum(1 for r in TAB if r['MDD'] == -15.0 or r['최악'] == -15.0)
out(f'   MDD 또는 최악이 정확히 −15.0으로 적힌 행 {eq15}개(하루 한도 15에서 잘린 값 · 반올림 뒤 −15 이상이라 자격 판단에 영향 없음; 원래 날별에서 결합 최악 = {min(CB[d] for d in SEL)!r})')

# ---------- 6. 참고 조건 ----------
out('== 6. 참고 조건(CHK 7~10월)')
def conds(x, ctrl):
    sx = stats(x, CHK); sc = stats(ctrl, CHK)
    mons = ['202607', '202608', '202609', '202610']; mp = sum(1 for m in mons if sx['_달'].get(m, 0) > 0)
    return {'①': mp >= 3, '②': sx['MDD'] >= -15 - E, '③': sx['최악'] >= -15 - E,
            '④': sx['위5 몫'] is not None and sx['위5 몫'] <= 0.35 + E, '⑤': sx['비'] >= sc['비'] - E}, sx, sc
def verdict(c): return '참고 지지' if all(c.values()) else '참고 지지 안 됨'
for lab, x, ctrl, rk, vk in (('주(결합 vs P2(T+R))', CB, CTRL, '참고 조건(결합 · 주 판정)', '참고 판정(주)'),
                             ('보조(추세만 vs P2 본)', G, P2, '참고 조건(추세만 · 보조)', '참고 판정(보조)')):
    c, sx, sc = conds(x, ctrl)
    rep = {k[0]: v for k, v in O[rk].items()}
    chk(f'{lab} 조건 ①~⑤ 같음', rep == c, f'다시 셈 {c} · 위5 {sx["위5 몫"]:.4f} · 비 {sx["비"]:.4f} vs 대조 {sc["비"]:.4f}')
    chk(f'{lab} 판정 같음', O[vk] == verdict(c), (O[vk], verdict(c)))
mb = {m: v for m, v in stats(CB, CHK)['_달'].items()}
b = {m: (O['7~10월 달별(결합)'][m], mb.get(m)) for m in O['7~10월 달별(결합)'] if abs(O['7~10월 달별(결합)'][m] - mb.get(m, 1e9)) > TOL}
chk('7~10월 달별(결합) 같음', not b, b if b else mb)

# ---------- 7. 아무 일도 안 하는 부품 ----------
out('== 7. 바꿔도 결과가 같은 부품(합 · MDD · 위5 · 최악이 지금 판과 같음)')
cur = O['출발(P2 본)']
for s in steps:
    rows = [r for r in TAB if r['단계'] == s]; cr = [r for r in rows if r['판'] == LOG[s]['지금 판']][0]
    noop = []
    for r in rows:
        if r is cr: continue
        if all(r[k] == cr[k] for k in ('합', 'MDD', '위5 몫', '최악')):
            pc, pr = parse(cr['판']), parse(r['판'])
            noop.append(next(f'{p}{pc[p]}->{pr[p]}' for p in PARTS if pc[p] != pr[p]))
    out(f'   단계 {s}: {noop if noop else "없음"}')
# 단계 사이에서 GB가 안 먹는 부품 조합
s0 = {r['판']: r for r in TAB if r['단계'] == 0}; s1 = [r for r in TAB if r['단계'] == 1]
same_gb = []
for r in s1:
    p = parse(r['판']); p['GB'] = 0; n = ' '.join(f'{q}{p[q]}' for q in PARTS)
    if n in s0 and n != r['판'] and all(s0[n][k] == r[k] for k in ('합', 'MDD', '위5 몫')): same_gb.append(n.replace(' ', ''))
out(f'   GB를 켜도 1~6월이 같은 판(GB0 판 이름): {same_gb}')

out(''); out(f'합계 PASS {npass} · FAIL {nfail}')
open(os.path.join(HERE, 'audit.out'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
