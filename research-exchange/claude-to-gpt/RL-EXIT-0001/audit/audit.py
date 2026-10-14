# RL-EXIT-0001 독립 감사 (공개 파일만 사용)
import json, os, re
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(H)
d = json.load(open(os.path.join(B, 'rl_exit1_out.json')))
bld = json.load(open(os.path.join(B, '..', 'BUILD-0001', 'build1_out.json')))['최종(추세 봇 + 그 밖의 봇)']
res = open(os.path.join(B, 'RESULT.md')).read()
out = []; P = lambda s, ok, m='': out.append(f"{'PASS' if ok else 'FAIL'} {s} {m}".rstrip())
TOL = 1e-3
BOARDS = ['대조 N', 'D γ0.9', 'D γ0.95', 'D γ0.98', 'R λ1', 'R λ10']
SEG = {'전체': lambda k: True, '1~6월': lambda k: k <= '20260630', '7~10월': lambda k: k > '20260630',
       '9~10월': lambda k: k >= '20260901', '09-21 이후': lambda k: k >= '20260921'}
# 1
for b in BOARDS:
    x = d['판'].get(b)
    ok = x is not None and all(k in x for k in ['real', 'mtm', 'real_날별', 'mtm_날별', '고른 팔 수'])
    P(f'1 판존재 {b}', ok)
P('1 판 수 6', set(d['판']) == set(BOARDS), str(sorted(d['판'])))

def stats(dd):
    ks = sorted(dd); v = [dd[k] for k in ks]
    s = sum(v); c = 0; m = 0; mdd = 0
    for a in v:
        c += a; m = max(m, c); mdd = min(mdd, c - m)
    mon = {}
    for k, a in zip(ks, v): mon[k[:6]] = mon.get(k[:6], 0) + a
    pos = sum(1 for a in mon.values() if a > 0)
    top5 = sum(sorted(v, reverse=True)[:5])
    return {'합': s, 'MDD': mdd, '최악': min(v) if v else 0, '월': f'{pos}/{len(mon)}', '위5': (top5 / s if s > 0 else None)}

def close(a, b):
    if a is None or b is None: return a is None and b is None
    if isinstance(a, str): return a == b
    return abs(a - b) <= TOL

rec = {}
for b in BOARDS:
    for st in ['real', 'mtm']:
        dd = d['판'][b][f'{st}_날별']; R = {}
        for sg, f in SEG.items():
            sub = {k: v for k, v in dd.items() if f(k)}
            R[sg] = stats(sub)
            stored = d['판'][b][st][sg]
            bad = [f'{k}:{R[sg][k]} vs {stored.get(k)}' for k in ['합', 'MDD', '최악', '월', '위5'] if not close(R[sg][k], stored.get(k))]
            P(f'2 {b} {st} {sg}', not bad, '; '.join(bad))
        # 3
        sc = round(min(R['1~6월']['합'] / 75, R['7~10월']['합'] / 47), 4)
        e = R['전체']; w5 = e['위5']
        el = (R['1~6월']['합'] > 0 and R['7~10월']['합'] > 0 and e['합'] > 0 and e['최악'] >= -15 - 1e-9
              and e['MDD'] >= -15 - 1e-9 and w5 is not None and w5 <= 0.35 + 1e-9)
        P(f'3 {b} {st} 점수', abs(sc - d['판'][b][st]['점수']) <= 1e-4, f"{sc} vs {d['판'][b][st]['점수']}")
        P(f'3 {b} {st} 자격', el == d['판'][b][st]['자격'], f"{el} vs {d['판'][b][st]['자격']}")
        rec[(b, st)] = (R, sc, el)
# 4
cs = rec[('대조 N', 'real')][1]
cand = [(sc, b) for b in BOARDS[1:] for (R, sc, el) in [rec[(b, 'real')]] if el and sc > cs]
pick = sorted(cand, key=lambda t: (-t[0], t[1]))[0][1] if cand else '대조 N'
P('4 고른 판', pick == d['고른 판'], f'재계산 {pick} · 저장 {d["고른 판"]} · 후보 {cand}')
# 5
for st in ['real', 'mtm']:
    a = d['판']['대조 N'][f'{st}_날별']; bb = bld[f'{st}_날별']
    ks = set(a) | set(bb); miss = [k for k in ks if k not in a or k not in bb]
    md = max((abs(a[k] - bb[k]) for k in ks if k in a and k in bb), default=0)
    P(f'5 대조 {st}_날별 = BUILD-0001', not miss and md <= 1e-9, f'날 {len(ks)} · 빠진 날 {len(miss)} · 최대 차 {md}')
# 6
NEED = {'VT': 130, 'VE': 26, 'M1_s1.0': 121}
for b in BOARDS:
    g = d['판'][b]['고른 팔 수']
    ok = set(g) == set(NEED) and all(sum(g[c].values()) == n for c, n in NEED.items())
    ok = ok and all(a in d['팔'] for c in g for a in g[c])
    P(f'6 {b} 팔 수 합', ok, str({c: sum(g[c].values()) for c in g}))
P('6 대조 모두 N', all(d['판']['대조 N']['고른 팔 수'][c] == {'N': n} for c, n in NEED.items()))
# 7 표
def num(t): return float(t.replace('−', '-').replace('+', '').replace('*', '').replace('%', '').strip())
rows = {}
for ln in res.splitlines():
    m = re.match(r'\|\s*\**([^|*]+?)\**\s*\|', ln)
    if m and m.group(1).strip() in BOARDS:
        rows[m.group(1).strip()] = [c.strip() for c in ln.strip('|').split('|')]
for b in BOARDS:
    if b not in rows: P(f'7 표 {b}', False, '행 없음'); continue
    c = rows[b]; R, sc, el = rec[(b, 'real')]
    exp = [('자격', ('O' if el else 'X'), c[1][0]), ('점수', round(sc, 3), num(c[2])),
           ('전체 합', round(R['전체']['합'], 1), num(c[3])), ('MDD', round(R['전체']['MDD'], 1), num(c[4])),
           ('최악', round(R['전체']['최악'], 1), num(c[5])), ('위5', round(R['전체']['위5'] * 100, 1), num(c[6])),
           ('앞', round(R['1~6월']['합'], 1), num(c[7])), ('뒤', round(R['7~10월']['합'], 1), num(c[8])),
           ('9~10월', round(R['9~10월']['합'], 1), num(c[9])), ('09-21 이후', round(R['09-21 이후']['합'], 1), num(c[10]))]
    bad = [f'{n}:{e}≠{g}' for n, e, g in exp if (e != g if isinstance(e, str) else abs(e - g) > 0.051)]
    # X 이유
    if not el:
        why = []
        if R['전체']['MDD'] < -15: why.append('MDD')
        if R['전체']['최악'] < -15: why.append('최악')
        got = re.findall(r'MDD|최악', c[1])
        if why != got: bad.append(f'X이유 {why}≠{got}')
    P(f'7 표 {b}', not bad, '; '.join(bad))
# mtm 줄
mr = rec[('대조 N', 'mtm')][0]['전체']
lm = [rec[(b, 'mtm')][0]['전체'] for b in BOARDS[1:]]
P('7 mtm 대조', round(mr['합'], 1) == 1114.4 and round(mr['MDD'], 1) == -20.6, f"{mr['합']:.2f}/{mr['MDD']:.2f}")
P('7 mtm 학습기 범위', round(min(x['합'] for x in lm), 1) == 1000.6 and round(max(x['합'] for x in lm), 1) == 1049.8
  and round(max(x['MDD'] for x in lm), 1) == -19.8 and round(min(x['MDD'] for x in lm), 1) == -24.1,
  f"합 {min(x['합'] for x in lm):.2f}~{max(x['합'] for x in lm):.2f} · MDD {max(x['MDD'] for x in lm):.2f}~{min(x['MDD'] for x in lm):.2f}")
# 7 §2 팔 수 (본문 인용)
Q = [('D γ0.9', 'VT', 'T(0.4,)', 75), ('D γ0.9', 'VT', 'N', 24), ('D γ0.9', 'VT', 'T(0.2,)', 12),
     ('D γ0.9', 'VE', 'N', 14), ('D γ0.9', 'VE', 'L(0.3, 0.1)', 8), ('D γ0.9', 'VE', 'L(0.3, 0.2)', 4),
     ('D γ0.9', 'M1_s1.0', 'N', 73), ('D γ0.9', 'M1_s1.0', 'B(30,)', 38), ('D γ0.9', 'M1_s1.0', 'B(15,)', 9), ('D γ0.9', 'M1_s1.0', 'T(0.2,)', 1),
     ('D γ0.95', 'VT', 'L(0.3, 0.2)', 52), ('D γ0.95', 'VT', 'T(0.4,)', 46), ('D γ0.95', 'VT', 'N', 24),
     ('D γ0.95', 'M1_s1.0', 'N', 92), ('D γ0.95', 'M1_s1.0', 'B(30,)', 24), ('D γ0.95', 'M1_s1.0', 'B(15,)', 5),
     ('D γ0.98', 'VT', 'N', 74), ('D γ0.98', 'VT', 'L(0.3, 0.2)', 53), ('D γ0.98', 'VT', 'B(15,)', 3),
     ('D γ0.98', 'M1_s1.0', 'N', 110), ('D γ0.98', 'M1_s1.0', 'B(30,)', 7), ('D γ0.98', 'M1_s1.0', 'B(15,)', 4),
     ('R λ1', 'VT', 'N', 45), ('R λ10', 'VT', 'N', 46), ('R λ1', 'VT', 'L(0.3, 0.2)', 46), ('R λ10', 'VT', 'L(0.3, 0.2)', 47),
     ('R λ1', 'M1_s1.0', 'N', 43), ('R λ10', 'M1_s1.0', 'N', 54), ('R λ1', 'M1_s1.0', 'T(0.3,)', 27), ('R λ10', 'M1_s1.0', 'T(0.3,)', 24)]
bad = [f'{b}/{c}/{a}: 글 {n} · 출력 {d["판"][b]["고른 팔 수"][c].get(a, 0)}' for b, c, a, n in Q if d['판'][b]['고른 팔 수'][c].get(a, 0) != n]
P('7 §2 팔 수 인용 30개', not bad, '; '.join(bad))
# 'VE 같음' (D γ0.95 · 0.98 VE = D γ0.9 VE)
for b in ['D γ0.95', 'D γ0.98']:
    P(f'7 §2 {b} VE 같음', d['판'][b]['고른 팔 수']['VE'] == d['판']['D γ0.9']['고른 팔 수']['VE'],
      f"{d['판'][b]['고른 팔 수']['VE']} vs {d['판']['D γ0.9']['고른 팔 수']['VE']}")
# 순서(상위) 인용 맞는지: D γ0.9 VT 1위 T(0.4)
def top(b, c): g = d['판'][b]['고른 팔 수'][c]; return sorted(g.items(), key=lambda t: -t[1])
P('7 §2 D γ0.9 VT 상위 3', [a for a, _ in top('D γ0.9', 'VT')[:3]] == ['T(0.4,)', 'N', 'T(0.2,)'], str(top('D γ0.9', 'VT')[:4]))
# 8
for s in ['학습기 인과성 · 배우는 때(비공개 rl_exit1.py)', '청산 변환 apply(비공개 exit1.py)', 'tla 조립 재생(tla.py)', '원천 장부 · 분봉 출처(pool_ledger.json)']:
    out.append(f'NEEDS_DATA 8 {s}')
n = {k: sum(1 for l in out if l.startswith(k)) for k in ['PASS', 'FAIL', 'NEEDS_DATA']}
out.append(f"합계 PASS {n['PASS']} · FAIL {n['FAIL']} · NEEDS_DATA {n['NEEDS_DATA']}")
open(os.path.join(H, 'audit.out'), 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
