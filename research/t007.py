"""LOAN-0037 — 대차잔고율 축소(생존 272 종목 안 탐색 1판 · GPT #179 조건).
사전등록: research-exchange/claude-to-gpt/LOAN-0037/PREREG.md
- 대차잔고율(d) = loan-data 잔고주수(d) ÷ public-daily-v2 상장주식수(d)(그날 위 400 줄이 있을 때만 · 없으면 미사용 · 원주수로 대신 안 함).
- 신호 날 t = 달마다 첫 유효 거래일(STR-0030 달력). 감소율 = 잔고율(t) ÷ 잔고율(t − 20칸) − 1(둘 다 있어야 · 0이면 미사용).
- 고르기: 그날 잔고율이 있는 종목 가운데 잔고율 위 30%(올림) → 감소율이 가장 낮은(가장 많이 준) 10종목.
  대조 1 = 그 위 30% 전체 · 대조 2 = 감소율이 가장 높은(가장 많이 는) 10종목.
- 체결: 대차 자료는 t 장 끝 뒤 확정 → t+1 종가에 사서 20거래일 뒤 종가에 팖(똑같은 몫 · 다음 달 신호까지 남는 날은 현금).
- 수익 · 결손 · 비용 회계는 research/t003.py(STR-0030) slots 그대로(lo · hi 두 경계) · 비용 왕복 0.5% · 스트레스 1.0%.
- 결합 계좌: ACCT-NAV-0035 A(MAXRET-0026 m1.csv · 흔들림 상한 1배) 80% + 후보 20% · 후보 산 날마다 80:20으로 되돌림(옮긴 돈 편도 0.25%).
python3 research/t007.py            (T_TO=YYYYMMDD — 자르기 시험)"""
import csv
import hashlib
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t003 as S  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOX = ROOT / "research-exchange/claude-to-gpt/LOAN-0037"
LOAN = ROOT / "loan-data"
LOOK, HOLD, TOPQ, PICK = 20, 20, 0.30, 10
COST, STRESS = 0.005, 0.010
W, MOVE = 0.20, 0.0025
END = "20260916"   # 결합 기준 A(base_m1.csv)의 마지막 날 — B · ALL · 모든 판정을 여기서 끊음(round 2 고침)
PERIODS = {"A": ("20200101", "20221231"), "B": ("20230101", END), "ALL": ("20200101", END)}
BLOCK, REPS, SEED = 3, 10000, 20261010
LOCK = json.loads((BOX / "inputs_sha256.json").read_text())
DUPS = []   # [종목, 날, 값이 같은지] — 같은 값 중복은 하나로 · 다른 값이면 멈춤


def check_inputs():
    for rel, h in LOCK.items():
        g = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if g != h:
            sys.exit(f"입력 해시 다름 {rel}")


def load_loan():
    out = {}
    for f in sorted(LOAN.glob("*.json")):
        if not f.stem.isdigit():
            continue
        rows = json.loads(f.read_text()).get("rows", [])
        m = {}
        for r in rows:
            if S.TO and r["date"] > S.TO:
                continue
            if r["date"] in m:
                DUPS.append([f.stem, r["date"], m[r["date"]] == r.get("잔고주수")])
            m[r["date"]] = r.get("잔고주수")
        out[f.stem] = m
    conflict = [d for d in DUPS if not d[2]]
    if conflict:
        sys.exit(f"대차 중복일 값 상충 {len(conflict)}건(예: {conflict[:3]}) — 멈춤")
    return out


def load_shares():
    sh = defaultdict(dict)
    for name in sorted(S.SHA_PD):
        with (S.PD / name).open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if S.TO and r["날"] > S.TO:
                    continue
                if r["상장주식수"] not in ("", None) and float(r["상장주식수"]) > 0:
                    sh[r["날"]][r["코드"]] = float(r["상장주식수"])
    return sh


def ratio(loan, sh, code, d):
    b = loan.get(code, {}).get(d)
    s = sh.get(d, {}).get(code)
    if b is None or not s or b <= 0:
        return None
    return b / s


def cohorts(loan, sh, cal):
    """[(산 날 칸 i = t+1, 판 날 칸 j = i + 20, 고른 10, 대조 1, 대조 2)] · 고르기는 t까지 자료만."""
    out = []
    for x in range(LOOK, len(cal) - 1):
        if cal[x][:6] == cal[x - 1][:6]:
            continue
        t, q = cal[x], cal[x - LOOK]
        rs = {c: r for c in loan if (r := ratio(loan, sh, c, t)) is not None}
        if len(rs) < PICK * 4:
            continue
        top = sorted(rs, key=lambda c: (-rs[c], c))[:math.ceil(len(rs) * TOPQ)]
        chg = {c: rs[c] / r0 - 1 for c in top if (r0 := ratio(loan, sh, c, q)) is not None}
        down = [c for c in sorted(chg, key=lambda c: (chg[c], c))][:PICK]
        up = [c for c in sorted(chg, key=lambda c: (-chg[c], c))][:PICK]
        i = x + 1
        out.append([i, i + HOLD if i + HOLD < len(cal) else None, down, top, up, t])
    # round 2 고침: 판 날 = min(산 날 + 20칸, 다음 바구니 산 날) — 겹쳐 들지 않음 · 같은 날이면 그 종가에 팔고 삼
    for k in range(len(out) - 1):
        nxt = out[k + 1][0]
        if out[k][1] is None or out[k][1] > nxt:
            out[k][1] = nxt
    return [tuple(o) for o in out]


def run(cap, vol, g, cal, cos, c, mode, which):
    """t003.run과 같은 회계 · 바구니 사이 현금 날은 NAV를 그대로 이어 적음."""
    k = {"pick": 2, "ctl": 3, "up": 4}[which]
    last = len(cal) - 1
    trades, nav, V, logs = [], [], 1.0, []
    prev_end = None
    for co in cos:
        i, j, names = co[0], co[1], co[k]
        if prev_end is not None:
            for x in range(prev_end + 1, i):
                nav.append((cal[x], V))
        xs, rows, info = S.slots(cap, vol, g, cal, i, j, names, mode, c, last)
        n = len(rows)
        basket = [sum(r[s] for r in rows) / n for s in range(len(xs))] if n else [1.0] * len(xs)
        start = V
        for s in range(len(xs)):
            day = cal[xs[s]]
            if nav and nav[-1][0] == day:      # 앞 바구니 판 날 = 이 바구니 산 날: 한 줄로(판 비용 뒤 값 × 산 비용)
                nav[-1] = (day, start * basket[s])
            else:
                nav.append((day, start * basket[s]))
        assert all(nav[z][0] < nav[z + 1][0] for z in range(len(nav) - 1)), "NAV 날짜 순서"
        V = start * basket[-1]
        if j is not None:
            trades.append((cal[i], cal[j], basket[-1] - 1))
        logs.append(info)
        prev_end = xs[-1]
        if j is None:
            break
    return trades, nav, logs


def base_a():
    p = ROOT / "research-exchange/claude-to-gpt/LOAN-0037/base_m1.csv"
    return {r["날"]: float(r["NAV"]) for r in csv.DictReader(p.open(encoding="utf-8")) if not S.TO or r["날"] <= S.TO}


def combine(navc, base, reb, lo, hi):
    """결합 계좌(round 2 고침 2): 기준 A의 거래일을 하나의 시간축으로 씀.
    후보 몫은 첫 매수 전 현금(1.0) · 후보 NAV가 없는 날은 앞 값 유지. 기간 첫날 수익은 기간 앞 마지막 기준 거래일에서 셈.
    후보 바꿔 담는 날(reb)마다 80:20으로 되돌림(옮긴 돈 편도 MOVE)."""
    bdays = sorted(base)
    days = [d for d in bdays if lo <= d <= hi]
    miss = [d for d, _ in navc if lo <= d <= hi and d not in base]
    if miss or not days:
        sys.exit(f"결합 기준 A에 없는 후보 날 {len(miss)}개(예: {miss[:3]}) 또는 기간 날 없음 — 멈춤")
    cmap, cv, last = dict(navc), {}, 1.0
    for d in bdays:
        if d in cmap:
            last = cmap[d]
        cv[d] = last
    prev = [d for d in bdays if d < lo]
    p0 = prev[-1] if prev else days[0]
    a, b, pa, pc = (1 - W), W, base[p0], cv[p0]
    out = []
    for d in days:
        a *= base[d] / pa
        b *= cv[d] / pc
        pa, pc = base[d], cv[d]
        if d in reb:
            tot = a + b
            tot -= abs(b - W * tot) * MOVE
            a, b = (1 - W) * tot, W * tot
        out.append((d, a + b))
    assert all(out[z][0] < out[z + 1][0] for z in range(len(out) - 1)), "결합 NAV 날짜 순서"
    return out


def paired_boot(a, c):
    """같은 산 날 짝(R − 대조 1) · 달 블록 3달 · 10,000번."""
    by = defaultdict(list)
    cm = {r[0]: r[2] for r in c}
    for r in a:
        if r[0] in cm:
            by[r[0][:6]].append(r[2] - cm[r[0]])
    months = sorted(by)
    rng = random.Random(SEED)
    nb = math.ceil(len(months) / BLOCK)
    ms = []
    for _ in range(REPS):
        xs = []
        for _ in range(nb):
            s = rng.randrange(0, len(months) - BLOCK + 1)
            for m in months[s:s + BLOCK]:
                xs += by[m]
        if xs:
            ms.append(sum(xs) / len(xs))
    q = lambda v, p: sorted(v)[int(p * (len(v) - 1))]
    return [round(q(ms, .025) * 100, 4), round(q(ms, .975) * 100, 4)] if ms else None


def receipt(loan):
    rep = {"files": len(loan), "start": {}, "end": {}, "zero_or_missing": 0, "dup_same_value": sum(1 for d in DUPS if d[2])}
    for c, m in loan.items():
        ds = sorted(m)
        rep["start"][c], rep["end"][c] = (ds[0], ds[-1]) if ds else (None, None)
        rep["zero_or_missing"] += sum(1 for v in m.values() if not v)
    st = defaultdict(int)
    for v in rep["start"].values():
        st[v] += 1
    rep["start_counts"], rep["end_counts"] = dict(st), {}
    for v in rep["end"].values():
        rep["end_counts"][v] = rep["end_counts"].get(v, 0) + 1
    del rep["start"], rep["end"]
    return rep


def main():
    S.check()
    check_inputs()
    cap, vol, g, _, cal, no_vs, resume = S.load()
    loan, sh, base = load_loan(), load_shares(), base_a()
    cos = cohorts(loan, sh, cal)
    reb = {cal[co[0]] for co in cos}
    out = {"task": "LOAN-0037", "round": 2, "dups": DUPS, "T_TO": S.TO or None, "cohorts": len(cos), "receipt": receipt(loan),
           "first_signal": cos[0][5] if cos else None, "last_signal": cos[-1][5] if cos else None}
    for mode in ("lo", "hi"):
        tp, navp, logs = run(cap, vol, g, cal, cos, COST, mode, "pick")
        tps, navs, _ = run(cap, vol, g, cal, cos, STRESS, mode, "pick")
        tc = run(cap, vol, g, cal, cos, COST, mode, "ctl")[0]
        tu = run(cap, vol, g, cal, cos, COST, mode, "up")[0]
        tcs = run(cap, vol, g, cal, cos, STRESS, mode, "ctl")[0]
        out[mode] = {}
        for p, (lo, hi) in PERIODS.items():
            a, s_, c_, u_, cs_ = (S.within(x, lo, hi) for x in (tp, tps, tc, tu, tcs))
            if not a:
                continue
            mean = lambda xs: sum(r[2] for r in xs) / len(xs)
            def rebase(full):
                """기간 첫날 앞 날의 값을 1로 · 기간 안 날만(첫날 수익도 살림)."""
                before = [v for d, v in full if d < lo]
                base0 = before[-1] if before else 1.0
                return [(d, v / base0) for d, v in full if lo <= d <= hi]
            na, ns = navp, navs
            out[mode][p] = {"pick": S.summary([r[2] for r in a]), "pick_stress": S.summary([r[2] for r in s_]),
                            "ctl1": S.summary([r[2] for r in c_]), "ctl2_up": S.summary([r[2] for r in u_]),
                            "excess_vs_ctl1_pct": round((mean(a) - mean(c_)) * 100, 4),
                            "excess_vs_ctl1_stress_pct": round((mean(s_) - mean(cs_)) * 100, 4),
                            "excess_vs_ctl2_pct": round((mean(a) - mean(u_)) * 100, 4),
                            "paired_ci95_vs_ctl1_pct": paired_boot(a, c_),
                            "risk_alone": S.risk(rebase(na)), "risk_alone_stress": S.risk(rebase(ns)),
                            "risk_combined": S.risk(combine(na, base, reb, lo, hi)),
                            "risk_combined_stress": S.risk(combine(ns, base, reb, lo, hi))}
        out[mode]["trades"] = [[b, s, round(x * 100, 6)] for b, s, x in tp]
        out[mode]["navs_all"] = [[d, round(v, 12)] for d, v in navp]
        if mode == "lo":
            out["pick_unfilled"] = [[cal[co[0]], nm] for co, lg in zip(cos, logs) for nm in lg["unfilled"]]
            out["pick_gaps"] = [x for lg in logs for x in lg["gap"]]
            out["pick_sell_halt"] = [x for lg in logs for x in lg["sell_halt"]]
    out["picks"] = [[co[5], cal[co[0]], cal[co[1]] if co[1] is not None else None, co[2], co[4], len(co[3])] for co in cos]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
