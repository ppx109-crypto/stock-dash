# RL-FILT-0001 독립 감사(공개 파일만: QUESTION.md · RESULT.md · rl_filt1_out.json · ../BUILD-0001/build1_out.json)
import json, os, re
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(H)
D = json.load(open(os.path.join(R, 'rl_filt1_out.json')))
B = json.load(open(os.path.join(R, '..', 'BUILD-0001', 'build1_out.json')))
RES = open(os.path.join(R, 'RESULT.md')).read(); Q = open(os.path.join(R, 'QUESTION.md')).read()
cnt = {'PASS': 0, 'FAIL': 0, 'NEEDS_DATA': 0}
def out(tag, msg): cnt[tag] += 1; print(f'{tag} {msg}')
def ck(ok, msg): out('PASS' if ok else 'FAIL', msg)
TOL = 1e-3; CTRL = '대조 다 넣기'; NAMES = [CTRL, 'R λ1', 'R λ10', 'K γ0.95']
SEG = {'전체': lambda d: True, '1~6월': lambda d: d <= '20260630', '7~10월': lambda d: d > '20260630',
       '9~10월': lambda d: d >= '20260901', '09-21 이후': lambda d: d >= '20260921'}
def stats(nb, f):
    ds = sorted(k for k in nb if f(k)); v = [nb[k] for k in ds]
    s = sum(v); c = 0; mx = 0; mdd = 0
    for x in v: c += x; mx = max(mx, c); mdd = min(mdd, c - mx)
    m = {}
    for k in ds: m[k[:6]] = m.get(k[:6], 0) + nb[k]
    top5 = sum(sorted(v, reverse=True)[:5])
    return {'합': s, 'MDD': mdd, '최악': min(v) if v else None,
            '월': f"{sum(1 for x in m.values() if x > 0)}/{len(m)}", '위5': (top5 / s) if s > 0 else None}
def close(a, b): return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= TOL)

P = D['판']
# 1. 구조
for n in NAMES:
    b = P.get(n)
    ok = b is not None and all(k in b for k in ('real', 'mtm', 'real_날별', 'mtm_날별', '뺀 거래')) \
        and all(s in b[m] for m in ('real', 'mtm') for s in SEG)
    ck(ok, f'[1] 판 "{n}" 있음 · real/mtm 통계 · 날별 · 뺀 거래 있음')
ck(set(P) == set(NAMES), f'[1] 판 이름 정확히 4개: {sorted(P)}')
# 2~3. 재계산
calc = {}
for n in NAMES:
    for m in ('real', 'mtm'):
        nb = P[n][m + '_날별']; st = P[n][m]; c = {s: stats(nb, f) for s, f in SEG.items()}; calc[(n, m)] = c
        for s in SEG:
            bad = [k for k in ('합', 'MDD', '최악', '위5') if not close(c[s][k], st[s][k])]
            if c[s]['월'] != st[s]['월']: bad.append('월')
            ck(not bad, f'[2] {n} {m} {s} 통계 재계산 일치' + (f' · 다름 {bad}: 셈 {c[s]} / 저장 {st[s]}' if bad else ''))
        sc = round(min(c['1~6월']['합'] / 75, c['7~10월']['합'] / 47), 4)
        e = 1e-9; a = c['전체']
        el = c['1~6월']['합'] > e and c['7~10월']['합'] > e and a['합'] > e and a['최악'] >= -15 - e \
            and a['MDD'] >= -15 - e and a['위5'] is not None and a['위5'] <= 0.35 + e
        ck(abs(sc - st['점수']) <= 1e-9, f'[3] {n} {m} 점수 셈 {sc} / 저장 {st["점수"]}')
        ck(el == st['자격'], f'[3] {n} {m} 자격 셈 {el} / 저장 {st["자격"]}')
# 4. 고르기(real 주)
def score(n): return round(min(calc[(n, 'real')]['1~6월']['합'] / 75, calc[(n, 'real')]['7~10월']['합'] / 47), 4)
def elig(n): return P[n]['real']['자격']
cs = score(CTRL)
cand = [n for n in NAMES if n != CTRL and elig(n) and score(n) > cs]
pick = sorted(cand, key=lambda n: (-score(n), n))[0] if cand else CTRL
ck(pick == D['고른 판'] == CTRL, f'[4] 고른 판 셈 "{pick}" / 저장 "{D["고른 판"]}" (대조 점수 {cs} · 후보 {cand})')
# 5. 대조 = BUILD-0001
bn = B['최종(추세 봇 + 그 밖의 봇)']['real_날별']; cn = P[CTRL]['real_날별']
same_days = set(bn) == set(cn) and len(cn) == 183
mx = max(abs(cn[k] - bn[k]) for k in cn if k in bn)
ck(same_days and mx <= 1e-9, f'[5] 대조 real_날별 = BUILD-0001 · 날 수 {len(cn)}/{len(bn)} · 날짜 같음 {same_days} · 최대 차 {mx:.3g}')
# 6. 뺀 거래
ck(all(v == 0 for v in P[CTRL]['뺀 거래'].values()), f'[6] 대조 뺀 거래 모두 0: {P[CTRL]["뺀 거래"]}')
exp = {'R λ1': (8, 0, 10), 'R λ10': (6, 0, 2), 'K γ0.95': (3, 0, 16)}
rows = {}
for line in RES.splitlines():
    cells = [x.strip().strip('*') for x in line.strip().strip('|').split('|')]
    if len(cells) >= 12 and cells[0] in NAMES: rows[cells[0]] = cells
for n, e3 in exp.items():
    g = P[n]['뺀 거래']; got = (g['VT'], g['VE'], g['M1_s1.0'])
    ck(got == e3, f'[6] {n} 뺀 거래 {got} = QUESTION smoke {e3}')
    rt = tuple(int(x) for x in re.findall(r'\d+', rows[n][1])) if n in rows else None
    ck(rt == got, f'[6] {n} 뺀 거래 RESULT 표 {rt} = 출력 {got}')
sm = re.search(r'R λ1 VT 8 · VE 0 · M1 10 / R λ10 6 · 0 · 2 / K γ0.95 3 · 0 · 16', Q)
ck(sm is not None, '[6] QUESTION.md에 smoke 숫자 문구 있음')
# 7. RESULT 표
def num(s): s = s.replace('−', '-').replace('+', '').replace('%', ''); return float(re.findall(r'-?\d+\.?\d*', s)[0])
ck(set(rows) == set(NAMES), f'[7] RESULT 표에 판 4줄 있음: {sorted(rows)}')
for n in NAMES:
    if n not in rows: continue
    r = rows[n]; c = calc[(n, 'real')]; st = P[n]['real']
    bad = []
    if ('O' if st['자격'] else 'X') != r[2][0]: bad.append('자격')
    if abs(num(r[3]) - round(score(n), 3)) > 5e-4: bad.append('점수')
    for i, (s, k) in enumerate([('전체', '합'), ('전체', 'MDD'), ('전체', '최악')]):
        if abs(num(r[4 + i]) - round(c[s][k], 1)) > 0.051: bad.append(f'{s}{k}')
    if abs(num(r[7]) - round(c['전체']['위5'] * 100, 1)) > 0.051: bad.append('위5')
    for i, s in enumerate(['1~6월', '7~10월', '9~10월', '09-21 이후']):
        if abs(num(r[8 + i]) - round(c[s]['합'], 1)) > 0.051: bad.append(s)
    if not st['자격']:
        mm = re.findall(r'-?\d+\.\d', r[2].replace('−', '-'))
        if [float(x) for x in mm] != [round(c['전체']['MDD'], 1), round(c['전체']['최악'], 1)]: bad.append('자격 사유')
    ck(not bad, f'[7] RESULT 표 "{n}" 숫자 일치' + (f' · 다름 {bad}' if bad else ''))
c7 = round(calc[(CTRL, 'real')]['7~10월']['합'], 1)
ck(c7 == 556.5 and all(round(calc[(n, 'real')]['7~10월']['합'], 1) == 556.5 for n in ('R λ1', 'R λ10')),
   f'[7] R 학습기 7~10월 합 = 대조 556.5 (대조 {c7} · λ1 {calc[("R λ1","real")]["7~10월"]["합"]:.4f} · λ10 {calc[("R λ10","real")]["7~10월"]["합"]:.4f})')
k9 = calc[('K γ0.95', 'real')]['09-21 이후']['합']
ck(round(k9, 1) == 23.7, f'[7] K 09-21 이후 합 {k9:.4f} ≈ 23.7')
cm = calc[(CTRL, 'mtm')]['전체']
ck(round(cm['합'], 1) == 1114.4 and round(cm['MDD'], 1) == -20.6, f'[7] mtm 대조 +1114.4 / −20.6 (셈 {cm["합"]:.2f} / {cm["MDD"]:.2f})')
lm = [calc[(n, 'mtm')]['전체'] for n in NAMES[1:]]
ck(round(min(x['합'] for x in lm), 1) == 1026.5 and round(max(x['합'] for x in lm), 1) == 1088.9
   and round(max(x['MDD'] for x in lm), 1) == -20.6 and round(min(x['MDD'] for x in lm), 1) == -25.5,
   f'[7] mtm 학습기 범위 +1026.5~+1088.9 / −20.6~−25.5 (셈 {[round(x["합"],1) for x in lm]} / {[round(x["MDD"],1) for x in lm]})')
# 8. 공개 자료로 확인 못 함
for t in ['학습기 인과성(엄격히 앞 거래만 배움) — rl_filt1.py 비공개',
          '맥락 가용 시각(진입 분에 앎) — rl_exit1.ctx 비공개',
          '비공개 구현(rl_filt1 / judge / exit1) 내용 · 해시 대조',
          'tla 조립 재생(VT > VE > M1 prio · stop) — tla.py 비공개',
          '원천 장부(pool_ledger.json · exit1 거래 목록) 대조']:
    out('NEEDS_DATA', '[8] ' + t)
print(f"요약 PASS {cnt['PASS']} · FAIL {cnt['FAIL']} · NEEDS_DATA {cnt['NEEDS_DATA']}")
