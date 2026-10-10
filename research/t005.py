"""GAP-0033(GPT 예비 가설) — KODEX 200(069500) 갭다운 당일 반전: t 시가 < 전날 원주가 종가면
t 시가에 사서 t 종가에 팖(G · 주가설 하나). 아니면 현금. 대조: D 전체일(모든 날 시가 → 종가) · 매수 · 보유.
사전등록: research-exchange/claude-to-gpt/GAP-0033/PREREG.md
- 자료 · 분배금 표 · 비용(날마다 호가 상한 · 수수료) · 기간 · 위험 · 부트스트랩은 research/t004.py(OVN-0032 d9631826 판) 그대로 불러 씀.
- round 2(GPT #169 지적 2): 신호는 **전날 원주가 종가만** 씀(분배금을 빼지 않음 — 9:00에 금액을 알았다는 공개 시각 근거가 없어서).
  분배락 날 시가가 분배금만큼 내려가 갭다운으로 잡힐 수 있음(그날도 똑같이 셈 · 건수는 결과에 적음). D · G는 분배금을 받지 않아
  est · zero 두 가정의 결과가 같음(형식상 둘 다 적음).
python3 research/t005.py            (T_TO=YYYYMMDD — 자르기 시험)"""
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t004 as T  # noqa: E402


def gap_trades(raw, dist, cost):
    """[(날, 날, 순수익)] — 갭다운 날(시가 < 전날 원주가 종가)만 시가 → 종가. dist는 쓰지 않음(round 2)."""
    out = []
    for i in range(1, len(raw)):
        y, t = raw[i - 1], raw[i]
        if t[1] < y[4]:
            b, s = t[1], t[4]
            out.append((t[0], t[0], s * (1 - T.side(s, cost, t[0])) / (b * (1 + T.side(b, cost, t[0]))) - 1))
    return out


def boot_diff(g, d):
    """달 블록 부트스트랩(6달 · 10,000번 · 씨앗 20261010): 같은 달 블록에서 G와 D 전체일을 함께 뽑아 G 평균 · (G 평균 − D 평균)."""
    bg, bd = defaultdict(list), defaultdict(list)
    for x in g:
        bg[x[0][:6]].append(x[2])
    for x in d:
        bd[x[0][:6]].append(x[2])
    months = sorted(set(bg) | set(bd))
    rng = random.Random(T.SEED)
    nb = math.ceil(len(months) / T.BLOCK)
    mg, md = [], []
    for _ in range(T.REPS):
        xs, ys = [], []
        for _ in range(nb):
            s = rng.randrange(0, len(months) - T.BLOCK + 1)
            for m in months[s:s + T.BLOCK]:
                xs += bg[m]
                ys += bd[m]
        if xs and ys:
            mg.append(sum(xs) / len(xs))
            md.append(sum(xs) / len(xs) - sum(ys) / len(ys))
    q = lambda v, p: sorted(v)[int(p * (len(v) - 1))]
    return [round(q(mg, .025) * 100, 5), round(q(mg, .975) * 100, 5)], [round(q(md, .025) * 100, 5), round(q(md, .975) * 100, 5)]


def evaluate(raw, dist):
    out = {}
    g, gs = gap_trades(raw, dist, T.MAIN), gap_trades(raw, dist, T.STRESS)
    d = T.trades(raw, dist, T.MAIN, "D")
    for p, (lo, hi) in T.PERIODS.items():
        a, s, dd = T.within(g, lo, hi), T.within(gs, lo, hi), T.within(d, lo, hi)
        if not a:
            continue
        ci_g, ci_gd = boot_diff(a, dd)
        hn = T.hold(raw, dist, max(lo, dd[0][0]), hi, T.MAIN)
        out[p] = {"G": T.summary([x[2] for x in a]), "G_stress": T.summary([x[2] for x in s]), "D_all": T.summary([x[2] for x in dd]),
                  "gap_day_share_pct": round(len(a) / len(dd) * 100, 2), "G_mean_ci95_pct": ci_g, "G_minus_Dall_ci95_pct": ci_gd,
                  "risk_G": T.risk(T.nav_of(a, raw, lo, hi)), "risk_G_stress": T.risk(T.nav_of(s, raw, lo, hi)), "risk_hold": T.risk(hn)}
    return out, g


def main():
    T.check()
    raw, dists = T.load()
    out = {"task": "GAP-0033", "round": 2, "first": raw[0][0], "last": raw[-1][0], "T_TO": T.TO or None, "days": len(raw)}
    for k in ("est", "zero"):
        out[k], g = evaluate(raw, dists[k])
        out[k]["trades_G"] = [[b, s_, round(x * 100, 7)] for b, s_, x in g]
        out[k]["gap_days_on_ex_date"] = sorted(x[0] for x in g if x[0] in dists["est"])
        out[k]["navs_all_G"] = [[dd, round(v, 12)] for dd, v in T.nav_of(g, raw, raw[0][0], raw[-1][0])]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
