# FILT-0001 독립 감사(공개 파일만: QUESTION.md · RESULT.md · filt1_out.json · ../BUILD-0001/build1_out.json)
import json, os, re
H = os.path.dirname(os.path.abspath(__file__))
B = os.path.dirname(H)
d = json.load(open(os.path.join(B, 'filt1_out.json'), encoding='utf-8'))
bld = json.load(open(os.path.join(B, '..', 'BUILD-0001', 'build1_out.json'), encoding='utf-8'))
R = open(os.path.join(B, 'RESULT.md'), encoding='utf-8').read()
cnt = {'PASS': 0, 'FAIL': 0, 'NEEDS_DATA': 0}
def out(tag, name, msg=''):
    cnt[tag] += 1
    print(f'{tag} {name}' + (f' :: {msg}' if msg else ''))

FL = ['N', 'HV(1.2)', 'HV(1.4)', 'LV(0.8)', 'LV(0.7)', 'LATE(780)', 'LATE(840)', 'GA(0.2)', 'GA(0.4)']
CS = ['VT', 'VE', 'M1_s1.0']
P = d['부품별']
# 1
out('PASS' if d['필터 판'] == FL else 'FAIL', '1 필터 목록', str(d['필터 판']))
for c in CS:
    ks = list(P.get(c, {}).keys())
    out('PASS' if ks == FL else 'FAIL', f'1 {c} 9판', str(ks))
# 2
bad_q, bad_s = [], []
for c in CS:
    for f in FL:
        v = P[c][f]
        a, b = v['1~6월']['합'], v['7~10월']['합']
        q = (a > 1e-9) and (b > 1e-9) and (v['전체']['최악'] >= -15 - 1e-9) and (v['전체']['MDD'] >= -15 - 1e-9)
        if q != v['자격']: bad_q.append((c, f, v['자격'], q))
        s = round(min(a / 75, b / 47), 4)
        if abs(s - v['점수']) > 1e-9: bad_s.append((c, f, v['점수'], s))
out('PASS' if not bad_q else 'FAIL', '2 자격 재계산(27판)', str(bad_q) if bad_q else '27/27 일치')
out('PASS' if not bad_s else 'FAIL', '2 점수 재계산(27판)', str(bad_s) if bad_s else '27/27 일치')
# 3
NB = {'HV(1.2)': 'HV(1.4)', 'HV(1.4)': 'HV(1.2)', 'LV(0.8)': 'LV(0.7)', 'LV(0.7)': 'LV(0.8)',
      'LATE(780)': 'LATE(840)', 'LATE(840)': 'LATE(780)', 'GA(0.2)': 'GA(0.4)', 'GA(0.4)': 'GA(0.2)'}
for c in CS:
    sN = P[c]['N']['점수']
    ok = [f for f in FL[1:] if P[c][f]['자격'] and P[c][f]['점수'] > sN and P[c][NB[f]]['점수'] > sN]
    pick = sorted(ok, key=lambda f: (-P[c][f]['점수'], f))[0] if ok else 'N'
    out('PASS' if pick == d['고른 필터'][c] == 'N' else 'FAIL', f'3 {c} 고른 필터', f'재계산 {pick} · 출력 {d["고른 필터"][c]} · N 점수 {sN}')
    above = [f for f in FL[1:] if P[c][f]['점수'] > sN]
    eq = [f for f in FL[1:] if P[c][f]['점수'] == sN]
    why = []
    for f in above:
        r = []
        if not P[c][f]['자격']:
            v = P[c][f]
            r.append(f"자격 X(MDD {v['전체']['MDD']} · 최악 {v['전체']['최악']} · 앞 {v['1~6월']['합']} · 뒤 {v['7~10월']['합']})")
        if not P[c][NB[f]]['점수'] > sN: r.append(f'이웃 {NB[f]} 점수 {P[c][NB[f]]["점수"]} ≤ N')
        why.append(f"{f}({P[c][f]['점수']}): " + (' · '.join(r) if r else '탈락 사유 없음'))
    print(f'   INFO {c} N보다 점수 큰 후보: ' + ('; '.join(why) if why else '없음') + (f' | N과 같은 점수(크지 않음): {eq}' if eq else ''))
# 4
TR = {'VT': 130, 'VE': 26, 'M1_s1.0': 121}
NN = {'VT': 129, 'VE': 26, 'M1_s1.0': 121}
for c in CS:
    v = P[c]['N']
    out('PASS' if v['잡힌 N'] == NN[c] and v['뺀 거래'] == 0 else 'FAIL', f'4 {c} N 잡힌', f"뺀 {v['뺀 거래']} · 잡힌 {v['잡힌 N']}")
    rows, bad = [], []
    for f in FL[1:]:
        e, k = P[c][f]['뺀 거래'], P[c][f]['잡힌 N']
        rows.append(f'{f} {e}+{k}={e+k}')
        if e + k > TR[c]: bad.append(f)
    out('PASS' if not bad else 'FAIL', f'4 {c} 뺀+잡힌 ≤ {TR[c]}', ' · '.join(rows))
for f in ['LATE(780)', 'LATE(840)']:
    v = P['M1_s1.0'][f]
    out('PASS' if v['뺀 거래'] == 121 and v['잡힌 N'] == 0 else 'FAIL', f'4 M1 {f}', f"뺀 {v['뺀 거래']} · 잡힌 {v['잡힌 N']}")
# 5
SEG = {'전체': lambda k: True, '1~6월': lambda k: k <= '20260630', '7~10월': lambda k: k > '20260630',
       '9~10월': lambda k: k >= '20260901', '09-21 이후': lambda k: k >= '20260921'}
def stats(dd):
    ks = sorted(dd); xs = [dd[k] for k in ks]
    s = sum(xs); cum = 0.0; mx = 0.0; mdd = 0.0
    for x in xs:
        cum += x; mx = max(mx, cum); mdd = min(mdd, cum - mx)
    mo = {}
    for k in ks: mo[k[:6]] = mo.get(k[:6], 0.0) + dd[k]
    pos = sum(1 for m in mo.values() if m > 0)
    t5 = sum(sorted(xs, reverse=True)[:5])
    w5 = (t5 / s) if s > 0 else None
    return {'합': s, 'MDD': mdd, '최악': min(xs) if xs else 0.0, '월': f'{pos}/{len(mo)}', '위5': w5}
def cmp(a, b):
    errs = []
    for k in ['합', 'MDD', '최악', '위5']:
        x, y = a[k], b[k]
        if x is None or y is None:
            if x is not y: errs.append(f'{k} {x} vs {y}')
        elif abs(x - y) > 1e-3: errs.append(f'{k} 재계산 {round(x,4)} vs 출력 {y}')
    if a['월'] != b['월']: errs.append(f"월 {a['월']} vs {b['월']}")
    return errs
A = d['조립']
for bot in ['새 추세 봇', '대조 BUILD-0001']:
    for mode in ['real', 'mtm']:
        dd = A[bot][mode + '_날별']
        for sg, fn in SEG.items():
            sub = {k: v for k, v in dd.items() if fn(k)}
            e = cmp(stats(sub), A[bot][mode][sg])
            out('PASS' if not e else 'FAIL', f'5 {bot} {mode} {sg}', '; '.join(e) if e else f'{len(sub)}일 일치')
for mode in ['real', 'mtm']:
    a, b = A['새 추세 봇'][mode + '_날별'], A['대조 BUILD-0001'][mode + '_날별']
    md = max(abs(a[k] - b[k]) for k in a) if set(a) == set(b) else None
    out('PASS' if md is not None and md == 0 else 'FAIL', f'5 새 봇 = 대조 {mode} 날별', f'날 수 {len(a)}/{len(b)} · 최대 차 {md}')
bx = bld['최종(추세 봇 + 그 밖의 봇)']
for mode in ['real', 'mtm']:
    a, b = A['대조 BUILD-0001'][mode + '_날별'], bx.get(mode + '_날별', {})
    md = max(abs(a[k] - b[k]) for k in a) if set(a) == set(b) else None
    tag = 'PASS' if md is not None and md == 0 else 'FAIL'
    if mode == 'mtm': tag = 'PASS' if md is not None and md <= 1e-9 else 'FAIL'
    out(tag, f'5 대조 = BUILD-0001 {mode}_날별', f'날 수 {len(a)}/{len(b)} · 최대 차 {md}')
# 6 RESULT.md 표 숫자
def r1(x): return f'{x:.1f}'
def r3(x): return f'{x:.3f}'
def num(s): return float(s.replace('−', '-'))
claims = []  # (설명, 표시값 문자열, 출력값, 자리)
def C(desc, shown, val, nd): claims.append((desc, shown, val, nd))
V = lambda c, f: P[c][f]
for c, f, sc, tot, mdd, a, b, s9 in [
    ('VT', 'N', '5.015', '731.3', '−12.1', '376.1', '355.2', '51.5'),
    ('VE', 'N', '1.668', '286.9', '−7.5', '125.1', '161.8', '0.0'),
    ('M1_s1.0', 'N', '0.646', '223.7', '−42.7', '193.3', '30.4', '−4.4')]:
    v = V(c, f); C(f'{c} {f} 점수', sc, v['점수'], 3); C(f'{c} {f} 합', tot, v['전체']['합'], 1)
    C(f'{c} {f} MDD', mdd, v['전체']['MDD'], 1); C(f'{c} {f} 앞', a, v['1~6월']['합'], 1)
    C(f'{c} {f} 뒤', b, v['7~10월']['합'], 1); C(f'{c} {f} 9~10월', s9, v['9~10월']['합'], 1)
for c, pair, ex, sc, tot, a, b, s9 in [
    ('VT', ('HV(1.2)', 'HV(1.4)'), ('73', '57', '64', '66'), ('0.855', '1.917'), ('264.6', '348.3'), ('64.1', '143.8'), ('200.4', '204.6'), ('51.5', '51.5')),
    ('VT', ('LV(0.8)', 'LV(0.7)'), ('25', '104', '25', '104'), ('4.891', '4.891'), ('639.9', '639.9'), ('366.9', '366.9'), ('273.0', '273.0'), ('0.0', '0.0')),
    ('VT', ('LATE(780)', 'LATE(840)'), ('36', '93', '20', '109'), ('4.322', '4.389'), ('595.6', '628.1'), ('324.2', '329.2'), ('271.4', '298.9'), ('33.0', '34.8')),
    ('VT', ('GA(0.2)', 'GA(0.4)'), ('31', '98', '24', '105'), ('3.739', '3.909'), ('566.8', '603.2'), ('280.4', '293.1'), ('286.4', '310.1'), ('32.3', '51.5')),
    ('M1_s1.0', ('LV(0.8)', 'LV(0.7)'), ('27', '94', '24', '97'), ('0.941', '0.941'), ('233.4', '233.8'), ('189.2', '189.6'), ('44.2', '44.2'), ('0.0', '0.0')),
    ('M1_s1.0', ('GA(0.2)', 'GA(0.4)'), ('3', '118', '2', '119'), ('0.734', '0.734'), ('212.6', '223.7'), ('178.2', '189.2'), ('34.5', '34.5'), ('−0.3', '−0.3'))]:
    for i, f in enumerate(pair):
        v = V(c, f)
        C(f'{c} {f} 뺀', ex[2*i], v['뺀 거래'], 0); C(f'{c} {f} 잡힌', ex[2*i+1], v['잡힌 N'], 0)
        C(f'{c} {f} 점수', sc[i], v['점수'], 3); C(f'{c} {f} 합', tot[i], v['전체']['합'], 1)
        C(f'{c} {f} 앞', a[i], v['1~6월']['합'], 1); C(f'{c} {f} 뒤', b[i], v['7~10월']['합'], 1)
        C(f'{c} {f} 9~10월', s9[i], v['9~10월']['합'], 1)
for f in ['HV(1.2)', 'HV(1.4)']: C(f'VT {f} MDD', '−7.6', V('VT', f)['전체']['MDD'], 1)
for f in ['LV(0.8)', 'LV(0.7)', 'LATE(780)', 'LATE(840)', 'GA(0.2)', 'GA(0.4)']: C(f'VT {f} MDD', '−12.1', V('VT', f)['전체']['MDD'], 1)
for f in ['LV(0.8)', 'LV(0.7)', 'GA(0.2)', 'GA(0.4)']: C(f'M1 {f} MDD', '−42.7', V('M1_s1.0', f)['전체']['MDD'], 1)
bad6 = []
for desc, shown, val, nd in claims:
    want = num(shown)
    got = round(val, nd) if nd else val
    if abs(want - got) > 1e-9 and not (nd and abs(want - val) <= 0.5 * 10 ** -nd + 1e-9):
        bad6.append(f'{desc} 표 {shown} vs 출력 {val}')
out('PASS' if not bad6 else 'FAIL', f'6 §1 표 개별 칸({len(claims)}개)', '; '.join(bad6) if bad6 else '모두 일치')
# 범위 행
def rng(c, fs, key):
    xs = [(V(c, f)['점수'] if key == '점수' else V(c, f)['전체'][key]) for f in fs]
    return min(xs), max(xs)
ve8 = FL[1:]
lo, hi = rng('VE', ve8, '점수'); e = [] if (r3(lo), r3(hi)) == ('0.055', '1.668') else [f'점수 {lo}~{hi}']
lo, hi = rng('VE', ve8, '합'); e += [] if (r1(lo), r1(hi)) == ('63.2', '285.6') else [f'합 {lo}~{hi}']
lo, hi = rng('VE', ve8, 'MDD'); e += [] if (r1(hi), r1(lo)) == ('0.0', '-12.5') else [f'MDD {hi}~{lo}']
e += [] if all(V('VE', f)['자격'] for f in ve8) else ['자격 O 아님']
e += [] if all(V('VE', f)['9~10월']['합'] == 0 for f in ve8) else ['9~10월 0 아님']
out('PASS' if not e else 'FAIL', '6 §1 VE 그 밖 8판 범위', '; '.join(e) if e else '점수 0.055~1.668 · 합 63.2~285.6 · MDD 0.0~−12.5 일치')
m4 = ['HV(1.2)', 'HV(1.4)', 'LATE(780)', 'LATE(840)']
lo, hi = rng('M1_s1.0', m4, '점수'); e = [] if (r3(lo), r3(hi)) == ('0.000', '0.185') else [f'점수 {lo}~{hi}']
lo, hi = rng('M1_s1.0', m4, '합'); e += [] if (r1(lo), r1(hi)) == ('0.0', '110.7') else [f'합 {lo}~{hi}']
e += [] if not any(V('M1_s1.0', f)['자격'] for f in m4) else ['자격 X 아님']
out('PASS' if not e else 'FAIL', '6 §1 M1 HV·LATE 범위', '; '.join(e) if e else '점수 0.000~0.185 · 합 0.0~110.7 · 자격 X 일치')
e = [f'{c} {f}' for c in CS for f in FL if V(c, f)['자격'] != (c != 'M1_s1.0')]
out('PASS' if not e else 'FAIL', '6 §1 자격 O/X 열', '; '.join(e) if e else 'VT·VE 모두 O · M1 모두 X')
# §2
Rn = A['새 추세 봇']
s2 = [('합 +1289.96', Rn['real']['전체']['합'], 1289.96, 2), ('MDD −11.52', Rn['real']['전체']['MDD'], -11.52, 2),
      ('최악 −7.18', Rn['real']['전체']['최악'], -7.18, 2), ('앞 +733.49', Rn['real']['1~6월']['합'], 733.49, 2),
      ('뒤 +556.47', Rn['real']['7~10월']['합'], 556.47, 2), ('9~10월 +49.95', Rn['real']['9~10월']['합'], 49.95, 2),
      ('09-21 이후 +14.85', Rn['real']['09-21 이후']['합'], 14.85, 2), ('mtm +1114.40', Rn['mtm']['전체']['합'], 1114.40, 2),
      ('mtm MDD −20.64', Rn['mtm']['전체']['MDD'], -20.64, 2)]
e = [f'{t} vs 출력 {v}' for t, v, w, nd in s2 if abs(round(v, nd) - w) > 1e-9]
out('PASS' if not e else 'FAIL', '6 §2 조립 숫자(9개)', '; '.join(e) if e else '모두 일치')
nd = len(Rn['real_날별'])
out('PASS' if nd == 183 and '183일' in R else 'FAIL', '6 §2 183일', f'출력 날 수 {nd}')
# 본문 글 확인(§3)
e = []
if not (P['VT']['HV(1.2)']['뺀 거래'] == 73 and P['VT']['HV(1.2)']['뺀 거래'] + P['VT']['HV(1.2)']['잡힌 N'] == 130): e.append('VT 130건 중 73건')
if not (P['VT']['LV(0.8)']['뺀 거래'] == P['VT']['LV(0.7)']['뺀 거래'] == 25 and P['VE']['LV(0.8)']['뺀 거래'] == P['VE']['LV(0.7)']['뺀 거래'] == 1): e.append('LV 뺀 거래 같음')
out('PASS' if not e else 'FAIL', '6 §3 본문 수치(73/130 · LV 25/1)', '; '.join(e) if e else '일치')
# smoke(QUESTION §0) 뺀 거래 수와 결과 비교
smoke = {'VT': [73, 64, 25, 25, 36, 20, 31, 24], 'VE': [21, 20, 1, 1, 10, 5, 7, 5], 'M1_s1.0': [61, 50, 27, 24, 121, 121, 3, 2]}
e = [f'{c} {f} smoke {smoke[c][i]} vs 결과 {P[c][f]["뺀 거래"]}' for c in CS for i, f in enumerate(FL[1:]) if smoke[c][i] != P[c][f]['뺀 거래']]
out('PASS' if not e else 'FAIL', '6 QUESTION smoke 뺀 거래 = 결과', '; '.join(e) if e else '24/24 일치')
# 7
for n in ['맥락(a · g · em) 가용 시각(진입 분에 알 수 있었는지)', '비공개 filt1.py / rl_exit1.ctx 구현', 'tla 재생(부품 혼자 · 조립 손익)', '원천 장부(exit1 거래 목록 · pool_ledger.json)']:
    out('NEEDS_DATA', '7 ' + n, '공개 파일로 확인 불가')
print(f"합계 PASS {cnt['PASS']} · FAIL {cnt['FAIL']} · NEEDS_DATA {cnt['NEEDS_DATA']}")
