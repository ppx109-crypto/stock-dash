"""500종목이 채워지면 지금 규칙을 통째로 다시 재는 자리.

서른여덟 회차 동안 쌓은 결론은 거의 전부 200~250종목 위에서 나왔습니다.
게다가 그 종목들은 **오늘의** 시가총액으로 고른 것이라, 2016년에 100등
안이었다가 지금 작아진 회사는 아예 없습니다. 살아남은 것만 보는 쪽이라
성적이 실제보다 좋게 나옵니다.

종목이 두 배가 되면 그 치우침이 줄어듭니다. 그때 무엇을 다시 재야 하는지를
미리 적어 둡니다. 나중에 기억에 기대어 고르면 좋아 보이는 것만 고르게
됩니다.

    python recheck.py

앞뒤 구간(2015~2020 / 2021~)을 따로 내고, 매매 60건 미만이면 결론을 내지
않습니다. 무너지면 무너졌다고 그대로 찍습니다.
"""
from __future__ import annotations

import json
import sys

import caps
import guard
import lab
import rule
import study

FLOOR = 60          # 이보다 적으면 결론을 내지 않습니다


def halves(rows):
    return (("앞 2015~2020", [r for r in rows if r["date"] < rule.MID], rule.SINCE),
            ("뒤 2021~", rows, rule.MID))


def run(rows, prices, holds, kin, rank=None, take=rule.TAKE, stop=rule.STOP,
        limit=rule.LIMIT, slots=rule.SLOTS):
    found = {}
    for tag, use, since in halves(rows):
        got = lab.run(use, prices, holds, lab.exit_fixed(take, stop, limit),
                      slots=slots, rank=rank or rule.order, since=since,
                      per_day=rule.PER_DAY, apart=kin, realistic=True)
        if not got or got["매매"] < FLOOR:
            found[tag] = f"{got['매매'] if got else 0}건 — 결론 안 냄"
        else:
            found[tag] = {k: got[k] for k in
                          ("매매", "승률", "중앙", "최대낙폭", "연수익", "가동률")}
    return found


def say(tag, found):
    print(f"  {tag}")
    for half, got in found.items():
        print(f"    {half}: {json.dumps(got, ensure_ascii=False)}")


def calm_matters(rows, prices, kin):
    """조용함을 빼면 중앙 수익의 부호가 뒤집히는지. 서른 회차 동안 그랬습니다."""
    print("\n[1] 조용함 조건 — 빼면 부호가 뒤집히나")
    for tag, test in (("그대로", rule.holds),
                      ("조용함 뺌", lambda r: rule.holds_without(r, "calm"))):
        picks = [r for r in rows if test(r)
                 and r.get("ahead", {}).get(lab.HORIZON) is not None]
        vals = sorted(r["ahead"][lab.HORIZON] - lab.COST for r in picks)
        if len(vals) < FLOOR:
            print(f"  {tag}: {len(vals)}건 — 결론 안 냄")
            continue
        print(f"  {tag}: {len(vals)}건 · 중앙 {vals[len(vals) // 2]:+.2f} · "
              f"평균 {sum(vals) / len(vals):+.2f}")


def slope_hill(rows, prices, kin):
    """추세 기울기 문턱이 여전히 비탈인지. 꼭짓점이면 믿지 않습니다."""
    print("\n[2] 추세 기울기 문턱 — 비탈인가 꼭짓점인가")
    for edge in (1.1, 1.3, rule.SLOPE, 1.6, 1.8):
        def holds(row, e=edge):
            return (caps.inside(row, rule.TOP)
                    and (row.get("변동성") or 99) <= rule._calm
                    and (row.get("추세 기울기") or -99) >= e
                    and (row.get("60일 전 대비") or -99) >= rule.SIXTY)
        say(f"기울기 {edge}", run(rows, prices, holds, kin))


def width_gone(rows, prices, kin):
    """정배열폭을 덜어 낸 것이 500종목에서도 맞는지."""
    print("\n[3] 정배열폭 — 덜어 낸 것이 맞았나")
    say("덜어 낸 지금", run(rows, prices, rule.holds, kin))
    for edge in (4.0, 6.18, 8.0):
        def holds(row, e=edge):
            return rule.holds(row) and (row.get("정배열폭") or -99) >= e
        say(f"정배열폭 {edge} 다시 넣음", run(rows, prices, holds, kin))


def how_long(rows, prices, kin):
    """보유 10일이 여전히 이기는지."""
    print("\n[4] 보유 기간 — 10일이 여전히 이기나")
    for limit in (5, 10, 15, 20):
        say(f"{limit}일", run(rows, prices, rule.holds, kin, limit=limit))


def main():
    prices = study.load_prices()
    rows = lab.load()
    if not rows:
        print("특징표가 없습니다. guard.build_verified()로 먼저 만드세요.")
        return 1
    if not guard.verify(prices, rows, samples=25):
        print("미래참조 검사를 통과하지 못했습니다. 숫자를 내지 않습니다.")
        return 1
    caps.tag(rows, rule.TOP)
    rule.calm_edge(rows)
    kin = rule.apart(prices)
    print(f"종목 {len(prices)} · 행 {len(rows)} · 조용함 문턱 {rule._calm:.2f}")
    print("\n[0] 지금 규칙")
    say("네 조건", run(rows, prices, rule.holds, kin))
    calm_matters(rows, prices, kin)
    slope_hill(rows, prices, kin)
    width_gone(rows, prices, kin)
    how_long(rows, prices, kin)
    print("\n끝. 무너진 것이 있으면 RL-LOG에 무너졌다고 그대로 적습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
