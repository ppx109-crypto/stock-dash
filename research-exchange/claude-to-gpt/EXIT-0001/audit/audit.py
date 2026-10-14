"""EXIT-0001 독립 감사(공개 파일만 사용)."""
import json, os, re
H = os.path.dirname(os.path.abspath(__file__))
D = os.path.dirname(H)
out = json.load(open(os.path.join(D, 'exit1_out.json'), encoding='utf-8'))
bld = json.load(open(os.path.join(D, '..', 'BUILD-0001', 'build1_out.json'), encoding='utf-8'))
cut = open(os.path.join(D, 'exit1_cut.txt'), encoding='utf-8').read().splitlines()
res = open(os.path.join(D, 'RESULT.md'), encoding='utf-8').read()
cnt = {'PASS': 0, 'FAIL': 0, 'NEEDS_DATA': 0}
def rep(tag, name, detail=''):
    cnt[tag] += 1
    print(f'{tag} | {name}' + (f' | {detail}' if detail else ''))
def chk(ok, name, detail=''):
    rep('PASS' if ok else 'FAIL', name, detail)

EXITS = ['N', 'L(0.3,0.1)', 'L(0.3,0.2)', 'L(0.5,0.1)', 'L(0.5,0.2)', 'T(0.2)', 'T(0.3)', 'T(0.4)',
         'TR(0.2)', 'TR(0.3)', 'TR(0.4)', 'B(15)', 'B(30)', 'BR(15)', 'BR(30)']
COMPS = ['VT', 'VE', 'M1_s1.0']
P = out['부품별']

# 1. 청산 판 목록
chk(out['청산 판'] == EXITS, '1 청산 판 15개 이름·순서', str(len(out['청산 판'])))
for c in COMPS:
    chk(c in P and sorted(P[c]) == sorted(EXITS), f'1 {c} 15판 모두 있음', str(len(P.get(c, {}))))

# 2. 자격 · 3. 점수
for c in COMPS:
    bad_e, bad_s = [], []
    for e in EXITS:
        r = P[c][e]
        a, b = r['1~6월']['합'], r['7~10월']['합']
        el = a > 0 and b > 0 and r['전체']['최악'] >= -15 - 1e-9 and r['전체']['MDD'] >= -15 - 1e-9
        if el != r['자격']: bad_e.append(e)
        sc = round(min(a / 75, b / 47), 4)
        if abs(sc - r['점수']) > 1e-3: bad_s.append((e, sc, r['점수']))
    chk(not bad_e, f'2 {c} 자격 재계산 일치', str(bad_e) if bad_e else '15/15')
    chk(not bad_s, f'3 {c} 점수 재계산 일치', str(bad_s) if bad_s else '15/15')

# 4. 고르기 규칙
def nb(e):
    m = re.match(r'L\(([\d.]+),([\d.]+)\)', e)
    if m:
        a, b = m.group(1), m.group(2)
        return [f'L({x},{b})' for x in ('0.3', '0.5') if x != a] + [f'L({a},{y})' for y in ('0.1', '0.2') if y != b]
    m = re.match(r'(TR|T)\(([\d.]+)\)', e)
    if m:
        f, k = m.group(1), m.group(2); ks = ['0.2', '0.3', '0.4']; i = ks.index(k)
        return [f'{f}({ks[j]})' for j in (i - 1, i + 1) if 0 <= j < 3]
    m = re.match(r'(BR|B)\((\d+)\)', e)
    if m:
        f, n = m.group(1), m.group(2)
        return [f'{f}({x})' for x in ('15', '30') if x != n]
    return []
for c in COMPS:
    base = P[c]['N']['점수']
    acc, notes = [], []
    for e in EXITS[1:]:
        r = P[c][e]
        if r['점수'] <= base: continue
        why = []
        if not r['자격']:
            t = r['전체']
            why.append(f"자격 미달(앞 {r['1~6월']['합']} · 뒤 {r['7~10월']['합']} · 최악 {t['최악']} · MDD {t['MDD']})")
        lo = [(n, P[c][n]['점수']) for n in nb(e) if not P[c][n]['점수'] > base]
        if lo: why.append(f'이웃 점수 <= 기준 {lo}')
        if not why: acc.append(e)
        notes.append(f"{e} {r['점수']}: " + ('채택 가능' if not why else ' / '.join(why)))
    pick = sorted(acc, key=lambda e: (-P[c][e]['점수'], e))[0] if acc else 'N'
    chk(pick == out['고른 청산'][c] == 'N', f'4 {c} 고른 청산 재현', f'기준 N {base} · 재현 {pick} · 출력 {out["고른 청산"][c]}')
    print(f'    {c} 기준보다 큰 판: ' + ('; '.join(notes) if notes else '없음'))

# 5. 조립
SEG = {'전체': lambda d: True, '1~6월': lambda d: d <= '20260630', '7~10월': lambda d: d > '20260630',
       '9~10월': lambda d: d >= '20260901', '09-21 이후': lambda d: d >= '20260921'}
def stats(days):
    v = [x for _, x in days]; s = sum(v); cum = 0; pk = 0; mdd = 0
    for x in v:
        cum += x; pk = max(pk, cum); mdd = min(mdd, cum - pk)
    mon = {}
    for d, x in days: mon[d[:6]] = mon.get(d[:6], 0) + x
    top5 = sum(sorted(v, reverse=True)[:5])
    return {'합': s, 'MDD': mdd, '최악': min(v), '월': f'{sum(1 for x in mon.values() if x > 0)}/{len(mon)}',
            '위5': (top5 / s if s > 0 else None)}
A = out['조립']
for k in ('새 추세 봇', '대조 BUILD-0001'):
    for mode in ('real', 'mtm'):
        ser = sorted(A[k][f'{mode}_날별'].items())
        bad = []
        for sg, f in SEG.items():
            got = stats([(d, x) for d, x in ser if f(d)]); want = A[k][mode][sg]
            for key in ('합', 'MDD', '최악', '위5'):
                g, w = got[key], want[key]
                if (g is None) != (w is None) or (g is not None and abs(g - w) > 1e-3): bad.append((sg, key, g, w))
            if got['월'] != want['월']: bad.append((sg, '월', got['월'], want['월']))
        chk(not bad, f'5 {k} {mode} 5구간 통계 재계산', str(bad) if bad else f'{len(ser)}일')
for mode in ('real', 'mtm'):
    x, y = A['새 추세 봇'][f'{mode}_날별'], A['대조 BUILD-0001'][f'{mode}_날별']
    md = max(abs(x[d] - y[d]) for d in x) if set(x) == set(y) else None
    chk(md is not None and md == 0, f'5 새 추세 봇 = 대조 ({mode} 날별)', f'날 수 {len(x)} · 최대 차 {md}')
bb = bld['최종(추세 봇 + 그 밖의 봇)']['real_날별']; cc = A['대조 BUILD-0001']['real_날별']
same_days = set(bb) == set(cc)
md = max(abs(bb[d] - cc[d]) for d in cc) if same_days else None
chk(same_days and md <= 1e-9, '5 대조 real 날별 = BUILD-0001 real 날별', f'날 수 {len(cc)}/{len(bb)} · 최대 차 {md}')
if 'mtm_날별' in bld['최종(추세 봇 + 그 밖의 봇)']:
    bm = bld['최종(추세 봇 + 그 밖의 봇)']['mtm_날별']; cm = A['대조 BUILD-0001']['mtm_날별']
    ok = set(bm) == set(cm); md2 = max(abs(bm[d] - cm[d]) for d in cm) if ok else None
    chk(ok and md2 <= 1e-9, '5 (덤) 대조 mtm 날별 = BUILD-0001 mtm 날별', f'최대 차 {md2}')

# 6. 자르기 기록
lines = [l for l in cut if l.strip()]
counts = [int(re.search(r'거래 수 (\d+)', l).group(1)) for l in lines if re.search(r'거래 수 (\d+)', l)]
chk(len(lines) == 5 and all(l.rstrip().endswith('같음') for l in lines), '6 자르기 5줄 모두 같음', f'건수 {counts}')
chk(counts == [30, 95, 175, 253, 271], '6 자르기 건수 = RESULT §3 (30·95·175·253·271)')
rep('NEEDS_DATA', '6 자르기 실질 검증', '고른 청산이 모두 N이라 청산 변환을 시험하지 않음(RESULT §3 명시) · 공개 파일로 재생 불가')

# 7. RESULT 숫자
def r1(x, n): return round(x, n)
spots = [
    ('VE L(0.3,0.2) 점수 1.743', r1(P['VE']['L(0.3,0.2)']['점수'], 3), 1.743),
    ('VE L(0.3,0.1) 점수 1.671', r1(P['VE']['L(0.3,0.1)']['점수'], 3), 1.671),
    ('VE L(0.5,0.2) 점수 1.668', r1(P['VE']['L(0.5,0.2)']['점수'], 3), 1.668),
    ('VE L(0.5,0.1) 점수 1.668', r1(P['VE']['L(0.5,0.1)']['점수'], 3), 1.668),
    ('VE N 점수 1.668', r1(P['VE']['N']['점수'], 3), 1.668),
    ('VT N 점수 5.015', r1(P['VT']['N']['점수'], 3), 5.015),
    ('M1 N 점수 0.646', r1(P['M1_s1.0']['N']['점수'], 3), 0.646),
    ('M1 T(0.2) 점수 0.681', r1(P['M1_s1.0']['T(0.2)']['점수'], 3), 0.681),
    ('M1 B(30) 점수 0.726', r1(P['M1_s1.0']['B(30)']['점수'], 3), 0.726),
    ('M1 TR(0.4) 점수 1.012', r1(P['M1_s1.0']['TR(0.4)']['점수'], 3), 1.012),
    ('VT TR(0.4) MDD -90.8', r1(P['VT']['TR(0.4)']['전체']['MDD'], 1), -90.8),
    ('VT TR(0.4) 최악 -28.6', r1(P['VT']['TR(0.4)']['전체']['최악'], 1), -28.6),
    ('VT T(0.2) 합 636.6', r1(P['VT']['T(0.2)']['전체']['합'], 1), 636.6),
    ('VT N 합 731.3', r1(P['VT']['N']['전체']['합'], 1), 731.3),
    ('M1 N MDD -42.7', r1(P['M1_s1.0']['N']['전체']['MDD'], 1), -42.7),
    ('조립 전체 합 1289.96', r1(A['새 추세 봇']['real']['전체']['합'], 2), 1289.96),
    ('조립 MDD -11.52', r1(A['새 추세 봇']['real']['전체']['MDD'], 2), -11.52),
    ('조립 최악 -7.18', r1(A['새 추세 봇']['real']['전체']['최악'], 2), -7.18),
    ('조립 앞 733.49', r1(A['새 추세 봇']['real']['1~6월']['합'], 2), 733.49),
    ('조립 뒤 556.47', r1(A['새 추세 봇']['real']['7~10월']['합'], 2), 556.47),
    ('조립 9~10월 49.95', r1(A['새 추세 봇']['real']['9~10월']['합'], 2), 49.95),
    ('조립 09-21 이후 14.85', r1(A['새 추세 봇']['real']['09-21 이후']['합'], 2), 14.85),
    ('mtm 전체 1114.40', r1(A['새 추세 봇']['mtm']['전체']['합'], 2), 1114.40),
    ('mtm MDD -20.64', r1(A['새 추세 봇']['mtm']['전체']['MDD'], 2), -20.64),
    ('mtm 최악 -17.50', r1(A['새 추세 봇']['mtm']['전체']['최악'], 2), -17.50),
]
for nm, g, w in spots:
    chk(abs(g - w) < 1e-9, f'7 {nm}', f'출력 {g}')
m1 = [P['M1_s1.0'][e]['전체']['MDD'] for e in ('T(0.2)', 'B(30)', 'TR(0.4)')]
chk(abs(min(m1) - (-60.4)) < 0.05 and abs(max(m1) - (-35.5)) < 0.05, '7 M1 큰 판 혼자 MDD 범위 -35.5 ~ -60.4', str(m1))
Ns = [('VT N', P['VT']['N']['N'], 129), ('VT TR(0.4)', P['VT']['TR(0.4)']['N'], 102),
      ('VE TR(0.4)', P['VE']['TR(0.4)']['N'], 20), ('M1 N', P['M1_s1.0']['N']['N'], 121), ('VE N', P['VE']['N']['N'], 26)]
for nm, g, w in Ns:
    chk(g == w, f'7 잡힌 N {nm} = {w}', f'출력 {g}')
over = [(c, e, P[c][e]['N']) for c in COMPS for e in EXITS
        if not e.startswith(('TR', 'BR')) and P[c][e]['N'] != P[c]['N']['N']]
chk(not over, '7 덧댐 판 N = 원래 N (RESULT §1)', str(over) if over else '모두 같음')

# 8. 비공개 항목
for nm in ('1분봉 청산 변환(exit1.py)', 'tla 조립 재생', '원천 장부(pool_ledger.json)', '09:45 분류 인과성'):
    rep('NEEDS_DATA', f'8 {nm}', '비공개 · 공개 파일로 확인 불가')

print(f"\n합계 PASS {cnt['PASS']} · FAIL {cnt['FAIL']} · NEEDS_DATA {cnt['NEEDS_DATA']}")
