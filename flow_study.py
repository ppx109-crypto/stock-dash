"""스승님 수급 조건 검증 — 외국인과 투신이 사고 개인이 팔면 그 뒤에 오르는가.

investor-data(개인·외국인·기관·투신·연기금·사모 순매수, 2017~)와 price-data(수정 종가)로 셉니다.
신호는 그날까지의 수급만 보고, 다음 날 종가에 사서 5·20·60거래일 뒤 수익률을 셉니다(수급은 장 마감 뒤에 나옴). 시장 전체가 오른 덕을
빼려고 **같은 날 같은 무리 평균과의 차이**를 함께 적고, 2017~2020과 2021~ 두 반으로 나눠
방향이 같은지 봅니다. 결과는 study/flow_study.json에 남깁니다.
"""
import json
import statistics as stats
from pathlib import Path

import caps
import study

DATA = Path("investor-data")
OUT = Path("study") / "flow_study.json"
SPANS = (5, 20, 60)
MID = "20210101"
TOP = 100


def load_flows(folder=DATA):
    found = {}
    for path in sorted(folder.glob("*.json")):
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        cols = body.get("cols") or []
        found[body.get("code") or path.stem] = [dict(zip(cols, row)) for row in body.get("rows") or []]
    return found


def _sum(rows, key):
    values = [r.get(key) for r in rows]
    return None if any(v is None for v in values) else sum(values)


def signals(window, cap):
    """그날까지의 수급 창(오래된 날이 먼저, 마지막이 그날)으로 켜진 신호들."""
    today = window[-1]
    got = {}
    def buys(rows):
        f, t, p = _sum(rows, "외국인"), _sum(rows, "투신"), _sum(rows, "개인")
        return None if None in (f, t, p) else (f > 0 and t > 0 and p < 0)
    got["그날 외국인·투신 매수 + 개인 매도"] = buys([today])
    if len(window) >= 3:
        got["사흘 연속"] = all(buys([r]) for r in window[-3:])
    if len(window) >= 5:
        got["닷새 합"] = buys(window[-5:])
        f5, p5 = _sum(window[-5:], "외국인"), _sum(window[-5:], "개인")
        t5, o5 = _sum(window[-5:], "투신"), _sum(window[-5:], "기관")
        got["닷새 합 · 외국인만 매수"] = None if f5 is None else f5 > 0
        got["닷새 합 · 투신만 매수"] = None if t5 is None else t5 > 0
        got["닷새 합 · 외국인·기관 매수 + 개인 매도"] = (None if None in (f5, o5, p5)
                                              else f5 > 0 and o5 > 0 and p5 < 0)
        got["반대: 닷새 합 개인만 매수"] = (None if None in (f5, t5, p5) else f5 < 0 and t5 < 0 and p5 > 0)
        price = today.get("종가")
        if cap and price and f5 is not None and t5 is not None:
            # 외국인+투신 닷새 순매수 금액이 시가총액의 몇 %인가. 크기를 종목끼리 견주려고 나눕니다.
            got["_세기"] = (f5 + t5) * price / cap * 100
    if len(window) >= 20:
        got["스무날 합"] = buys(window[-20:])
    return got


def observe(flows, prices):
    """(날짜, 신호들, 그 뒤 수익률들, 순위) 관측을 모읍니다."""
    found = []
    for code, rows in flows.items():
        block = prices.get(code)
        if not block or len(rows) < 25:
            continue
        index = {d: k for k, (d, _) in enumerate(block["rows"])}
        closes = [c for _, c in block["rows"]]
        for k in range(len(rows)):
            day = rows[k]["date"]
            i = index.get(day)
            if i is None:
                continue
            shares = caps.known_by(code, day)
            cap = shares * rows[k]["종가"] if shares and rows[k].get("종가") else None
            # 그날 수급은 장이 끝난 뒤에야 나오므로 그날 종가에는 살 수 없습니다. 다음 날 종가에 산 셈입니다.
            buy = i + 1
            ahead = {s: (closes[buy + s] / closes[buy] - 1) * 100 for s in SPANS if buy + s < len(closes)}
            if not ahead:
                continue
            found.append({"code": code, "date": day, "ahead": ahead,
                          "size": shares * closes[i] if shares else None,
                          "on": signals(rows[max(0, k - 19):k + 1], cap)})
    # 그날 시가총액 순위(caps와 같은 셈 · 수정 종가 × 그날까지 알려진 주식 수)
    by_day = {}
    for o in found:
        if o["size"]:
            by_day.setdefault(o["date"], []).append(o)
    for here in by_day.values():
        here.sort(key=lambda o: -o["size"])
        for place, o in enumerate(here, 1):
            o["rank"] = place
    # 세기 위 10%: 그날 무리 안에서 줄을 세웁니다.
    for here in by_day.values():
        power = sorted((o["on"]["_세기"] for o in here if o["on"].get("_세기") is not None), reverse=True)
        if len(power) >= 20:
            edge = power[len(power) // 10]
            for o in here:
                if o["on"].get("_세기") is not None:
                    o["on"]["외국인+투신 닷새 순매수 세기 위 10%"] = o["on"]["_세기"] >= edge
    return found


def tally(sel, base):
    out = {}
    for s in SPANS:
        pairs = [(o["ahead"][s], base[s].get(o["date"])) for o in sel if s in o["ahead"]]
        pairs = [(r, b) for r, b in pairs if b is not None]
        if len(pairs) < 30:
            continue
        moves = [r for r, _ in pairs]
        out[str(s)] = {"건수": len(moves), "종목수": len({o["code"] for o in sel}),
                       "오른 비율": round(sum(m > 0 for m in moves) / len(moves) * 100, 1),
                       "평균": round(stats.mean(moves), 2), "중앙": round(stats.median(moves), 2),
                       "시장보다": round(stats.mean(r - b for r, b in pairs), 2)}
    return out


def compute():
    prices = study.load_prices()
    flows = load_flows()
    obs = [o for o in observe(flows, prices) if o["date"] >= "20170101"]
    names = sorted({k for o in obs for k in o["on"] if not k.startswith("_")})
    result = {"stocks": len(flows), "observations": len(obs),
              "period": [min(o["date"] for o in obs), max(o["date"] for o in obs)] if obs else None,
              "pools": {}}
    for pool_name, pool in (("시총 100위 안", [o for o in obs if o.get("rank") and o["rank"] <= TOP]),
                            ("모은 종목 전체", obs)):
        halves = {}
        for half, part in (("2017~2020", [o for o in pool if o["date"] < MID]),
                           ("2021~", [o for o in pool if o["date"] >= MID])):
            base = {s: {} for s in SPANS}
            for s in SPANS:
                acc = {}
                for o in part:
                    if s in o["ahead"]:
                        acc.setdefault(o["date"], []).append(o["ahead"][s])
                base[s] = {d: sum(v) / len(v) for d, v in acc.items()}
            rows = {"전체": tally(part, base)}
            for name in names:
                rows[name] = tally([o for o in part if o["on"].get(name) is True], base)
            halves[half] = rows
        result["pools"][pool_name] = halves
    return result


if __name__ == "__main__":
    got = compute()
    OUT.write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f'종목 {got["stocks"]} · 관측 {got["observations"]:,} · {got["period"]}')
    for pool, halves in got["pools"].items():
        print(f"\n== {pool} ==")
        for half, rows in halves.items():
            print(f"  [{half}]")
            for name, t in rows.items():
                cells = " | ".join(f'{s}일 {v["건수"]}건 오름 {v["오른 비율"]}% 시장보다 {v["시장보다"]:+.2f}'
                                   for s, v in t.items())
                print(f"    {name:34s} {cells}")
