# SPLIT-0001 공개 출력 감사(split1_out.json만 읽음 · 비공개 코드 안 읽음)
import json, os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, '..', 'split1_out.json'), encoding='utf-8'))
BOARDS = ['대조 v12a', '대조 P2', 'S1 나누기', 'S2 나누기+P2T 채우기', 'S3 P2T 우선']
SEGS = {'고르기 1~6월': ('20260101', '20260630'), '참고 7~10월': ('20260701', '20261031'),
        '9~10월': ('20260901', '99999999'), '09-21 이후': ('20260921', '99999999'), '전체': ('00000000', '99999999')}
TOL = 1e-6
cnt = defaultdict(int)
def out(st, name, detail=''):
    cnt[st] += 1
    print(f'{st} {name}' + (f' :: {detail}' if detail else ''))

def metrics(days):
    ks = sorted(days)
    v = [days[k] for k in ks]
    s = sum(v)
    cum = 0.0; peak = 0.0; mdd = 0.0
    for x in v:
        cum += x; peak = max(peak, cum); mdd = min(mdd, cum - peak)
    mon = defaultdict(float)
    for k in ks: mon[k[:6]] += days[k]
    pos = sum(1 for m in mon.values() if m > 0)
    top5 = sum(sorted(v, reverse=True)[:5])
    return {'합': s, 'MDD': mdd, '최악': min(v) if v else 0.0,
            '월 양수율': pos / len(mon) if mon else 0.0, '월 양수': f'{pos}/{len(mon)}',
            '위5 몫': (top5 / s) if s != 0 else None, '비': s / max(1.0, abs(mdd)),
            '거래 날': sum(1 for x in v if x != 0)}, dict(mon)

def seg(days, a, b): return {k: x for k, x in days.items() if a <= k <= b}

def cmp(a, b):
    if isinstance(a, str) or isinstance(b, str) or a is None or b is None: return a == b
    if isinstance(a, bool) or isinstance(b, bool): return a == b
    return abs(a - b) <= TOL

REAL, MTM = D['판별 날별'], D['판별 날별(mtm)']
calc = {}
for tag, src, key in (('real', REAL, '판별 구간 성적(stop real)'), ('mtm', MTM, '판별 구간 성적(stop mtm · 보조)')):
    rep = D[key]
    for b in BOARDS:
        days = src.get(b)
        if days is None: out('FAIL', f'[{tag}] {b} 날별 있음'); continue
        ks = sorted(days)
        ok = len(ks) == 183 and ks[0] == '20260108' and ks[-1] == '20261012'
        out('PASS' if ok else 'FAIL', f'[{tag}] {b} 183일 · 20260108~20261012', f'n={len(ks)} {ks[0]}~{ks[-1]}')
        for sn, (a, z) in SEGS.items():
            m, mon = metrics(seg(days, a, z))
            calc[(tag, b, sn)] = (m, mon)
            r = rep.get(b, {}).get(sn)
            if r is None: out('FAIL', f'[{tag}] {b} {sn} 보고 없음'); continue
            bad = [f'{f}: 셈 {m.get(f)} / 보고 {r.get(f)}' for f in m if not cmp(m[f], r.get(f))]
            extra = [f for f in r if f not in m]
            if extra: bad.append(f'보고에만 있는 칸 {extra}')
            out('PASS' if not bad else 'FAIL', f'[{tag}] {b} {sn} 지표 일치', '; '.join(bad))

# 고르기 다시 하기(real · 1~6월)
SN = '고르기 1~6월'
rows = {b: calc[('real', b, SN)][0] for b in BOARDS}
elig = {b: (m['합'] > 0 and m['최악'] >= -15 - 1e-9 and m['MDD'] >= -15 - 1e-9) for b, m in rows.items()}
g = [b for b in BOARDS if elig[b]]
pick = None
if g:
    mx = max(rows[b]['월 양수율'] for b in g)
    g = [b for b in g if rows[b]['월 양수율'] == mx]
    g5 = [b for b in g if rows[b]['위5 몫'] is not None and rows[b]['위5 몫'] <= 0.35]
    if g5: g = g5
    g.sort(key=lambda b: (-rows[b]['비'], -rows[b]['합'], b))
    pick = g[0]
print(f'INFO 다시 고른 순서: {g} · 자격 {elig}')
out('PASS' if pick == D['고른 판'] else 'FAIL', '고른 판 일치', f'셈 {pick} / 보고 {D["고른 판"]}')
tab = {r['판']: r for r in D['후보 표(1~6월)']}
out('PASS' if set(tab) == set(BOARDS) else 'FAIL', '후보 표 판 목록', str(list(tab)))
for b in BOARDS:
    r = tab.get(b)
    if r is None: continue
    m = dict(rows[b]); m['자격'] = elig[b]
    bad = [f'{f}: 셈 {m.get(f)} / 보고 {r.get(f)}' for f in r if f != '판' and not cmp(m.get(f), r.get(f))]
    out('PASS' if not bad else 'FAIL', f'후보 표 {b}', '; '.join(bad))

# 참고 조건(고른 판 vs 대조 P2 · 7~10월 · real)
P = D['고른 판']
pm, pmon = calc[('real', P, '참고 7~10월')]
cm, _ = calc[('real', '대조 P2', '참고 7~10월')]
npos = sum(1 for x in pmon.values() if x > 0)
cond = {'① 4달 중 양수 ≥ 3': npos >= 3 and len(pmon) == 4,
        '② MDD ≥ −15': pm['MDD'] >= -15 - 1e-9,
        '③ 최악 ≥ −15': pm['최악'] >= -15 - 1e-9,
        '④ 위5 ≤ 35%': pm['위5 몫'] is not None and pm['위5 몫'] <= 0.35,
        '⑤ 비 ≥ 대조 P2': pm['비'] >= cm['비']}
print(f'INFO 참고 셈: 달 {len(pmon)} 양수 {npos} · MDD {pm["MDD"]:.4f} · 최악 {pm["최악"]:.4f} · 위5 {pm["위5 몫"]:.4f} · 비 {pm["비"]:.4f} vs 대조 P2 비 {cm["비"]:.4f}')
rc = D['참고 조건']
for k, v in cond.items():
    out('PASS' if rc.get(k) == v else 'FAIL', f'참고 조건 {k}', f'셈 {v} / 보고 {rc.get(k)}')
out('PASS' if set(rc) == set(cond) else 'FAIL', '참고 조건 항목 목록', str(list(rc)))
verdict = '참고 지지' if all(cond.values()) else '참고 지지 안 됨'
out('PASS' if verdict == D['참고 판정'] else 'FAIL', '참고 판정', f'셈 {verdict} / 보고 {D["참고 판정"]}')
rm = D['7~10월 달별(고른 판)']
bad = [f'{k}: 셈 {pmon.get(k)} / 보고 {rm.get(k)}' for k in set(pmon) | set(rm) if not cmp(pmon.get(k), rm.get(k))]
out('PASS' if not bad else 'FAIL', '7~10월 달별(고른 판)', '; '.join(bad))

# mtm vs real 날 차이
for b in BOARDS:
    diff = sorted(k for k in REAL[b] if k not in MTM[b] or abs(REAL[b][k] - MTM[b][k]) > TOL)
    print(f'INFO mtm≠real {b}: {len(diff)}일 ' + ', '.join(f'{k}(real {REAL[b][k]:.4f} / mtm {MTM[b].get(k, float("nan")):.4f})' for k in diff))
    d910 = [k for k in diff if k >= '20260901']
    print(f'INFO(보고만) {b} 9~10월 mtm = real: {"같음" if not d910 else "다름 " + str(d910)}')

# 비공개 코드가 있어야 하는 것
for n in ('거래 단위 겹침 처리(tla) 재현', '인과성 · 미래 참조(kmf_guard · 자르기)', '원본 v12a 다시 돌리기(C1 vs 장부 05-21 0.98 차 포함)'):
    out('NEEDS_DATA', n, '비공개 코드 · 장부 필요 · 공개 출력만으로 확인 불가')
print(f'SUMMARY PASS={cnt["PASS"]} FAIL={cnt["FAIL"]} NEEDS_DATA={cnt["NEEDS_DATA"]}')
