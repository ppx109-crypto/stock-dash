"""2차: 손익분기 손절 옮기기(진입가로) · 최근 성적 쉬기 · S3 손절폭 · 조합(같은 158일 · 탐색)."""
import sys, json; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from kmf_hdd_base import *
def execute_be(d, sigs, be=None, maxn=2):
    """K.execute와 같되 be가 있으면 유리한 쪽 움직임이 be × 손절폭에 닿은 다음 분부터 손절을 진입가(+비용)로 옮김."""
    x = K.BY[d]; real = 0.0; cnt = 0; free_at = 0; stopped = False
    for (m0, side, tg, sd, m_exit) in sigs:
        if stopped or cnt >= maxn or K.CAP + real < 3.0: continue
        me = next((mm for mm in range(m0, 935) if mm in x), None)
        if me is None or me < free_at or me >= m_exit: continue
        ent = x[me][2]; sd = min(sd, max(0.5, K.CAP + real - 2 * K.COST)); stop = ent - side * sd; cnt += 1; out = None; moved = False
        for m in range(me, 935):
            if m not in x: continue
            o, h, l, c = x[m][2], x[m][3], x[m][4], x[m][5]
            if m == me: o = ent
            if m >= m_exit: out = (o, m, m); break
            if (l <= stop) if side > 0 else (h >= stop): out = (min(o, stop) if side > 0 else max(o, stop), m, m + 1); break
            if tg is not None and ((h >= tg) if side > 0 else (l <= tg)): out = (max(o, tg) if side > 0 else min(o, tg), m, m + 1); break
            if real + side * (c - ent) - 2 * K.COST <= -K.CAP:
                nm = next((mm for mm in range(m + 1, 935) if mm in x), None); out = (x[nm][2] if nm else c, nm or m, 999); stopped = True; break
            if be and not moved and side * ((h if side > 0 else l) - ent) >= be * sd: stop = ent + side * 2 * K.COST; moved = True   # 다음 분부터 적용
        if out is None: out = (K.last_close(d), 935, 999)
        r = side * (out[0] - ent) - 2 * K.COST; real += r; free_at = out[2]
        if real <= -K.CAP: stopped = True
    return real
def run(be_r0=None, be_s3=None, s3s=1.5, s3t=0.5, r0max=2, skip_after=0, eqN=0):
    p = {}; lossrun = 0; hist = []
    for d in DAYS:
        if eqN and len(hist) >= eqN and sum(hist[-eqN:]) < 0: p[d] = 0.0; hist.append(shadow(d, be_r0, be_s3, s3s, s3t, r0max)); continue
        if Z[d] and skip_after and lossrun >= skip_after: p[d] = 0.0; lossrun = 0; hist.append(shadow(d, be_r0, be_s3, s3s, s3t, r0max)); continue
        p[d] = shadow(d, be_r0, be_s3, s3s, s3t, r0max); hist.append(p[d])
        if Z[d]: lossrun = lossrun + 1 if p[d] < 0 else 0
    return p
def shadow(d, be_r0, be_s3, s3s, s3t, r0max):
    if Z[d]: return execute_be(d, K.sig_r0(d), be=be_r0, maxn=r0max)
    sig = [x for x in K.sig_t(d, "T2", s=s3s) if R4.slope15(d, x[0]) <= s3t]
    return execute_be(d, sig, be=be_s3)
chk = run(); base_ok = all(abs(chk[d] - K.execute(d, R4.r0(d) if Z[d] else R4.s3(d))) < 1e-9 for d in DAYS); print("기준 재현", base_ok)
V = {"H(기준)": {}}
for b in (0.5, 1.0, 1.5): V[f"손익분기 옮기기 R0 · S3 {b}×손절폭"] = dict(be_r0=b, be_s3=b)
for b in (0.5, 1.0): V[f"손익분기 옮기기 S3만 {b}"] = dict(be_s3=b)
for b in (0.5, 1.0): V[f"손익분기 옮기기 R0만 {b}"] = dict(be_r0=b)
for s_ in (1.0, 2.0): V[f"S3 손절 {s_}ATR"] = dict(s3s=s_)
for t in (0.4, 0.6): V[f"S3 기울기 문턱 {t}"] = dict(s3t=t)
for n in (3, 5, 10): V[f"H 최근 {n}일 합 < 0이면 쉼(그림자 손익으로 셈)"] = dict(eqN=n)
V["R0 하루 1번 + R0 손실 2번 이어지면 쉼"] = dict(r0max=1, skip_after=2)
out = {}
for name, kw in V.items():
    out[name] = stat(run(**kw)); print(f"| {name} | " + " | ".join(str(out[name][x]) for x in ("합", "MDD", "최악", "나쁜달", "앞반", "뒤반", "연속손실", "회복최장")) + " |")
json.dump(out, open(Path(__file__).resolve().parent / "kmf_hdd_grid2_out.json", "w"), ensure_ascii=False, indent=1); print("시도", len(V) - 1)
