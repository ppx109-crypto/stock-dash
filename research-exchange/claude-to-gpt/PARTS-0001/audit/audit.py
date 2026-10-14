# PARTS-0001 독립 감사 — 공개 파일만 읽음(QUESTION.md · RESULT.md · parts1_out.json · ../BUILD-0001/build1_out.json)
import json, os, re, hashlib, itertools
from collections import defaultdict
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(H, 'parts1_out.json')))
B1 = json.load(open(os.path.join(H, '..', 'BUILD-0001', 'build1_out.json')))
RES = open(os.path.join(H, 'RESULT.md'), encoding='utf-8').read()
CNT = defaultdict(int)
def out(tag, msg):
    CNT[tag] += 1; print(f'{tag} {msg}')
def chk(c, msg): out('PASS' if c else 'FAIL', msg)

# 0. 출력 해시(보고 값과)
h = hashlib.sha256(open(os.path.join(H, 'parts1_out.json'), 'rb').read()).hexdigest()
chk(h in RES and h.startswith('0cdb6bb2'), f'0 parts1_out.json sha256 {h} 보고와 같음')

# 1. 부품 거르기
G = P['부품 거르기']
def gate(r):
    ok = r['N'] >= 20 and r['t'] >= 2 and r['앞'] > 0 and r['뒤'] > 0
    if '이웃' in r:
        nb = r['이웃']; nok = nb['N'] >= 20 and nb['t'] >= 2 and nb['앞'] > 0 and nb['뒤'] > 0
        if nok != nb['ok']: out('FAIL', f'1 이웃 ok 불일치 {r}')
        ok = ok and nok
    return ok
EXP = {'T': ['VT1', 'P2T-e', 'P2T-b', 'VE', 'P2T-p', 'VT2', 'M1_s1.0', 'M12_s1.0'], 'B': ['VR', 'P2R', 'M1_s1.0']}
PRIO = {}
for s in 'TB':
    bad = [k for k, r in G[s].items() if gate(r) != r['ok']]
    chk(not bad, f'1 {s} ok = 규칙 재계산({len(G[s])}부품) 불일치 {bad}')
    passed = [k for k, r in G[s].items() if r['ok']]
    prio = sorted(passed, key=lambda k: (-G[s][k]['t'], k))
    chk(set(passed) == set(EXP[s]) and prio == EXP[s], f'1 {s} 통과 {prio}')
    PRIO[s] = prio
p0 = G['T'].get('P2T-0')
chk(p0 is not None and p0['N'] < 20 and not p0['ok'], f'1 T P2T-0 N={p0 and p0["N"]} 탈락')

# 2. 판 집합
C = P['후보']
for s, n in (('T', 255), ('B', 7)):
    exp = ['+'.join(c) for r in range(1, len(PRIO[s]) + 1) for c in itertools.combinations(PRIO[s], r)]
    chk(len(C[s]) == n and set(C[s]) == set(exp), f'2 {s} 판 {len(C[s])}개 = 통과 부품의 빈 것 아닌 모든 부분집합')
    bad = [k for k, v in C[s].items() if '+'.join(v['comps']) != k or v['comps'] != sorted(v['comps'], key=PRIO[s].index)]
    chk(not bad, f'2 {s} 판 안 부품 순서 = (-t, 이름) 우선순위 · 이름 = comps 이음 (어긋남 {len(bad)})')
    out('PASS' if list(C[s]) == exp else 'FAIL', f'2 {s} 판 나열 순서 = 크기별 combinations(우선순위) 순')

# 3. 지표 재계산
SEGS = {'전체': lambda d: True, '1~6월': lambda d: d <= '20260630', '7~10월': lambda d: d > '20260630',
        '9~10월': lambda d: d >= '20260901', '09-21 이후': lambda d: d >= '20260921'}
def metrics(nb, seg):
    ds = sorted(d for d in nb if SEGS[seg](d)); xs = [nb[d] for d in ds]
    S = sum(xs); cum = 0; mx = 0; mdd = 0
    for x in xs:
        cum += x; mx = max(mx, cum); mdd = min(mdd, cum - mx)
    mo = defaultdict(float)
    for d in ds: mo[d[:6]] += nb[d]
    ms = list(mo.values())
    return {'합': S, 'MDD': mdd, '최악': min(xs), '월': f'{sum(1 for m in ms if m > 0)}/{len(ms)}',
            '최악달': min(ms), '위2달': (sum(sorted(ms, reverse=True)[:2]) / S if S > 0 else None),
            '위5': (sum(sorted(xs, reverse=True)[:5]) / S if S > 0 else None), '거래날': sum(1 for x in xs if x != 0)}, mo
def close(a, b):
    if a is None or b is None: return a is None and b is None
    if isinstance(a, str): return a == b
    return abs(a - b) <= 1e-3 or any(abs(a - round(b, k)) <= 1e-9 for k in (2, 4))  # 저장 값이 2 · 4자리 반올림이면 허용
def cmp_block(stored, nb, tag):
    bad = []
    for seg in SEGS:
        m, _ = metrics(nb, seg)
        for k, v in m.items():
            if k not in stored.get(seg, {}): bad.append((seg, k, 'missing')); continue
            if not close(stored[seg][k], v): bad.append((seg, k, stored[seg][k], v))
    return bad
REC = {}
for s in 'TB':
    allbad = {}
    for k, v in C[s].items():
        b = cmp_block(v['real'], v['날별'], k)
        if b: allbad[k] = b[:3]
        REC[(s, k)] = {seg: metrics(v['날별'], seg)[0] for seg in SEGS}
    chk(not allbad, f'3 {s} {len(C[s])}판 × 5구간 × 8지표 real 재계산 일치 (어긋난 판 {len(allbad)}: {list(allbad.items())[:3]})')

# 4. 자격 · 고르기
E = 1e-9
def elig(r): return r['1~6월']['합'] > E and r['7~10월']['합'] > E and r['전체']['최악'] >= -15 - E and r['전체']['MDD'] >= -15 - E
def key(s, k, r):
    a = r['전체']; return (-(a['최악달'] // 5), -(a['MDD'] // 2), -(a['거래날'] // 5), -a['합'], len(C[s][k]['comps']), k)
EL = {}
for s, ne, pick in (('T', 50, 'P2T-e+P2T-b+P2T-p+VT2'), ('B', 3, 'VR')):
    bad = [k for k, v in C[s].items() if elig(REC[(s, k)]) != v['자격']]
    chk(not bad, f'4 {s} 자격 재계산 = 저장 자격 (어긋남 {bad[:5]})')
    el = [k for k in C[s] if elig(REC[(s, k)])]; EL[s] = el
    chk(len(el) == ne, f'4 {s} 자격 판 수 {len(el)} (기대 {ne})')
    rk = sorted(el, key=lambda k: key(s, k, REC[(s, k)]))
    rk2 = sorted([k for k in C[s] if C[s][k]['자격']], key=lambda k: key(s, k, C[s][k]['real']))
    chk(rk[0] == P['고른 것'][s] == pick == rk2[0], f'4 {s} 고른 판 재계산 {rk[0]} · 저장 값 순위 {rk2[0]} · 출력 {P["고른 것"][s]}')
    print(f'INFO 4 {s} 상위 3: {rk[:3]}')

# 5. 최종
F = P['최종']; tn = C['T'][P['고른 것']['T']]['날별']; bn = C['B'][P['고른 것']['B']]['날별']
chk(set(F['real_날별']) == set(tn) == set(bn) and all(abs(F['real_날별'][d] - tn[d] - bn[d]) <= 1e-9 for d in tn),
    f'5 최종 real_날별 = T 판 + B 판 ({len(tn)}일)')
ov = [d for d in tn if tn[d] != 0 and bn[d] != 0]
chk(not ov, f'5 T · B 판 거래 날 겹침 {len(ov)}일')
chk(not cmp_block(F['real'], F['real_날별'], 'F'), f'5 최종 real 5구간 지표 재계산 일치 {cmp_block(F["real"], F["real_날별"], "F")[:3]}')
_, mo = metrics(F['real_날별'], '전체')
chk(set(mo) == set(F['real_달별']) and all(abs(mo[m] - F['real_달별'][m]) <= 0.005 + E for m in mo), f'5 최종 달별 재계산 일치')
chk(not cmp_block(F['mtm'], F['mtm_날별'], 'M'), '5 최종 mtm 지표 = mtm_날별 재계산')
fm = F['real']['전체']; mm = F['mtm']['전체']
chk(abs(fm['합'] - mm['합']) < 1e-6 and abs(fm['MDD'] - mm['MDD']) < 1e-6, f'5 mtm 합 · MDD 같음(보고 "같음") real {fm["합"]:.2f}/{fm["MDD"]} mtm {mm["합"]:.2f}/{mm["MDD"]}')
# RESULT §3 최종 표 · 달별 줄
fin = {'전체': (1116.32, -15.00, -15.00, '10/10', 14.18, .542, .277, 122), '1~6월': (606.09, -15.00, -15.00, '6/6', 14.18, None, None, 70),
       '7~10월': (510.22, -13.41, -8.72, '4/4', 14.51, None, None, 52), '9~10월': (37.03, -13.41, -6.32, '2/2', None, None, None, 15),
       '09-21 이후': (14.65, -13.41, -6.32, '2/2', None, None, None, 7)}
bad = []
for seg, t in fin.items():
    m, _ = metrics(F['real_날별'], seg)
    for i, k in enumerate(['합', 'MDD', '최악', '월', '최악달', '위2달', '위5', '거래날']):
        if t[i] is None: continue
        tol = 0.0005 + E if k in ('위2달', '위5') else 0.005 + E
        if (m[k] != t[i]) if isinstance(t[i], str) else abs(m[k] - t[i]) > tol: bad.append((seg, k, t[i], m[k]))
chk(not bad, f'5 RESULT §3 최종 표 = 재계산 {bad}')
monline = re.search(r'달별: (.*)', RES).group(1)
vals = [float(x.replace('−', '-')) for x in re.findall(r'월 ([+−-]\d+(?:\.\d+)?)', monline)]
chk(len(vals) == 10 and all(abs(a - round(b, 1)) <= 0.05 + E for a, b in zip(vals, [mo[m] for m in sorted(mo)])), f'5 RESULT 달별 줄 = 재계산 {vals}')

# 6. 파레토
T = C['T']; A = {k: REC[('T', k)]['전체'] for k in EL['T']}
f4 = lambda k: (A[k]['최악달'], A[k]['MDD'], A[k]['거래날'], A[k]['합'])
dom = lambda a, b: all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))
par = [k for k in EL['T'] if not any(dom(f4(j), f4(k)) for j in EL['T'] if j != k)]
chk(len(par) == 13, f'6 T 파레토 {len(par)}판 (기대 13)')
sec3 = RES.split('### 추세 날 파레토')[1].split('\n- (')[0]
NM = {'M1': 'M1_s1.0', 'M12': 'M12_s1.0'}
rows = []
for ln in sec3.splitlines():
    if not ln.startswith('| ') or '---' in ln or '추세 날 판' in ln: continue
    c = [x.strip() for x in ln.strip('|').split('|')]
    name = re.sub(r'\(.*\)', '', c[0]).strip()
    comps = [NM.get(x.strip(), x.strip()) for x in name.split('+')]
    num = lambda x: float(x.replace('−', '-').replace('+', '').replace('%', ''))
    rows.append(('+'.join(comps), [num(x) for x in c[1:]]))
chk(len(rows) == 10, f'6 RESULT 파레토 표 줄 {len(rows)} (10줄 + 줄인 3판)')
bad = []; inpar = []
for k, v in rows:
    if k not in T: bad.append((k, 'no board')); continue
    inpar.append(k)
    a = REC[('T', k)]
    calc = [a['전체']['합'], a['전체']['MDD'], a['전체']['최악'], a['전체']['최악달'], a['전체']['거래날'], a['전체']['위2달'] * 100, a['9~10월']['합'], a['09-21 이후']['합']]
    for i, (x, y) in enumerate(zip(v, calc)):
        tol = 0.5 + E if i in (4, 5) else 0.05 + E
        if abs(x - y) > tol: bad.append((k, i, x, round(y, 3)))
chk(not bad, f'6 파레토 표 숫자 = 재계산 (어긋남 {bad})')
chk(set(inpar) <= set(par), f'6 표 판이 모두 파레토 안 (밖: {set(inpar) - set(par)})')
rest = [k for k in par if k not in inpar]
pairs = []
for k in rest:
    base = '+'.join(c for c in T[k]['comps'] if c != 'M12_s1.0')
    same = base in inpar and 'M12_s1.0' in T[k]['comps'] and T[k]['날별'] == T[base]['날별']
    pairs.append((base, k, same))
chk(len(rest) == 3 and all(p[2] for p in pairs), f'6 줄인 3판 = 표 판 + M12 · 날별 완전히 같음 {[(p[1], p[2]) for p in pairs]}')

# 7. 사실(§4 고친 판 · §1)
both = [k for k in T if {'VT1', 'P2T-b'} <= set(T[k]['comps'])]
be = [k for k in both if k in EL['T']]
wa = [REC[('T', k)]['전체']['최악'] for k in both]; we = [REC[('T', k)]['전체']['최악'] for k in be]
print(f'INFO 7 VT1+P2T-b 든 판 {len(both)} · 자격 {len(be)} · 최악 하루(전체 {len(both)}판) {min(wa):.2f} ~ {max(wa):.2f} · (자격 {len(be)}판) {min(we):.2f} ~ {max(we):.2f}')
chk(len(both) == 64 and len(be) == 8, f'7 VT1+P2T-b 든 판 64 · 자격 8 (재계산 {len(both)} · {len(be)})')
chk(abs(min(wa) + 20.08) <= 0.005 and abs(max(wa) + 9.12) <= 0.005, f'7 보고 최악 하루 범위 −20.08 ~ −9.12 = 64판 전체 범위 {min(wa):.2f} ~ {max(wa):.2f}')
out('FAIL' if be else 'PASS', f'7 옛 문구 "둘 다 든 판은 자격 없음 · 모두 최악 하루 −15 미만" — 자격 {len(be)}판 · −15 이상 {sum(1 for x in wa if x >= -15)}판 → 옛 문구 {"틀림(고친 문구가 맞음)" if be else "맞음"}')
chk(not [k for k in par if k in both], f'7 파레토 13판 중 VT1+P2T-b 함께 든 판 0 ({[k for k in par if k in both]})')
ep = [k for k in EL['T'] if {'VT1', 'P2T-e'} <= set(T[k]['comps']) and 'P2T-b' not in T[k]['comps']]
we2 = [REC[('T', k)]['전체']['최악'] for k in ep]
chk(len(ep) == 24 and min(we2) >= -9.30 - 0.005 and abs(min(we2) + 9.30) <= 0.005 and abs(max(we2) + 5.72) <= 0.005,
    f'7 VT1+P2T-e(P2T-b 없이) 자격 {len(ep)}판 · 최악 하루 {min(we2):.4f} ~ {max(we2):.4f} (보고 24 · −9.30 ~ −5.72)')
pk = T[P['고른 것']['T']]['부품별']; bk = C['B']['VR']['부품별']
exp = {'P2T-b': [115, 397.63], 'P2T-e': [79, 348.81], 'P2T-p': [53, 303.86], 'VT2': [7, -22.14]}
chk(pk == exp, f'7 고른 T 판 부품별 {pk}')
chk(bk == {'VR': [24, 88.16]}, f'7 고른 B 판 부품별 {bk}')
chk(abs(sum(v[1] for v in pk.values()) - REC[('T', P['고른 것']['T'])]['전체']['합']) <= 0.02, '7 고른 T 판 부품별 합 = 날별 합')
a = REC[('T', P['고른 것']['T'])]['전체']
chk(abs(a['최악달'] - 14.18) < .005 and a['MDD'] >= -15 - E and abs(a['MDD'] + 15) < .005 and abs(a['최악'] + 15) < .005 and a['거래날'] == 112
    and abs(a['합'] - 1028.16) < .005 and abs(a['위2달'] - .5557) < .0005 and abs(a['위5'] - .301) < .0005, f'7 §1 고른 판 숫자(+14.2 · −15.0 · −15.0 · 112 · +1028.2 · 56% · 30.1%)')
bb = {k: REC[('B', k)]['전체'] for k in ('VR', 'VR+P2R', 'P2R')}
chk(set(EL['B']) == set(bb) and abs(bb['VR']['합'] - 88.16) < .005 and abs(bb['VR+P2R']['합'] - 268.1) < .05 and abs(bb['P2R']['합'] - 176.3) < .05
    and abs(bb['VR+P2R']['MDD'] + 14.6) < .05 and bb['VR+P2R']['거래날'] == 46 and bb['P2R']['거래날'] == 45 and bb['VR']['거래날'] == 10,
    f'7 §2 막힌 날 자격 3판 숫자 {[(k, round(v["합"], 2), round(v["MDD"], 2), round(v["최악달"], 2), v["거래날"]) for k, v in bb.items()]}')
# 타당성 경계: 고른 판 MDD가 −15 경계에 정확히 닿음
print(f'INFO 7 고른 T 판 MDD 원값 {a["MDD"]!r} · 최악 원값 {a["최악"]!r} (경계 −15, 허용 1e-9)')

# 8. BUILD-0001 비교
bn1 = B1['최종(추세 봇 + 그 밖의 봇)']['real_날별']
m1, mo1 = metrics(bn1, '전체')
chk(abs(m1['합'] - 1289.96) < .005 and abs(m1['MDD'] + 11.52) < .005 and abs(m1['최악달'] + 6.35) < .005 and m1['월'] == '9/10' and abs(m1['위2달'] - .602) < .0005,
    f'8 BUILD-0001 합 {m1["합"]:.2f} · MDD {m1["MDD"]:.2f} · 최악달 {m1["최악달"]:.2f} · {m1["월"]} · 위2달 {m1["위2달"]:.4f}')
chk(abs(B1['최종(추세 봇 + 그 밖의 봇)']['real']['전체']['합'] - m1['합']) < 1e-3, '8 BUILD-0001 저장 합 = 날별 재계산')
chk(set(bn1) == set(F['real_날별']), f'8 같은 183일 비교 ({len(bn1)}일)')

# 9. 공개 파일로 못 보는 것
for x in ['부품 표식 원천(replay.log · 엔진 TR2 진입 종류)', '비공개 parts1.py 재실행', 'tla 재생(중재 · stop)', '원천 장부(pool_ledger 등)']:
    out('NEEDS_DATA', f'9 {x}')
print('COUNT', dict(CNT))
