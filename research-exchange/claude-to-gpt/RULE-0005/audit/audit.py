# RULE-0005 독립 감사: 공개 파일만 읽음(비공개 폴더 안 읽음). 실행: python3 -I audit.py
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R5 = os.path.dirname(HERE); BASE = os.path.dirname(R5); R1 = os.path.join(BASE, 'RULE-0001')
def L(p): return json.load(open(p, encoding='utf-8'))
O = L(os.path.join(R5, 'rule5_out.json'))
T = L(os.path.join(R1, 'trend_out.json')); RV = L(os.path.join(R1, 'rev_out.json')); C1 = L(os.path.join(R1, 'combine_out.json'))
E = 1e-9; TOL = 1e-6
lines = []; npass = nfail = 0
def out(s=''): lines.append(str(s))
def chk(name, ok, detail=''):
    global npass, nfail
    if ok: npass += 1
    else: nfail += 1
    out(('PASS ' if ok else 'FAIL ') + name + ((' | ' + str(detail)) if detail != '' else ''))

# ---------- 1. 날 ----------
out('== 1. 날 목록')
DAYS = sorted(C1['결합 날별'])
SEL = [d for d in DAYS if d <= '20260630']; CHK = [d for d in DAYS if d > '20260630']
chk('183일', len(DAYS) == 183, f'{len(DAYS)}일 {DAYS[0]}~{DAYS[-1]} · SEL {len(SEL)} · CHK {len(CHK)}')
chk('rule5 결합 날별 날짜 = RULE-0001 183일', sorted(O['결합 날별']) == DAYS)
B = O['판']; D = O['판별 전체 날별(추세)']
chk('판 8개 · 날별 8개', len(B) == 8 and sorted(D) == sorted(B), len(B))
chk('모든 판 날별이 183일 포함', all(set(DAYS) <= set(D[b]) for b in B))
chk('P2R 날별 = 183일', sorted(RV['P2R 날별']) == DAYS)
SEGS = {'고르기 1~6월': ('20260101', '20260630'), '참고 7~8월': ('20260701', '20260831'),
        '참고 9~10월': ('20260901', '20261031'), '참고 7~10월': ('20260701', '20261031'), '전체': ('0', '9')}
def segdays(k, base=DAYS):
    a, b = SEGS[k]; return [d for d in base if a <= d <= b]
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
def cmp(rep, calc, keys=None):
    bad = {}
    for k, v in rep.items():
        if keys and k not in keys: continue
        c = calc.get(k)
        if v is None or c is None:
            if v != c: bad[k] = (v, c)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            if abs(v - c) > TOL: bad[k] = (v, c)
        elif v != c: bad[k] = (v, c)
    return bad

# ---------- 2. 후보 표 ----------
out('== 2. 후보 표(1~6월) 다시 셈 · 대조 = RULE-0001 P2 본')
TAB = {r['판']: r for r in O['후보 표(1~6월)']}
chk('후보 표 8행 = 판 목록', sorted(TAB) == sorted(B))
SS = {b: stats(D[b], SEL) for b in B}
for b in B:
    bd = cmp({k: v for k, v in TAB[b].items() if k in SS[b]}, SS[b])
    chk(f'후보 표 {b}', not bd, bd if bd else '')
    out(f'   {b}: 합 {SS[b]["합"]:.4f} MDD {SS[b]["MDD"]:.4f} 최악 {SS[b]["최악"]:.4f} 월 {SS[b]["월 양수"]} 위5 {SS[b]["위5 몫"]:.4f} 비 {SS[b]["비"]:.4f} 거래 {SS[b]["거래 날"]} · 표의 다른 열 {sorted(set(TAB[b]) - set(SS[b]))}')
P2 = T['P2 본 날별']; CT = D['대조 P2 본']
m183 = max(abs(CT[d] - P2[d]) for d in DAYS)
com = set(CT) & set(P2); mall = max(abs(CT[d] - P2[d]) for d in com)
chk('대조 P2 본 날별 = RULE-0001 P2 본 날별(183일)', m183 <= 1e-12, f'최대 차 {m183} · 공통 {len(com)}일 최대 차 {mall}')
chk('대조 날 집합 = RULE-0001 P2 본 날 집합(187일)', set(CT) == set(P2), f'{len(CT)} vs {len(P2)}')
for b in B:
    n183 = sum(1 for d in DAYS if abs(D[b][d] - CT[d]) > 1e-12); n187 = sum(1 for d in D[b] if abs(D[b][d] - CT[d]) > 1e-12)
    out(f'   대조와 다른 날 수 {b}: 183일 {n183} · 187일 {n187}')

# ---------- 3. 고르기 ----------
out('== 3. 고르기 다시 하기')
rows = [dict(TAB[b], 판=b) for b in B]
el = [r for r in rows if r['합'] > 0 and r['최악'] >= -15 - E and r['MDD'] >= -15 - E]
for r in rows:
    if '자격' in r: chk(f'자격 표시 {r["판"]}', bool(r['자격']) == (r in el), (r['자격'], r in el))
mx = max(r['월 양수율'] for r in el); g = [r for r in el if r['월 양수율'] >= mx - E]
g5 = [r for r in g if r['위5 몫'] is not None and r['위5 몫'] <= 0.35 + E]
g2 = sorted(g5 or g, key=lambda r: (-r['비'], -r['합'], r['판']))
out(f'   자격 {[r["판"] for r in el]} · 월 최대 {mx} 무리 {len(g)} · 위5≤0.35 {len(g5)} · 순서 ' + ', '.join(f'{r["판"]}({r["비"]:.4f})' for r in g2))
chk('다시 고른 판 = 고른 판', g2[0]['판'] == O['고른 판'], (g2[0]['판'], O['고른 판']))
for r in rows:
    bf = r['합'] / max(1, abs(r['MDD']))
    if abs(bf - r['비']) > 1e-6: chk(f'비 정의 {r["판"]}', False, (r['비'], bf))
CH = D[O['고른 판']]

# ---------- 4. 결합 ----------
out('== 4. 결합 = 추세 도는 날 고른 판 · 아니면 P2R')
P2R = RV['P2R 날별']; CB = O['결합 날별']; C1d = C1['결합 날별']
cls = {'둘 다': [], '고른 판만': [], 'P2R만': [], '둘 다 아님': []}
for d in DAYS:
    eg = abs(CB[d] - CH[d]) <= 1e-12; er = abs(CB[d] - P2R[d]) <= 1e-12
    cls['둘 다' if eg and er else '고른 판만' if eg else 'P2R만' if er else '둘 다 아님'].append(d)
out('   ' + ' · '.join(f'{k} {len(v)}일' for k, v in cls.items()))
chk('모든 날 결합 ∈ {고른 판, P2R}', not cls['둘 다 아님'], cls['둘 다 아님'][:10])
# RULE-0001 날 나누기(같은 엔진 날)로 결합 재구성
tday = [d for d in DAYS if abs(C1d[d] - P2[d]) <= 1e-12 and abs(C1d[d] - P2R[d]) > 1e-12]
rday = [d for d in DAYS if abs(C1d[d] - P2R[d]) <= 1e-12 and abs(C1d[d] - P2[d]) > 1e-12]
amb = [d for d in DAYS if d not in tday and d not in rday]
out(f'   RULE-0001 결합으로 본 확실한 추세 날 {len(tday)} · P2R 날 {len(rday)} · 모호 {len(amb)}(보고 추세 도는 날 {C1["추세 도는 날 수"]})')
bad = [d for d in tday if abs(CB[d] - CH[d]) > 1e-12] + [d for d in rday if abs(CB[d] - P2R[d]) > 1e-12]
chk('확실한 날 나누기에서 결합 값 맞음', not bad, bad[:10])
dc = [d for d in DAYS if abs(CB[d] - C1d[d]) > 1e-12]
dg = [d for d in DAYS if abs(CH[d] - CT[d]) > 1e-12]
okdc = set(dc) <= set(dg) and all(abs((CB[d] - C1d[d]) - (CH[d] - CT[d])) <= 1e-9 for d in dc)
chk('RULE-0001 결합과 다른 날 = 고른 판 바뀐 날 · 차이 = 고른 판 − 대조', okdc, f'다른 날 {len(dc)} · 바뀐 날 중 결합 밖 {[d for d in dg if d not in dc]}')
for d in [d for d in dg if d not in dc]:
    out(f'   {d}: 대조 {CT[d]:+.3f} → 고른 판 {CH[d]:+.3f} · 결합 {CB[d]:+.3f}(P2R {P2R[d]:+.3f}) · 추세 날로 보이나 {d in tday}')
CTRL = {d: P2[d] + P2R[d] for d in DAYS}
m = max(abs(CTRL[d] - C1d[d]) for d in DAYS)
out(f'   참고: P2 본 + P2R 와 RULE-0001 결합 날별 최대 차 {m}')
for rk, daily, lab in (('결합 성적', CB, '결합'), ('대조 P2(T + R) 성적', CTRL, '대조 P2(T+R)')):
    for k, v in O[rk].items():
        bd = cmp(v, stats(daily, segdays(k)))
        chk(f'{lab} · {k}', not bd, bd if bd else '')
mb = stats(CB, CHK)['_달']
bd = {k: (v, mb.get(k)) for k, v in O['7~10월 달별(결합)'].items() if abs(v - mb.get(k, 1e9)) > TOL}
chk('7~10월 달별(결합)', not bd and len(mb) == len(O['7~10월 달별(결합)']), bd if bd else '')
sx, sc = stats(CB, CHK), stats(CTRL, CHK)
mp = sum(1 for mm in ['202607', '202608', '202609', '202610'] if sx['_달'].get(mm, 0) > 0)
c = {'①': mp >= 3, '②': sx['MDD'] >= -15 - E, '③': sx['최악'] >= -15 - E,
     '④': sx['위5 몫'] is not None and sx['위5 몫'] <= 0.35 + E, '⑤': sx['비'] >= sc['비'] - E}
rep = {k[0]: v for k, v in O['참고 조건'].items()}
chk('참고 조건 ①~⑤', rep == c, f'다시 셈 {c} · 위5 {sx["위5 몫"]:.4f} · 비 {sx["비"]:.4f} vs 대조 {sc["비"]:.4f}')
vd = '참고 지지' if all(c.values()) else '참고 지지 안 됨'
chk('참고 판정', O['참고 판정'] == vd, (O['참고 판정'], vd))

# ---------- 5. RESULT §2 · §4 ----------
out('== 5. RESULT §2 고른 판 vs 대조 날별')
diff = {d: CH[d] - CT[d] for d in dg}
better = [d for d in dg if diff[d] > 0]; worse = [d for d in dg if diff[d] < 0]
out(f'   다른 날 {len(dg)} · 나아짐 {len(better)} · 나빠짐 {len(worse)} · 차 합 {sum(diff.values()):+.4f} · 1~6월 {sum(diff[d] for d in dg if d in SEL):+.4f} · 7~10월 {sum(diff[d] for d in dg if d in CHK):+.4f}')
out('   ' + ' · '.join(f'{d[4:6]}-{d[6:]} {diff[d]:+.2f}' for d in dg))
REP2 = {'0520': 7.48, '0602': 6.68, '0609': -7.62, '0624': 7.66, '0701': 7.56, '0707': 5.00, '0713': -19.80, '0714': 6.80, '0729': 8.96, '0811': 0.74}
calc2 = {d[4:]: round(diff[d], 2) for d in dg}
chk('§2 날 목록 · 값(소수 2자리)', calc2 == REP2, {k: (REP2.get(k), calc2.get(k)) for k in set(REP2) | set(calc2) if REP2.get(k) != calc2.get(k)})
chk('§2 10일 · 8/2 · 합 +23.46', len(dg) == 10 and len(better) == 8 and len(worse) == 2 and round(sum(diff.values()), 2) == 23.46)
out('== 5b. RESULT §4 저변동 날')
LV = sorted(O['저변동 날'])
lvs = [d for d in LV if d in SEL]; lvc = [d for d in LV if d in CHK]; oth = [d for d in SEL if d not in set(LV)]
chk('저변동 55일 · 1~6월 17 · 모두 183일 안', len(LV) == 55 and len(lvs) == 17 and set(LV) <= set(DAYS), f'{len(LV)} · SEL {len(lvs)} · CHK {len(lvc)} · 그 밖 SEL {len(oth)}')
AUX = O['보조 · 저변동 날 성적(추세만 · 판정 아님)']
for b in B:
    for k, dd in (('저변동 1~6월', lvs), ('저변동 7~10월', lvc), ('그 밖 1~6월', oth)):
        s = stats(D[b], dd); bd = cmp(AUX[b][k], s)
        chk(f'보조 {b} · {k}', not bd, bd if bd else '')
        out(f'   {b} · {k}: 합 {s["합"]:+.3f} MDD {s["MDD"]:.3f} 거래 날 {s["거래 날"]}')
# P2R 거래가 있던 저변동 날(참고)
out(f'   참고: 대조(P2 본) 기준 저변동 거래 날 1~6월 {sum(1 for d in lvs if CT[d] != 0)} · 7~10월 {sum(1 for d in lvc if CT[d] != 0)}')

# ---------- 6. RESULT 숫자 대조 ----------
out('== 6. RESULT.md 보인 숫자 대조(보인 자리 반올림)')
def r(x, n): return round(x + 0.0, n)
T1 = {  # 판: (합, MDD, 최악, 월, 위5%, 비, 자격)
 '대조 P2 본': (574.4, -15.00, -15.00, '6/6', 37.2, 38.30, True),
 '잠금 ATR 1.5→0.3': (570.9, -15.00, -15.00, '6/6', 36.1, 38.06, True),
 '잠금 ATR 2.0→0.5': (566.1, -15.00, -15.00, '6/6', 36.8, 37.74, True),
 '잠금 ATR 3.0→1.0': (574.4, -15.00, -15.00, '6/6', 37.2, 38.30, True),
 '잠금 10p→2p(고정 참고)': (588.6, -15.00, -15.00, '6/6', 36.3, 39.24, True),
 '되밀림 1.0 ATR': (403.6, -27.84, -15.00, '6/6', 40.2, 14.50, False),
 '되밀림 1.5 ATR': (483.0, -19.56, -15.00, '6/6', 41.2, 24.70, False),
 '되밀림 2.0 ATR': (482.5, -24.70, -15.00, '6/6', 46.3, 19.53, False)}
for b, v in T1.items():
    s = SS[b]; c = (r(s['합'], 1), r(s['MDD'], 2), r(s['최악'], 2), s['월 양수'], r(100 * s['위5 몫'], 1), r(s['비'], 2), any(x['판'] == b for x in el))
    chk(f'§1 표 {b}', tuple(v) == c, '' if tuple(v) == c else (v, c))
sc6 = SS['잠금 10p→2p(고정 참고)']['합'] - SS['대조 P2 본']['합']
chk('§1/§6 1~6월 +14.2p', r(sc6, 1) == 14.2, sc6)
s3 = stats(CB, CHK); s3c = stats(CTRL, CHK); sa = stats(CB, DAYS); sac = stats(CTRL, DAYS)
chk('§3 결합 7~10월 +511.8 · MDD −15 · 위5 49.5%', (r(s3['합'], 1), r(s3['MDD'], 0), r(100 * s3['위5 몫'], 1)) == (511.8, -15, 49.5), (s3['합'], s3['MDD'], s3['위5 몫']))
chk('§3 대조 +502.58 · 47.2%', (r(s3c['합'], 2), r(100 * s3c['위5 몫'], 1)) == (502.58, 47.2), (s3c['합'], s3c['위5 몫']))
chk('§3 전체 결합 +1174.8 · 대조 +1151.3', (r(sa['합'], 1), r(sac['합'], 1)) == (1174.8, 1151.3), (sa['합'], sac['합']))
chk('§6 전체 +23.5p', r(sa['합'] - sac['합'], 1) == 23.5, sa['합'] - sac['합'])
A = lambda b, k: stats(D[b], {'저변동 1~6월': lvs, '저변동 7~10월': lvc, '그 밖 1~6월': oth}[k])
T4 = {'대조 P2 본': (10.0, 108.8, -6.39, 564.5, -15.0), '잠금 ATR 1.5→0.3': (10.0, 97.3, -6.39, 560.9, -15.0),
      '잠금 ATR 2.0→0.5': (4.3, 113.8, -6.39, 561.8, -15.0), '잠금 ATR 3.0→1.0': (10.0, 109.6, -6.39, 564.5, -15.0),
      '잠금 10p→2p(고정 참고)': (10.0, 109.6, -6.39, 578.7, -15.0)}
for b, v in T4.items():
    c = (r(A(b, '저변동 1~6월')['합'], 1), r(A(b, '저변동 7~10월')['합'], 1), r(A(b, '저변동 7~10월')['MDD'], 2), r(A(b, '그 밖 1~6월')['합'], 1), r(A(b, '그 밖 1~6월')['MDD'], 1))
    chk(f'§4 표 {b}', v == c, '' if v == c else (v, c))
chk('§4 대조 거래 날 6 · 21', (A('대조 P2 본', '저변동 1~6월')['거래 날'], A('대조 P2 본', '저변동 7~10월')['거래 날']) == (6, 21))
RB = ['되밀림 1.0 ATR', '되밀림 1.5 ATR', '되밀림 2.0 ATR']
c = tuple(r(A(b, '저변동 1~6월')['합'], 1) for b in RB)
chk('§4 되밀림 저변동 1~6월 +7.4/+8.7/+10.8', c == (7.4, 8.7, 10.8), c)
c = tuple(r(A(b, '저변동 7~10월')['합'], 1) for b in RB)
chk('§4 되밀림 저변동 7~10월 +67.7/+68.2/+79.9', c == (67.7, 68.2, 79.9), c)
c = sorted(r(A(b, '저변동 7~10월')['MDD'], 1) for b in RB)
chk('§4 되밀림 저변동 7~10월 MDD −17.0 ~ −9.6', (c[0], c[-1]) == (-17.0, -9.6), c)
c = sorted(A(b, '그 밖 1~6월')['합'] for b in RB)
chk('§4 되밀림 그 밖 1~6월 합 +396 ~ +474', (round(c[0]), round(c[-1])) == (396, 474), c)
c = sorted(r(A(b, '그 밖 1~6월')['MDD'], 1) for b in RB)
chk('§4 되밀림 그 밖 1~6월 MDD −19.6 ~ −27.8', (c[0], c[-1]) == (-27.8, -19.6), c)
SM = [15, 8, 1, 10, 101, 91, 89]
c183 = [sum(1 for d in DAYS if abs(D[b][d] - CT[d]) > 1e-12) for b in B[1:]]
c187 = [sum(1 for d in D[b] if abs(D[b][d] - CT[d]) > 1e-12) for b in B[1:]]
chk('QUESTION §4 smoke 다른 날 수(15·8·1·10·101·91·89) = 183일 또는 187일 셈', SM in (c183, c187), f'183일 {c183} · 187일 {c187}')
chk('결합 거래 날(1~6월 93 · 7~10월 61 · 전체 154)', (stats(CB, SEL)['거래 날'], s3['거래 날'], sa['거래 날']) == (93, 61, 154))

out(''); out(f'합계 PASS {npass} · FAIL {nfail}')
open(os.path.join(HERE, 'audit.out'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
