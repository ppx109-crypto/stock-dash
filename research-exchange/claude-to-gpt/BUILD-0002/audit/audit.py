# BUILD-0002 독립 감사(공개 파일만: QUESTION.md · RESULT.md · build2_out.json · ../BUILD-0001/build1_out.json)
import json, os, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
D = json.load(open(os.path.join(BASE, 'build2_out.json'), encoding='utf-8'))
D1 = json.load(open(os.path.join(BASE, '..', 'BUILD-0001', 'build1_out.json'), encoding='utf-8'))
R = {'PASS': 0, 'FAIL': 0, 'NEEDS_DATA': 0}
def rep(st, name, msg=''):
    R[st] += 1
    print(f'{st} | {name}' + (f' | {msg}' if msg else ''))
G = D['부품 거르기']; C = D['후보']; PICK = D['고른 것']; FIN = D['최종(추세 봇 + 그 밖의 봇)']; NB = D['이웃(s1.5)']

# 1. 거르기
bad = []
for k in 'TB':
    for n, g in G[k].items():
        exp = g['N'] >= 20 and g['t'] >= 2.0 and g['앞'] > 0 and g['뒤'] > 0
        if '이웃' in g:
            nb = g['이웃']
            nok = nb['N'] >= 20 and nb['t'] >= 2.0 and nb['앞'] > 0 and nb['뒤'] > 0
            if nok != nb['ok']: bad.append(f'{k}/{n} 이웃 ok')
            exp = exp and nb['ok']
        if exp != g['ok']: bad.append(f'{k}/{n} ok {g["ok"]}!={exp}')
rep('FAIL' if bad else 'PASS', '1a 거르기 ok = 규칙(N≥20 · t≥2 · 앞>0 · 뒤>0 · 이웃)', '; '.join(bad))
PASSED = {k: [n for n, g in G[k].items() if g['ok']] for k in 'TB'}
expP = {'T': {'P2T', 'VT1', 'VE', 'VT2', 'M1_s1.0', 'M12_s1.0'}, 'B': {'VR', 'P2R', 'M1_s1.0'}}
rep('PASS' if all(set(PASSED[k]) == expP[k] for k in 'TB') else 'FAIL', '1b 통과 부품', str(PASSED))
bad = []
for n, (N, t, a, b) in {'VT1': (103, 5.248, 341.8, 243.94), 'VT2': (27, 2.557, 33.32, 111.26)}.items():
    g = G['T'][n]
    if g['N'] != N or abs(g['t'] - t) > 1e-3 or abs(g['앞'] - a) > 1e-3 or abs(g['뒤'] - b) > 1e-3: bad.append(f'{n} {g}')
for n, N in (('VT1', 9), ('VT2', 1)):
    if G['B'][n]['N'] != N or G['B'][n]['ok']: bad.append(f'B/{n} {G["B"][n]}')
rep('FAIL' if bad else 'PASS', '1c VT1 · VT2 수치 = QUESTION §0', '; '.join(bad))

# 2. 판
bad = []
for k, want in (('T', 63), ('B', 7)):
    if len(C[k]) != want: bad.append(f'{k} 판 {len(C[k])}!={want}')
    order = sorted(PASSED[k], key=lambda n: (-G[k][n]['t'], n))
    allsub = {'+'.join(s) for r_ in range(1, len(order) + 1) for s in itertools.combinations(order, r_)}
    if set(C[k]) != allsub: bad.append(f'{k} 판 이름 ≠ 모든 부분집합')
    for name, v in C[k].items():
        cp = v['comps']
        if cp != sorted(cp, key=lambda n: (-G[k][n]['t'], n)) or '+'.join(cp) != name: bad.append(f'{k}/{name} 순서·이름')
    print(f'   {k} 우선순위: {order}')
rep('FAIL' if bad else 'PASS', '2 판 수(T 63 · B 7) · 부분집합 · -t 다음 이름 순', '; '.join(bad))

# 3. 지표
SEG = {'전체': lambda d: True, '1~6월': lambda d: d <= '20260630', '7~10월': lambda d: d > '20260630',
       '9~10월': lambda d: d >= '20260901', '09-21 이후': lambda d: d >= '20260921'}
def metrics(day, seg):
    ds = sorted(d for d in day if SEG[seg](d)); xs = [day[d] for d in ds]
    s = sum(xs); cum = 0; peak = 0; mdd = 0
    for x in xs:
        cum += x; peak = max(peak, cum); mdd = min(mdd, cum - peak)
    mon = {}
    for d, x in zip(ds, xs): mon[d[:6]] = mon.get(d[:6], 0) + x
    pos = sum(1 for v in mon.values() if v > 0)
    top5 = sum(sorted(xs, reverse=True)[:5])
    return {'합': s, 'MDD': mdd, '최악': min(xs) if xs else 0, '월': f'{pos}/{len(mon)}',
            '위5': (top5 / s) if s > 0 else None, '거래날': sum(1 for x in xs if x != 0)}
def cmp(a, b, tol=1e-3):
    out = []
    for f in ('합', 'MDD', '최악', '위5', '거래날'):
        x, y = a[f], b.get(f)
        if x is None or y is None:
            if not (x is None and y is None): out.append(f'{f} {x}/{y}')
        elif abs(x - y) > tol: out.append(f'{f} {x:.4f}/{y}')
    if a['월'] != b.get('월'): out.append(f'월 {a["월"]}/{b.get("월")}')
    return out
bad = []; nch = 0
for k in 'TB':
    for name, v in C[k].items():
        if len(v['날별']) != 183: bad.append(f'{k}/{name} 날 {len(v["날별"])}')
        for seg in SEG:
            nch += 1
            e = cmp(metrics(v['날별'], seg), v['real'][seg])
            if e: bad.append(f'{k}/{name}/{seg}: ' + ','.join(e))
rep('FAIL' if bad else 'PASS', '3 판별 real 지표 다시 셈(tol 1e-3)', f'{nch}칸 · ' + '; '.join(bad[:10]))

# 4. 점수
bad = []
for k, (n1, n2) in (('T', (75, 47)), ('B', (40, 21))):
    for name, v in C[k].items():
        sc = min(v['real']['1~6월']['합'] / n1, v['real']['7~10월']['합'] / n2)
        if abs(sc - v['점수']) > 1e-3: bad.append(f'{k}/{name} {sc:.4f}/{v["점수"]}')
rep('FAIL' if bad else 'PASS', '4 점수 = min(앞합/n1, 뒤합/n2) · T(75,47) · B(40,21)', '; '.join(bad[:10]))

# 5. 자격 · 고르기
bad = []; ELIG = {}
for k in 'TB':
    elig = []
    for name, v in C[k].items():
        r = v['real']; a = r['전체']
        e = (r['1~6월']['합'] > 0 and r['7~10월']['합'] > 0 and a['합'] > 0 and a['최악'] >= -15 - 1e-9
             and a['MDD'] >= -15 - 1e-9 and a['위5'] is not None and a['위5'] <= 0.35 + 1e-9)
        if e != v['자격']: bad.append(f'{k}/{name} 자격 {v["자격"]}!={e}')
        if e: elig.append(name)
    best = sorted(elig, key=lambda n: (-C[k][n]['점수'], len(C[k][n]['comps']), n))
    ELIG[k] = best
    print(f'   {k} 자격 판 {len(elig)}: ' + ', '.join(f'{n}({C[k][n]["점수"]})' for n in best))
    if (best[0] if best else None) != PICK[k]: bad.append(f'{k} 고른 것 {PICK[k]}')
if PICK != {'T': 'VT1+VE+VT2+M1_s1.0', 'B': None}: bad.append(f'고른 것 {PICK}')
if len(ELIG['T']) != 10: bad.append(f'T 자격 판 {len(ELIG["T"])}!=10')
rep('FAIL' if bad else 'PASS', '5 자격 · 고르기(T VT1+VE+VT2+M1_s1.0 · B 없음 · T 자격 10판)', '; '.join(bad))

# 6. 최종
tp = C['T'][PICK['T']]
bn = C['B'][PICK['B']]['날별'] if PICK['B'] else {}
f1 = D1['최종(추세 봇 + 그 밖의 봇)']['real_날별']
d_pick = max(abs(FIN['real_날별'][d] - tp['날별'][d] - bn.get(d, 0)) for d in tp['날별'])
d_b1 = max(abs(FIN['real_날별'][d] - f1[d]) for d in f1)
same = set(FIN['real_날별']) == set(tp['날별']) == set(f1)
bad = []
for seg in SEG: bad += [f'real/{seg}:{x}' for x in cmp(metrics(FIN['real_날별'], seg), FIN['real'][seg])]
st = 'PASS' if same and d_pick <= 1e-9 and d_b1 <= 1e-9 and not bad else 'FAIL'
rep(st, '6a 최종 real_날별 = T 고른 판 = BUILD-0001 최종', f'날 {len(f1)} · 고른 판과 최대 차 {d_pick:.3g} · BUILD-0001과 최대 차 {d_b1:.3g} · ' + '; '.join(bad))
bad = []
for seg in SEG:
    bad += [f'{seg}:{x}' for x in cmp(metrics(FIN['mtm_날별'], seg), FIN['mtm'][seg])]
    bad += [f'T판mtm/{seg}:{x}' for x in cmp(FIN['mtm'][seg], tp['mtm'][seg])]
dm = max(abs(FIN['mtm_날별'][d] - D1['최종(추세 봇 + 그 밖의 봇)']['mtm_날별'][d]) for d in f1)
rep('FAIL' if bad else 'PASS', '6b 최종 mtm = mtm_날별 = 고른 판 mtm', f'BUILD-0001 mtm_날별과 최대 차 {dm:.3g} · ' + '; '.join(bad))

# 7. 이웃 · 평가 수
n_eval = (len(C['T']) + len(C['B'])) * 2 + len(NB)
rep('PASS' if 'T' in NB and n_eval <= 142 else 'FAIL', '7 이웃(s1.5) T 있음 · 평가 수 ≤ 142',
    f'키 {list(NB)} · 이웃 전체 {NB["T"]["전체"]["합"]} · MDD {NB["T"]["전체"]["MDD"]} · 최악 {NB["T"]["전체"]["최악"]} · ({len(C["T"])}+{len(C["B"])})×2+{len(NB)} = {n_eval}')

# 8. RESULT.md 수치
bad = []
want = {'VT1': (102, 602.86), 'VE': (26, 286.88), 'VT2': (27, 144.58), 'M1_s1.0': (95, 255.64)}
for n, (N, s) in want.items():
    g = tp['부품별'].get(n)
    if not g or g[0] != N or abs(g[1] - s) > 1e-2: bad.append(f'{n} {g}')
if abs(tp['점수'] - 9.780) > 5e-4: bad.append(f'고른 판 점수 {tp["점수"]}')
rep('FAIL' if bad else 'PASS', '8a 고른 판 부품별 N · 합 · 점수 9.780', '; '.join(bad))
v = C['T']['VT1+VE+M1_s1.0']; a = v['real']['전체']
ok = abs(a['합'] - 1146.0) < 0.05 and abs(a['MDD'] + 11.5) < 0.05 and abs(a['최악'] + 9.9) < 0.05 and abs(v['점수'] - 9.336) < 5e-4 and v['자격']
rep('PASS' if ok else 'FAIL', '8b VT1+VE+M1 = 1146.0 / -11.5 / -9.9 / 9.336 · 자격 O', f'{a["합"]} / {a["MDD"]} / {a["최악"]} / {v["점수"]} / {v["자격"]}')
v = C['T']['P2T+VT1+VE+VT2+M1_s1.0']; a = v['real']['전체']
ok = abs(a['합'] - 1326.8) < 0.05 and abs(a['최악'] + 20.4) < 0.05 and not v['자격']
rep('PASS' if ok else 'FAIL', '8c P2T+VT1+VE+VT2+M1 = 1326.8 / 최악 -20.4 · 자격 X', f'{a["합"]} / {a["최악"]} / {v["자격"]}')
hi = [n for n, x in C['T'].items() if x['점수'] > tp['점수'] + 1e-12]
worst = [C['T'][n]['real']['전체']['최악'] for n in hi]
ok = (len(hi) == 12 and all(C['T'][n]['comps'][0] == 'P2T' for n in hi) and not any(C['T'][n]['자격'] for n in hi)
      and round(max(worst), 1) == -15.2 and round(min(worst), 1) == -29.3)
rep('PASS' if ok else 'FAIL', '8d 점수 더 높은 12판 모두 P2T 맨 앞 · 자격 미달 · 최악 -15.2 ~ -29.3',
    f'{len(hi)}판 · P2T 맨 앞 {sum(C["T"][n]["comps"][0] == "P2T" for n in hi)} · 자격 {sum(C["T"][n]["자격"] for n in hi)} · 최악 {min(worst):.2f} ~ {max(worst):.2f}')
exp = {'전체': 1289.96, '1~6월': 733.49, '7~10월': 556.47, '9~10월': 49.95, '09-21 이후': 14.85}
bad = [f'{s} {FIN["real"][s]["합"]}' for s, x in exp.items() if abs(FIN['real'][s]['합'] - x) > 0.006]
r = FIN['real']['전체']; m = FIN['mtm']['전체']
if abs(r['MDD'] + 11.52) > 0.006 or abs(r['최악'] + 7.18) > 0.006: bad.append('MDD/최악')
if abs(m['합'] - 1114.40) > 0.006 or abs(m['MDD'] + 20.64) > 0.006: bad.append('mtm')
nbt = NB['T']['전체']
if abs(nbt['합'] - 1299.76) > 0.006 or abs(nbt['MDD'] + 14.02) > 0.006 or abs(nbt['최악'] + 8.62) > 0.006: bad.append('이웃')
if len(ELIG['B']) != 0: bad.append('B 자격 판 있음')
rep('FAIL' if bad else 'PASS', '8e RESULT §1 이웃 · §2 B 없음 · §3 최종 5구간 · mtm', '; '.join(bad))

# 9. 비공개
for item in ('문② 표식 원천(replay.log · trade_log · v12a 코드 · 29/29 맞춤)', '비공개 build2.py 실행 · 해시',
             'tla 중재 다시 돌리기', '원천 장부(pool_ledger.json) 대조'):
    rep('NEEDS_DATA', f'9 비공개: {item}', '공개 파일만으로 확인 불가')
print(f'합계 PASS {R["PASS"]} · FAIL {R["FAIL"]} · NEEDS_DATA {R["NEEDS_DATA"]}')
