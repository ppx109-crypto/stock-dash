"""확률 검증 · 최종 조건(A·B그룹)이 과거에 실제로 맞았는지 셉니다.

앱의 '확률 검증' 화면이 읽는 study/final_study.json을 만듭니다. 두 가지를 셉니다.

1) 그룹별 성적: 2017년부터 날마다 모든 종목을 오늘 화면과 같은 잣대(final_group.shortfalls)로
   A(한 갈래의 조건을 모두 채움) · B(1~2개 모자람) · 그 밖으로 나누고, 그 뒤 5·20·60거래일
   수익률을 셉니다. 판정에는 그날까지의 종가만 씁니다.
2) 실제로 매매했다면: A그룹을 자리 5개 · 하루 2종목까지 사서 갈래마다 정한 대로 팔았을 때의
   연수익과 최대 낙폭(89회차 모의 매매 + 97회차 수급 조건). 순서를 조금씩 흔들어 여덟 번 돌린 가운데 값.
   수급(investor-data)이 없는 종목은 A가 될 수 없습니다.

표(study/features.json)가 있어야 합니다. 몇십 분 걸려 손으로 돌리고, 결과 파일만 저장소에 넣습니다.
"""
import bisect
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

import caps
import final_group
import lab
import rule
import study

OUT = Path("study") / "final_study.json"
SPANS = (5, 20, 60)
TRIES = 8
HALVES = (("2017~2020", rule.SINCE, rule.MID), ("2021~", rule.MID, None))


def _sma(closes, span):
    a = np.asarray(closes, float)
    total = np.cumsum(a)
    out = np.full(len(a), np.nan)
    out[span - 1:] = (total[span - 1:] - np.concatenate(([0.0], total[:-span]))) / span
    return out


def shapes(lanes, codes):
    """종목마다 날짜별 정배열 여부 · 선 간격 · 50일선>200일선. final_group.lines_now와 같은 잣대."""
    lines = final_group.LINES
    found = {}
    for code in codes:
        closes = lanes[code]["closes"]
        m = {span: _sma(closes, span) for span in sorted(set(lines) | {50})}
        ok = np.ones(len(closes), bool)
        for a, b in zip(lines, lines[1:]):
            ok &= m[a] > m[b]
        ok[:250] = False
        found[code] = {"정배열": ok, "간격": (m[lines[0]] / m[lines[-1]] - 1) * 100,
                       "50>200": m[50] > m[200], "200": m[200]}
    return found


def breadth_by_day(rows, shape):
    """그날 시총 100위 안 종목 가운데 50일선이 200일선 위인 몫(%)."""
    by_day = {}
    for row in rows:
        if not caps.inside(row, rule.TOP):
            continue
        one = shape[row["code"]]
        if np.isnan(one["200"][row["i"]]):
            continue
        by_day.setdefault(row["date"], []).append(bool(one["50>200"][row["i"]]))
    return {day: sum(v) / len(v) * 100 for day, v in by_day.items() if len(v) >= 30}


def form_of(shape, row):
    one = shape[row["code"]]
    i = row["i"]
    if i < 250:
        return {}
    gap = one["간격"][i]
    return {"정배열": bool(one["정배열"][i]), "간격": None if np.isnan(gap) else float(gap)}


def flow_index(codes):
    """종목마다 (날짜들, 수급 줄들). 그날 전날까지 5일 합을 빨리 찾으려고 둡니다."""
    found = {}
    for code in codes:
        rows = final_group.flow_rows(code)
        found[code] = ([r["date"] for r in rows], rows)
    return found


def flow_of(index, row):
    """그 행의 날 **전날까지** 5거래일 수급 합(final_group.flow_before와 같은 셈)."""
    days, rows = index.get(row["code"], ([], []))
    k = bisect.bisect_left(days, row["date"])
    return final_group.flow_before(rows[max(0, k - final_group.FLOW_DAYS):k], row["date"])


def grade(row, shape, breadth, flows=None):
    """A · B · 밖과, A라면 어느 갈래로 들어왔는지."""
    missing = final_group.shortfalls(row, form_of(shape, row), breadth.get(row["date"], 0.0), rule._calm,
                                     flow_of(flows or {}, row))
    doors = [door for door, gaps in missing.items() if not gaps]
    if doors:
        return "A", doors
    return ("B" if min(len(g) for g in missing.values()) <= 2 else "밖"), []


def tally(moves, codes):
    if not moves:
        return None
    ordered = sorted(moves)
    return {"건수": len(moves), "종목수": len(codes),
            "상승확률": round(sum(1 for m in moves if m > 0) / len(moves) * 100, 1),
            "평균수익률": round(sum(moves) / len(moves), 2),
            "중앙수익률": round(ordered[len(ordered) // 2], 2),
            "최악": round(ordered[0], 1), "최고": round(ordered[-1], 1)}


def group_table(rows, shape, breadth, flows=None):
    """그룹마다, 보유 기간마다 그 뒤 수익률을 모읍니다."""
    moves = {}
    for row in rows:
        group, doors = grade(row, shape, breadth, flows)
        row["_group"], row["_doors"] = group, doors
        for key in [group, "전체"] + [f"A · {d}" for d in doors]:
            for span in SPANS:
                if span in row["ahead"]:
                    bucket = moves.setdefault(key, {}).setdefault(span, ([], set()))
                    bucket[0].append(row["ahead"][span])
                    bucket[1].add(row["code"])
    order = ["A", f"A · {final_group.RULE_DOOR}", f"A · {final_group.LINES_DOOR}", "B", "밖", "전체"]
    return {key: {str(span): tally(*moves[key][span]) for span in SPANS if span in moves.get(key, {})}
            for key in order if key in moves}


def trading(rows, prices, shape, breadth, flows=None):
    """A그룹을 실제로 사고팔았다면. 89회차의 계좌(두 갈래 · 자리 5 · 하루 2)를 그대로 씁니다."""
    lo, hi = final_group.SPREAD
    inside = [r for r in rows if caps.inside(r, rule.TOP)]

    def aligned(row):
        form = form_of(shape, row)
        return (form.get("정배열") and form.get("간격") is not None and lo <= form["간격"] < hi
                and breadth.get(row["date"], 0) >= final_group.BREADTH)

    def flowing(row):
        got = flow_of(flows or {}, row)
        return final_group.flow_gap(got) is None

    def holds(row):
        # 두 갈래 가운데 하나 + 스승님 수급 조건(97회차)
        return (rule.holds(row) or aligned(row)) and flowing(row)

    def broken(lane, start, price, step, peak, row=None):
        spot = start + step
        close = lane["closes"][spot]
        if (close / price - 1) * 100 <= -8 or step >= 60:
            return True
        return not shape[lane["code"]]["정배열"][spot]

    tier = lambda r: "규칙" if rule.holds(r) else "정배열"
    exits = lab.exit_per_tier(tier, {"규칙": lab.exit_fixed(10, 5, 10), "정배열": broken})
    kin = rule.apart(prices)
    found = {}
    for label, since, until in HALVES:
        pool = [r for r in inside if r["date"] < until] if until else inside
        got = lab.wobble(pool, prices, holds, exits, tries=TRIES, rank=rule.order, slots=final_group.SLOTS,
                         since=since, per_day=2, apart=kin, realistic=True, cap=130)
        if got:
            found[label] = {k: got[k] for k in ("매매", "연수익", "폭", "최대낙폭", "골 폭", "승률", "평균",
                                                 "중앙", "보유중앙", "가동률", "연패", "해마다")}
    return found


def compute():
    prices = study.load_prices()
    rows = lab.load()
    if not rows:
        raise SystemExit("study/features.json이 없습니다. lab.build로 먼저 만드세요.")
    caps.tag(rows, rule.TOP)
    rule.calm_edge(rows)
    rows = [r for r in rows if r["date"] >= rule.SINCE]
    lanes = lab.lanes(prices)
    shape = shapes(lanes, {r["code"] for r in rows})
    breadth = breadth_by_day(rows, shape)
    flows = flow_index({r["code"] for r in rows})
    groups = group_table(rows, shape, breadth, flows)
    trades = trading(rows, prices, shape, breadth, flows)
    days = sorted({r["date"] for r in rows})
    return {"period": [days[0], days[-1]], "stocks": len({r["code"] for r in rows}),
            "observations": len(rows), "groups": groups, "trading": trades,
            "made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")}


def load(path=OUT):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


if __name__ == "__main__":
    got = compute()
    OUT.write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
    for key, spans in got["groups"].items():
        print(key, {s: (t or {}).get("상승확률") for s, t in spans.items()},
              {s: (t or {}).get("평균수익률") for s, t in spans.items()})
    for label, t in got["trading"].items():
        print(label, t["매매"], t["연수익"], t["최대낙폭"], t["승률"])
