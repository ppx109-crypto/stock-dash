"""RNK-0034(GPT 1순위 가설) — 시총 순위 상승 모멘텀: 20거래일마다, 전날 p 시총 200위 안에서 60거래일 동안 순위가 가장 많이 오른
10종목을 그날 t 종가에 똑같이 사서 다음 바꿔 담는 날 종가에 팖. p 자료(data.go.kr)는 p+1 낮 공개 → t = p+1 종가 체결.
사전등록: research-exchange/claude-to-gpt/RNK-0034/PREREG.md
- 자료 · 달력 · 수정 수익 g · 못 삼 / 결손(lo · hi) · 판 날 정지 · 비용 회계는 research/t003.py(STR-0030 09c7ff9e 판)를 그대로 불러 씀.
- 순위 = 그날 위 400 줄 가운데 모집단(6자리 숫자 · 끝자리 5/7/9 제외) 시총 순위. 순위 오름 = 순위(p − 60) − 순위(p).
  p − 60에 줄이 없는 종목(위 400 밖 · 새 상장)은 신호 없음.
- 대조(사전 고정): 같은 Universe(200) 전체 · 가격 모멘텀 위 10(같은 60일 g를 이은 값 · 하루라도 g 없으면 신호 없음).
- 결합 계좌: 기존 운영 조합 NAV(80%) + 후보(20%) · 후보 바꿔 담는 날마다 80:20으로 되돌림(옮긴 돈에 편도 0.175% · 이 밖 비용 없음).
python3 research/t006.py            (T_TO=YYYYMMDD — 자르기 시험)"""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t003 as S  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOX = ROOT / "research-exchange/claude-to-gpt/RNK-0034"
BASE = json.loads((BOX / "base_nav.json").read_text())   # {"path": ..., "sha256": ..., "date_col": ..., "nav_col": ...}
UNI, PICK, LOOK, STEP = 200, 10, 60, 20
W, MOVE = 0.20, 0.00175
S.TOP = 400   # load()의 top[d]를 위 400 전체 순위로 받음(아래에서 200으로 자름)


def base_nav():
    p = ROOT / BASE["path"]
    if hashlib.sha256(p.read_bytes()).hexdigest() != BASE["sha256"]:
        sys.exit("기존 조합 NAV 해시 다름")
    out = {}
    with p.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = r[BASE["date_col"]].replace("-", "")
            if not S.TO or d <= S.TO:
                out[d] = float(r[BASE["nav_col"]])
    return out


def cohorts(g, top, cal):
    """[(산 날 칸 i, 판 날 칸 j, 후보 10, 대조 전체, 가격 모멘텀 10)] · 고르기는 p = i − 1까지 자료만."""
    idx = list(range(LOOK + 1, len(cal), STEP))
    out = []
    for k, i in enumerate(idx):
        p, q = i - 1, i - 1 - LOOK
        rank_p = {c: n for n, c in enumerate(top[cal[p]], 1)}
        rank_q = {c: n for n, c in enumerate(top[cal[q]], 1)}
        uni = top[cal[p]][:UNI]
        rise = [(-(rank_q[c] - rank_p[c]), rank_p[c], c) for c in uni if c in rank_q]
        picks = [c for *_, c in sorted(rise)][:PICK]
        mom = []
        for c in uni:
            x, ok = 1.0, True
            for z in range(p - LOOK + 1, p + 1):
                if c not in g[cal[z]]:
                    ok = False
                    break
                x *= g[cal[z]][c]
            if ok:
                mom.append((-x, c))
        pm = [c for _, c in sorted(mom)][:PICK]
        j = idx[k + 1] if k + 1 < len(idx) else None
        out.append((i, j, picks, list(uni), pm))
    return out


def run(cap, vol, g, cal, cos, c, mode, which):
    """S.run과 같은 회계 · which: pick / ctl / mom."""
    conv = [(i, j, {"pick": p, "ctl": u, "mom": m}[which], u) for i, j, p, u, m in cos]
    return S.run(cap, vol, g, cal, conv, c, mode, "pick")


def combine(navc, base, lo, hi):
    """결합 계좌(현금 1에서): 날마다 두 조각을 각자 수익으로 굴리고, 후보 바꿔 담는 날(navc에서 표시)마다 80:20으로 되돌림."""
    days = [d for d, _ in navc if lo <= d <= hi and d in base]
    cv = dict(navc)
    reb = set(BASE.get("_reb", []))
    out, a, b, prev = [], (1 - W), W, None
    for d in days:
        if prev is None:
            b = W * cv[d]   # 후보 첫날 NAV에는 첫 산 비용이 들어 있음(현금 1 기준)
        else:
            a *= base[d] / base[prev]
            b *= cv[d] / cv[prev]
            if d in reb:
                tot = a + b
                tot -= abs(b - W * tot) * MOVE
                a, b = (1 - W) * tot, W * tot
        out.append((d, a + b))
        prev = d
    return out


def main():
    S.check()
    cap, vol, g, top, cal, no_vs, resume = S.load()
    base = base_nav()
    cos = cohorts(g, top, cal)
    BASE["_reb"] = [cal[i] for i, *_ in cos]
    out = {"task": "RNK-0034", "round": 1, "first": min(cap), "last": max(cap), "T_TO": S.TO or None, "cohorts": len(cos),
           "base": {k: v for k, v in BASE.items() if not k.startswith("_")}, "base_first": min(base), "base_last": max(base)}
    for mode in ("lo", "hi"):
        tp, navp, logs = run(cap, vol, g, cal, cos, S.COST, mode, "pick")
        tps, navs, _ = run(cap, vol, g, cal, cos, S.STRESS, mode, "pick")
        tc = run(cap, vol, g, cal, cos, S.COST, mode, "ctl")[0]
        tm = run(cap, vol, g, cal, cos, S.COST, mode, "mom")[0]
        out[mode] = {}
        for p, (lo, hi) in S.PERIODS.items():
            a, s_, c_, m_ = (S.within(x, lo, hi) for x in (tp, tps, tc, tm))
            if not a:
                continue
            mean = lambda xs: sum(r[2] for r in xs) / len(xs)
            sub = [x for x in cos if x[1] is not None and lo <= cal[x[0]] and cal[x[1]] <= hi]
            na = run(cap, vol, g, cal, sub, S.COST, mode, "pick")[1]
            ns = run(cap, vol, g, cal, sub, S.STRESS, mode, "pick")[1]
            bo = [(d, base[d]) for d, _ in na if d in base]
            bo = [(d, v / bo[0][1]) for d, v in bo]
            out[mode][p] = {"pick": S.summary([r[2] for r in a]), "pick_stress": S.summary([r[2] for r in s_]),
                            "control": S.summary([r[2] for r in c_]), "price_mom": S.summary([r[2] for r in m_]),
                            "diff_ctl_pct": round((mean(a) - mean(c_)) * 100, 4), "diff_mom_pct": round((mean(a) - mean(m_)) * 100, 4),
                            **S.boot(a, c_), "pick_vs_mom_ci95_pct": S.boot(a, m_)["diff_ci95_pct"],
                            "risk_alone": S.risk(na), "risk_alone_stress": S.risk(ns),
                            "risk_base": S.risk(bo), "risk_combined": S.risk(combine(na, base, lo, hi)),
                            "risk_combined_stress": S.risk(combine(ns, base, lo, hi)),
                            "mean_rank_pick": round(sum(sum(top[cal[x[0] - 1]].index(c) + 1 for c in x[2]) / len(x[2]) for x in sub) / len(sub), 2)}
        out[mode]["trades"] = [[b, s, round(x * 100, 6)] for b, s, x in tp]
        out[mode]["navs_all"] = [[d, round(v, 12)] for d, v in navp]
        if mode == "lo":
            out["pick_unfilled"] = [[cal[i], nm] for (i, *_), lg in zip(cos, logs) for nm in lg["unfilled"]]
            out["pick_gaps"] = [x for lg in logs for x in lg["gap"]]
            out["pick_sell_halt"] = [x for lg in logs for x in lg["sell_halt"]]
    out["picks"] = [[cal[i], cal[j] if j is not None else None, p, m] for i, j, p, _, m in cos]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
