"""D1-SIMPLE-0041 — 1일봉 '쉬운 판' 대 지금 판(사용자 2026-10-10 "이것도 진행해줘").
사전등록: research-exchange/claude-to-gpt/D1-SIMPLE-0041/PREREG.md
- 셈 엔진은 지금 1일봉과 같음(nrl · lab.wobble · 씨앗 8번 가운데값 · 시총 100위 안 · 신호 날 종가에 삼 · 같이 움직이던 종목 안 담음 ·
  순서 rule.order · 계좌 10칸 · realistic · cap 130). 바꾸는 것은 '살 조건 · 팔 조건 · 담는 칸'뿐.
- 판(5개 · 숫자 고정):
  B  지금 판(nrl.BASE_HOLD · BASE_EXIT · BASE_SIZE) — 기준 재현
  S1 쉬운 판: 지수이동평균 5 > 20 > 60 > 120(정배열) + 전날까지 5일 외국인 순매수 > 0 · 투신 > 0 · 개인 < 0 → 2칸(20%) ·
     정배열이 깨지는 날 종가에 팖(다른 팔 조건 없음)
  S0 S1에서 수급 조건을 뺌(정배열만) — 수급이 쉬운 판에서 얼마를 더하는지
  S2 S1 + 손절 −10%(지금 판 정배열 길의 손절 숫자 그대로)
  S3 S1 + 시장 폭 ≥ 50(지금 판 정배열 길의 시장 거르기 그대로)
python3 research/t011.py [판 ...]        (기본: 다섯 판 모두)"""
import json
import sys
import time

sys.path.insert(0, "/home/user/stock-dash")
import lab  # noqa: E402

SPANS = (5, 20, 60, 120)
STOP, SIZE = -10.0, 2
WARM = 250          # 지금 판 정배열과 같은 앞 250칸은 신호 없음


def aligned_list(closes):
    """칸별 '지수이동평균 5 > 20 > 60 > 120' 여부 — 칸 i는 closes[:i+1]만 씀(앞 WARM칸은 False)."""
    m = [lab.ema_series(closes, s) for s in SPANS]
    ok = []
    for i in range(len(closes)):
        v = [x[i] for x in m]
        ok.append(i >= WARM and None not in v and all(v[k] > v[k + 1] for k in range(len(v) - 1)))
    return ok


def exit_rule(ema, stop=None):
    """정배열이 깨지는 날 종가에 팖(stop이 있으면 종가 손익 ≤ stop%도 팖)."""
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        if stop is not None and (lane["closes"][spot] / price - 1) * 100 <= stop:
            return True
        return not ema[lane["code"]][spot]
    return go


def build(nrl):
    ema = {code: aligned_list(lane["closes"]) for code, lane in nrl.lanes.items()}

    def on(r):
        got = ema.get(r["code"])
        return bool(got and r["i"] < len(got) and got[r["i"]])

    two = lambda r: SIZE
    return {
        "B": dict(holds=nrl.BASE_HOLD, exits=nrl.BASE_EXIT, size=nrl.BASE_SIZE),
        "S1": dict(holds=lambda r: on(r) and nrl.teacher(r), exits=exit_rule(ema), size=two),
        "S0": dict(holds=on, exits=exit_rule(ema), size=two),
        "S2": dict(holds=lambda r: on(r) and nrl.teacher(r), exits=exit_rule(ema, STOP), size=two),
        "S3": dict(holds=lambda r: on(r) and nrl.teacher(r) and nrl.BR.get(r["date"], 0) >= 50, exits=exit_rule(ema), size=two),
    }


def one(nrl, rule, w):
    res = {}
    for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
        g = lab.wobble(pool, nrl.prices, w["holds"], w["exits"], tries=8, rank=rule.order, slots=nrl.SLOTS, since=since,
                       per_day=None, apart=nrl.kin, realistic=True, cap=130, detail=True, size=w["size"])
        if not g:
            res[side] = None
            continue
        s, a, b = nrl.luck(g, nrl.SLOTS, since)
        res[side] = {k: g.get(k) for k in ("매매", "연수익", "폭", "최대낙폭", "골 폭", "가동률", "승률", "보유중앙", "해마다")}
        res[side].update({"단순": s, "행운뺌": a, "큰2건뺌": b})
    return res


def main():
    import nrl
    import rule
    ways = build(nrl)
    tags = sys.argv[1:] or list(ways)
    out = {"task": "D1-SIMPLE-0041", "round": 1}
    for t in tags:
        t0 = time.time()
        out[t] = one(nrl, rule, ways[t])
        out[t]["초"] = round(time.time() - t0)
        print(t, json.dumps(out[t], ensure_ascii=False), file=sys.stderr, flush=True)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
