"""가족 A(거래 관리 · 청산 · 진입 확인) — H 낙폭 줄이기. 날 · 팔 고르기는 그대로(조용 → R0 · 아니면 S3).
python3 run_a.py → results_a.json · python3 run_a.py --daily → 판별 날별 손익만 출력(자르기 시험용)."""
import sys, json, os
sys.path.insert(0, "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/hdd")
from base import K, R4, Z, DAYS, stat
BY, COST, CAP, B15, E10, E20, BYD = K.BY, K.COST, K.CAP, K.B15, K.E10, K.E20, K.BYD
J15 = {(B15[j][0], B15[j][1]): j for j in range(len(B15))}
E15 = K.ind(B15, 15)

def execute2(d, sigs, delay=0, maxn=2, trail=None, block=None):
    """K.execute 복사 + 선택 기능. trail=(발동 ATR배, 따라붙는 ATR배): 진입 뒤 끝난 15분봉 고가(저가)로만 유리한 끝값 갱신 ·
    끝값이 진입가에서 발동배×ATR 이상이면 손절 = 끝값 − 따라붙는배×ATR(조이기만) · 끝난 봉 다음 분부터 적용.
    block='same'|'any': 그날 손절 난 방향(또는 모든 방향) 새 진입 막음."""
    x = BY[d]; real = 0.0; cnt = 0; free_at = 0; stopped = False; blocked = set()
    for (m0, side, tg, sd, m_exit) in sigs:
        if stopped or cnt >= maxn or CAP + real < 3.0: continue
        if block == "same" and side in blocked: continue
        if block == "any" and blocked: continue
        me = next((mm for mm in range(m0 + delay, 935) if mm in x), None)
        if me is None or me < free_at or me >= m_exit + delay: continue
        atr = E10[J15[(d, m0)]][1]
        ent = x[me][2]; sd = min(sd, max(0.5, CAP + real - 2 * COST)); stop = ent - side * sd; cnt += 1; out = None
        bq = [B15[j] for j in BYD[d] if B15[j][1] > me]; bi = 0; ext = None
        for m in range(me, 935):
            if m not in x: continue
            if trail:
                while bi < len(bq) and bq[bi][1] <= m:          # 이 분 시작 전에 끝난 15분봉만
                    b = bq[bi]; bi += 1; v = b[3] if side > 0 else b[4]
                    ext = v if ext is None else (max(ext, v) if side > 0 else min(ext, v))
                    if side * (ext - ent) >= trail[0] * atr:
                        ns = ext - side * trail[1] * atr
                        stop = max(stop, ns) if side > 0 else min(stop, ns)
            o, h, l, c = x[m][2], x[m][3], x[m][4], x[m][5]
            if m == me: o = ent
            if m >= m_exit + delay: out = (o, m, "정리분", m); break
            if (l <= stop) if side > 0 else (h >= stop): out = (min(o, stop) if side > 0 else max(o, stop), m, "손절", m + 1); break
            if tg is not None and ((h >= tg) if side > 0 else (l <= tg)): out = (max(o, tg) if side > 0 else min(o, tg), m, "목표", m + 1); break
            if real + side * (c - ent) - 2 * COST <= -CAP:
                nm = next((mm for mm in range(m + 1, 935) if mm in x), None); out = (x[nm][2] if nm else c, nm or m, "하루멈춤", 999); stopped = True; break
        if out is None: out = (K.last_close(d), 935, "끝", 999)
        r = side * (out[0] - ent) - 2 * COST; real += r; free_at = out[3]
        if out[2] == "손절": blocked.add(side)
        if real <= -CAP: stopped = True
    return real

# ── 신호 바꾸기 ──
def r0_hold(N):
    return lambda d: [(m, s, t, sd, min(mx, m + 15 * N)) for (m, s, t, sd, mx) in K.sig_r0(d)]
def r0_tgt(f):
    def g(d):
        out = []
        for (m, s, t, sd, mx) in K.sig_r0(d):
            c = B15[J15[(d, m)]][5]; out.append((m, s, c + f * (t - c), sd, mx))
        return out
    return g
def r0_confirm(minmove):
    """앞 봉 종가가 EMA10에서 1.0×ATR 이상 벌어졌고, 이번 봉 종가가 EMA10 쪽으로 minmove×ATR(앞 봉 ATR) 이상 돌아왔으면 이번 봉 끝에 진입.
    목표 = 이번 봉 EMA10 · 손절 1.0×이번 봉 ATR. 이번 봉 종가가 EMA10을 이미 넘었으면 안 함."""
    def g(d):
        out = []
        for j in BYD[d]:
            b = B15[j]; e, a = E10[j]
            if b[1] > 900 or a <= 0 or j < 1 or B15[j - 1][0] != d: continue
            pb = B15[j - 1]; pe, pa = E10[j - 1]
            if pa <= 0 or abs(pb[5] - pe) < 1.0 * pa: continue
            side = -1 if pb[5] > pe else 1
            if side * (b[5] - pb[5]) < max(minmove * pa, 1e-9): continue
            if side * (e - b[5]) <= 0: continue
            out.append((b[1], side, e, a, 915))
        return out
    return g
def s3_exit(EX):
    """S3과 같은 진입(T2 s1.5 + 기울기/ATR ≤ 0.5) · 정리만 15분 종가가 EX(EMA20 또는 EMA15)를 거꾸로 건널 때."""
    def g(d):
        js = BYD[d]; base = R4.s3(d); keep = {s[0] for s in base}; out = []
        for (m0, side, tg, sd, mx) in base:
            t = js.index(J15[(d, m0)]); m_exit = 915
            for q in js[t + 1:]:
                bb = B15[q]
                if bb[1] > 915: break
                if (bb[5] < EX[q][0]) if side > 0 else (bb[5] > EX[q][0]): m_exit = bb[1]; break
            out.append((m0, side, tg, sd, m_exit))
        return out
    return g

def run(r0f=K.sig_r0, s3f=R4.s3, r0kw=None, s3kw=None):
    p = {}
    for d in DAYS:
        if Z[d]: p[d] = execute2(d, r0f(d), **(r0kw or {}))
        else: p[d] = execute2(d, s3f(d), **(s3kw or {}))
    return p

VAR = {
    "기준 H": {},
    "A1 따라붙는 손절 발동1.0 · 폭1.0 (두 팔)": dict(r0kw={"trail": (1.0, 1.0)}, s3kw={"trail": (1.0, 1.0)}),
    "A2 따라붙는 손절 발동0.75 · 폭0.75 (두 팔)": dict(r0kw={"trail": (0.75, 0.75)}, s3kw={"trail": (0.75, 0.75)}),
    "A3 따라붙는 손절 발동1.5 · 폭1.0 (두 팔)": dict(r0kw={"trail": (1.5, 1.0)}, s3kw={"trail": (1.5, 1.0)}),
    "A4 R0 최대 보유 2봉(30분)": dict(r0f=r0_hold(2)),
    "A5 R0 최대 보유 3봉(45분)": dict(r0f=r0_hold(3)),
    "A6 R0 최대 보유 4봉(60분)": dict(r0f=r0_hold(4)),
    "A7 R0 확인 뒤 진입(되돌림 >0)": dict(r0f=r0_confirm(0.0)),
    "A8 R0 확인 뒤 진입(되돌림 ≥0.25ATR)": dict(r0f=r0_confirm(0.25)),
    "A9 R0 목표 EMA10까지 절반": dict(r0f=r0_tgt(0.5)),
    "A10 R0 목표 EMA10까지 3/4": dict(r0f=r0_tgt(0.75)),
    "A11 R0 손절 난 방향 그날 다시 안 들어감": dict(r0kw={"block": "same"}),
    "A12 R0 손절 한 번이면 그날 R0 끝": dict(r0kw={"block": "any"}),
    "A13 S3 정리 EMA20 건넘": dict(s3f=s3_exit(E20)),
    "A14 S3 정리 EMA15 건넘": dict(s3f=s3_exit(E15)),
}

if __name__ == "__main__":
    # 재현 확인: 바꾼 것 없는 복사본 = K.execute (두 팔 모두 · 모든 날)
    diff = 0.0
    for d in DAYS:
        for sg in (K.sig_r0(d), R4.s3(d)):
            diff = max(diff, abs(execute2(d, sg) - K.execute(d, sg, delay=0, maxn=2)))
    assert diff < 1e-9, diff
    hp = {d: K.execute(d, K.sig_r0(d) if Z[d] else R4.s3(d)) for d in DAYS}
    assert all(abs(run()[d] - hp[d]) < 1e-9 for d in DAYS)
    res = {}
    for k, kw in VAR.items():
        p = run(**kw); res[k] = {"stat": stat(p), "daily": {d: round(v, 4) for d, v in p.items()}}
    if sys.argv[1:] == ["--daily"]:
        print(json.dumps({k: v["daily"] for k, v in res.items()})); sys.exit()
    out = {"재현_최대차": diff, "날수": len(DAYS), "변형수": len(VAR) - 1, "판": res}
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_a.json"), "w"), ensure_ascii=False, indent=1)
    print("재현 최대 차이", diff)
    for k, v in res.items(): print(k, v["stat"])
