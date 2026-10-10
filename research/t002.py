"""REV-0029(NEW-BOT-0027 G1 · GPT 제안) — KODEX 200 단기 하락 뒤 반전: t일 판단에 t−1까지 값만 씀.
t−1 종가 ÷ t−4 종가 − 1 < 0이면 t일 종가에 069500을 사서 t+3거래일 종가에 팖. 한 자리만 · 들고 있는 동안 신호 무시 · 판 날 다시 사지 않음.
달력 · 자료 해시 · 비용(편도 나눔) · 기간 · 표본 경계 · 기간별 NAV · 달 블록 부트스트랩은 t001(TOM-0028 round 3) 그대로 불러 씀.
사전등록: research-exchange/claude-to-gpt/REV-0029/PREREG.md
python3 research/t002.py            (T_TO=YYYYMMDD면 그날까지 가격만 읽음 — 자르기 시험)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t001 as T  # noqa: E402

LOOK = 3


def plan(px, cal):
    """(산 날, 판 날). 산 날 t: 달력에서 t−1 · t−4 종가가 있고 그 3일 수익 < 0. 판 날 = t+3(달력). 겹치지 않게 앞에서부터."""
    out, i, free_from = [], LOOK + 1, 0
    while i + 0 < len(cal):
        if i >= free_from:
            a, b = cal[i - 1], cal[i - 1 - LOOK]
            if a in px and b in px and px[a] / px[b] - 1 < 0:
                s = cal[i + T.HOLD] if i + T.HOLD < len(cal) else None
                if s is None:
                    break
                out.append((cal[i], s))
                free_from = i + T.HOLD + 1            # 판 날(i+3)은 다시 사지 않음 → 그다음 날부터
        i += 1
    return out


def tom_like(px, plan_, c):
    return [(b, s, T.trade_ret(px, b, s, c)) for b, s in plan_ if b in px and s in px]


def control(px, cal, c):
    """같은 보유 길이 대조: 모든 거래일 종가에 사서 3거래일 뒤 종가에 판 순수익(조건 없음)."""
    return [(cal[i], cal[i + T.HOLD], T.trade_ret(px, cal[i], cal[i + T.HOLD], c))
            for i in range(len(cal) - T.HOLD) if cal[i] in px and cal[i + T.HOLD] in px]


def main():
    T.check()
    px, cal = T.load()
    p = plan(px, cal)
    out = {"task": "REV-0029", "round": 1, "price_first": min(px), "price_last": max(px), "T_TO": T.TO or None,
           "sha256": {k.name: v for k, v in T.SHA.items()}}
    t_all, ts_all = tom_like(px, p, T.COST), tom_like(px, p, T.STRESS)
    c_all = control(px, cal, T.COST)
    for name, (lo, hi) in T.PERIODS.items():
        t, ts, c = T.within(t_all, lo, hi), T.within(ts_all, lo, hi), T.within(c_all, lo, hi)
        if not t:
            continue
        mt, mc = sum(r[2] for r in t) / len(t), sum(r[2] for r in c) / len(c)
        out[name] = {"rev": T.summary([r[2] for r in t]), "rev_stress": T.summary([r[2] for r in ts]), "control": T.summary([r[2] for r in c]),
                     "diff_pct": round((mt - mc) * 100, 4), **T.boot(t, c),
                     "risk": T.risk(T.nav(px, cal, t, lo, hi, T.COST)), "risk_stress": T.risk(T.nav(px, cal, ts, lo, hi, T.STRESS))}
    out["trades"] = [[b, s, round(x * 100, 6)] for b, s, x in t_all]
    last = max(px)
    out["plan_without_price"] = [[b, s] for b, s in p if s <= last and (b not in px or s not in px)]
    out["calendar_days_without_price"] = sorted(d for d in cal if d <= last and d not in px)
    lo, _ = T.PERIODS["ALL"]
    out["navs_all"] = [[d, round(v, 12)] for d, v in T.nav(px, cal, [(b, s, None) for b, s in p if b in px], lo, last, T.COST)]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
