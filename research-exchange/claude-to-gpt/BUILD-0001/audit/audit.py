# BUILD-0001 독립 감사(공개 파일만: QUESTION.md · build1_out.json)
import json, os, re, itertools, math
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
D = json.load(open(os.path.join(BASE, 'build1_out.json'), encoding='utf-8'))
Q = open(os.path.join(BASE, 'QUESTION.md'), encoding='utf-8').read()
R = {'PASS': 0, 'FAIL': 0, 'NEEDS_DATA': 0}
def rep(st, name, msg=''):
    R[st] += 1
    print(f'{st} | {name}' + (f' | {msg}' if msg else ''))

G = D['부품 거르기']; C = D['후보']; PICK = D['고른 것']; FIN = D['최종(추세 봇 + 그 밖의 봇)']

# 1. 거르기 표
bad = []
for k in 'TB':
    for n, g in G[k].items():
        exp = g['N'] >= 20 and g['t'] >= 2.0 and g['앞'] > 0 and g['뒤'] > 0
        if '이웃' in g:
            nb = g['이웃']
            nok = nb['N'] >= 20 and nb['t'] >= 2.0 and nb['앞'] > 0 and nb['뒤'] > 0
            if nok != nb['ok']: bad.append(f'{k}/{n} 이웃 ok {nb["ok"]} != {nok}')
            exp = exp and nb['ok']
        if exp != g['ok']: bad.append(f'{k}/{n} ok {g["ok"]} != {exp}')
rep('FAIL' if bad else 'PASS', '1a 거르기 ok = 규칙', '; '.join(bad))

rows = {}
for line in Q.splitlines():
    m = re.match(r'\|\s*([TB])\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([−\-]?[\d.]+)\s*\|\s*([−\-]?[\d.]+)\s*\|\s*([−\-]?[\d.]+)\s*\|\s*([^|]+?)\s*\|', line)
    if m:
        f = lambda s: float(s.replace('−', '-'))
        key = m.group(2).replace(' ', '_')
        rows[(m.group(1), key)] = (int(m.group(3)), f(m.group(4)), f(m.group(5)), f(m.group(6)), m.group(7).startswith('통과'))
bad = []
for k in 'TB':
    for n, g in G[k].items():
        r = rows.get((k, n))
        if r is None: bad.append(f'{k}/{n} 표에 없음'); continue
        N, t, a, b, ok = r
        if N != g['N']: bad.append(f'{k}/{n} N {N}!={g["N"]}')
        if abs(round(g['t'], 2) - t) > 0.0051: bad.append(f'{k}/{n} t {t}!={g["t"]}')
        if abs(a - g['앞']) > 0.051: bad.append(f'{k}/{n} 앞 {a}!={g["앞"]}')
        if abs(b - g['뒤']) > 0.051: bad.append(f'{k}/{n} 뒤 {b}!={g["뒤"]}')
        if ok != g['ok']: bad.append(f'{k}/{n} 결과 {ok}!={g["ok"]}')
extra = [x for x in rows if x[1] not in G[x[0]]]
if extra: bad.append(f'표에만 있음 {extra}')
rep('FAIL' if bad else 'PASS', '1b 거르기 값 = QUESTION §1-보완 표', f'표 {len(rows)}줄 · ' + '; '.join(bad))
PASSED = {k: [n for n, g in G[k].items() if g['ok']] for k in 'TB'}
expP = {'T': {'VT', 'P2T', 'VE', 'M1_s1.0', 'M12_s1.0'}, 'B': {'VR', 'P2R', 'M1_s1.0'}}
ok = all(set(PASSED[k]) == expP[k] for k in 'TB')
rep('PASS' if ok else 'FAIL', '1c 통과 부품', str(PASSED))

# 2. 판 수 · 부품 순서
bad = []
for k, want in (('T', 31), ('B', 7)):
    if len(C[k]) != want: bad.append(f'{k} 판 {len(C[k])}!={want}')
    order = sorted(PASSED[k], key=lambda n: (-G[k][n]['t'], n))
    allsub = set()
    for r_ in range(1, len(order) + 1):
        for s in itertools.combinations(order, r_): allsub.add('+'.join(s))
    if set(C[k]) != allsub: bad.append(f'{k} 판 이름이 모든 부분집합과 다름')
    for name, v in C[k].items():
        cp = v['comps']
        if not cp or not set(cp) <= set(PASSED[k]): bad.append(f'{k}/{name} comps 범위')
        if cp != sorted(cp, key=lambda n: (-G[k][n]['t'], n)): bad.append(f'{k}/{name} 순서')
        if '+'.join(cp) != name: bad.append(f'{k}/{name} 이름≠comps')
rep('FAIL' if bad else 'PASS', '2 판 수(T 31 · B 7) · 부분집합 · t 순서', '; '.join(bad))

# 3. 지표
SEG = {'전체': lambda d: True, '1~6월': lambda d: d <= '20260630', '7~10월': lambda d: d > '20260630',
       '9~10월': lambda d: d >= '20260901', '09-21 이후': lambda d: d >= '20260921'}
def metrics(day, seg, month_mode='present'):
    ds = sorted(d for d in day if SEG[seg](d)); xs = [day[d] for d in ds]
    s = sum(xs); cum = 0; peak = 0; mdd = 0
    for x in xs:
        cum += x; peak = max(peak, cum); mdd = min(mdd, cum - peak)
    mon = {}
    for d, x in zip(ds, xs):
        if month_mode == 'traded' and x == 0: continue
        mon[d[:6]] = mon.get(d[:6], 0) + x
    pos = sum(1 for v in mon.values() if v > 0)
    top5 = sum(sorted(xs, reverse=True)[:5])
    return {'합': s, 'MDD': mdd, '최악': min(xs) if xs else 0, '월': f'{pos}/{len(mon)}',
            '위5': (top5 / s) if s > 0 else None, '거래날': sum(1 for x in xs if x != 0)}
def cmp(a, b, tol=1e-3):
    out = []
    for f in ('합', 'MDD', '최악', '위5', '거래날'):
        x, y = a[f], b.get(f)
        if x is None or y is None:
            if x is not y and not (x is None and y is None): out.append(f'{f} {x}/{y}')
        elif abs(x - y) > tol: out.append(f'{f} {x:.4f}/{y}')
    if a['월'] != b.get('월'): out.append(f'월 {a["월"]}/{b.get("월")}')
    return out
bad = []; nch = 0; mmode_bad = {'present': 0, 'traded': 0}
for k in 'TB':
    for name, v in C[k].items():
        if len(v['날별']) != 183: bad.append(f'{k}/{name} 날 {len(v["날별"])}')
        for seg in SEG:
            nch += 1
            for mm in mmode_bad:
                if metrics(v['날별'], seg, mm)['월'] != v['real'][seg]['월']: mmode_bad[mm] += 1
            e = cmp(metrics(v['날별'], seg), v['real'][seg])
            if e: bad.append(f'{k}/{name}/{seg}: ' + ','.join(e))
rep('FAIL' if bad else 'PASS', '3 판별 real 지표 다시 셈', f'{nch}칸 · 월 세는 법(달력 달) 불일치 {mmode_bad["present"]} · (거래 있는 달) 불일치 {mmode_bad["traded"]} · ' + '; '.join(bad[:10]))

# 4. 날 종류
nz = {k: set() for k in 'TB'}; bad = []
for k in 'TB':
    for v in C[k].values(): nz[k] |= {d for d, x in v['날별'].items() if x != 0}
ov = nz['T'] & nz['B']
rep('FAIL' if ov else 'PASS', '4a 추세 · 막힌 날 거래 날 안 겹침', f'관측 거래 날 T {len(nz["T"])} · B {len(nz["B"])} · 겹침 {len(ov)}')
rep('NEEDS_DATA', '4b 날 종류 T 122일 · B 61일 주장', f'공개 출력에 날 종류 목록 없음 · 관측(거래 있는 날 합집합)만 T {len(nz["T"])} · B {len(nz["B"])}')
NZH = {k: (sum(1 for d in nz[k] if d <= '20260630'), sum(1 for d in nz[k] if d > '20260630')) for k in 'TB'}

# 5. 점수 분모 역산
infer = {}
for k in 'TB':
    pairs = []
    for n1 in range(1, 184):
        for n2 in range(1, 184):
            if all(abs(min(v['real']['1~6월']['합'] / n1, v['real']['7~10월']['합'] / n2) - v['점수']) <= 1e-3 for v in C[k].values()):
                pairs.append((n1, n2))
    infer[k] = pairs
    st = 'PASS' if len(pairs) == 1 else ('FAIL' if not pairs else 'NEEDS_DATA')
    tot = {'T': 122, 'B': 61}[k]
    sumfit = [p_ for p_ in pairs if sum(p_) == tot]
    rep(st, f'5 점수 분모 {k}', f'맞는 (n1,n2) {len(pairs)}개 {pairs[:5]}{" …" if len(pairs) > 5 else ""} · 이 중 n1+n2={tot}(주장)인 쌍 {sumfit} · n2 범위 {min(b for a, b in pairs) if pairs else None}~{max(b for a, b in pairs) if pairs else None} · 관측 거래날 반별 {NZH[k]}')

# 6. 자격 · 고르기
bad = []
for k in 'TB':
    elig = []
    for name, v in C[k].items():
        r = v['real']; a = r['전체']
        e = (r['1~6월']['합'] > 0 and r['7~10월']['합'] > 0 and a['합'] > 0 and a['최악'] >= -15 - 1e-9
             and a['MDD'] >= -15 - 1e-9 and a['위5'] is not None and a['위5'] <= 0.35)
        if e != v['자격']: bad.append(f'{k}/{name} 자격 {v["자격"]}!={e}')
        if e: elig.append(name)
    best = sorted(elig, key=lambda n: (-C[k][n]['점수'], len(C[k][n]['comps']), n))
    got = best[0] if best else None
    print(f'   {k} 자격 판 {len(elig)}: ' + ', '.join(f'{n}({C[k][n]["점수"]})' for n in best))
    if got != PICK[k]: bad.append(f'{k} 고른 것 {PICK[k]}!={got}')
exp = {'T': 'VT+VE+M1_s1.0', 'B': None}
if PICK != exp: bad.append(f'고른 것 {PICK} != 기대 {exp}')
rep('FAIL' if bad else 'PASS', '6 자격 · 고르기(T VT+VE+M1_s1.0 · B 없음)', '; '.join(bad))

# 7. 최종
bad = []
tp = C['T'][PICK['T']]
bn = C['B'][PICK['B']]['날별'] if PICK['B'] else {}
for d in tp['날별']:
    want = tp['날별'][d] + bn.get(d, 0)
    if abs(FIN['real_날별'].get(d, 1e9) - want) > 1e-9: bad.append(f'{d}')
if set(FIN['real_날별']) != set(tp['날별']): bad.append('날 목록 다름')
for seg in SEG:
    e = cmp(metrics(FIN['real_날별'], seg), FIN['real'][seg]); bad += [f'real/{seg}:{x}' for x in e]
rep('FAIL' if bad else 'PASS', '7a 최종 real = T 고른 판 + B 0 · 지표 다시 셈', '; '.join(bad[:10]))
bad = []
for seg in SEG:
    e = cmp(metrics(FIN['mtm_날별'], seg), FIN['mtm'][seg]); bad += [f'{seg}:{x}' for x in e]
rep('FAIL' if bad else 'PASS', '7b 최종 mtm 지표 = mtm_날별', '; '.join(bad))
bad = []
for seg in SEG:
    e = cmp(FIN['mtm'][seg], tp['mtm'][seg]); bad += [f'{seg}:{x}' for x in e]
rep('FAIL' if bad else 'PASS', '7c 최종 mtm = T 고른 판 저장 mtm', '; '.join(bad))

# 8. 이웃
nb = D['이웃(s1.5)']
if 'T' in nb:
    a = nb['T']['전체']; f = FIN['real']['전체']
    rep('PASS', '8 이웃(s1.5) T 있음(보고만)', f'전체 합 {a["합"]} (s1.0 {f["합"]}) · MDD {a["MDD"]} · 최악 {a["최악"]} · 1~6월 {nb["T"]["1~6월"]["합"]} · 7~10월 {nb["T"]["7~10월"]["합"]} · 09-21 이후 {nb["T"]["09-21 이후"]["합"]} · 키 {list(nb)}')
else:
    rep('FAIL', '8 이웃(s1.5) T 없음')

# 9. 평가 수
n_eval = (len(C['T']) + len(C['B'])) * 2 + len(nb)
rep('PASS' if n_eval <= 78 else 'FAIL', '9 평가 수 ≤ 78', f'{len(C["T"]) + len(C["B"])}판 × 2 + 이웃 {len(nb)} = {n_eval}')

# 10. 비공개
for item in ('tla 중재 다시 돌리기', '09:45 전 진입 빼기', '원천 장부(pool_ledger.json) 대조', '인과(미래 참조 없음)'):
    rep('NEEDS_DATA', f'10 비공개: {item}', '공개 파일만으로 확인 불가')
print(f'합계 PASS {R["PASS"]} · FAIL {R["FAIL"]} · NEEDS_DATA {R["NEEDS_DATA"]}')
