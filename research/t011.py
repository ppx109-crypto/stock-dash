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
python3 research/t011.py [판 ...]        (기본: S0 S1 S2 S3 — B는 evidence/B_reproduce.json으로 잠금)
- round 2(GPT #189 6095121561): 시작 때 캐시 · 표 sha256이 잠근 값과 다르면 셈 없이 멈춤 · 왕복 비용 0.25% 고정 ·
  판정(CORE_RETAINED / CORE_WEAK)을 코드가 직접 셈 — 엔진이 내는 소수 둘째 자리 값 그대로 · 비율 ≥ 0.5(같으면 통과)."""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
import lab  # noqa: E402

ROOT = Path("/home/user/stock-dash")
BOX = ROOT / "research-exchange/claude-to-gpt/D1-SIMPLE-0041"
LOCK = {"/tmp/nrl-cache.pkl": "CACHE_SHA", "study/features.json": "FEAT_SHA"}
CACHE_SHA = "4ec07fae1acb8ec516ee98befb89c25961171a78dc4d8b9e54a9a44f31cfda57"
FEAT_SHA = "9e5818196117059980750de779eebb28981971465cfc0875c9b6f9ca03e1a82e"
COST = 0.25         # 왕복 %(lab.COST와 같은 값을 호출에서 고정)
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
                       per_day=None, apart=nrl.kin, realistic=True, cap=130, detail=True, size=w["size"], cost=COST)
        if not g:
            res[side] = None
            continue
        s, a, b = nrl.luck(g, nrl.SLOTS, since)
        res[side] = {k: g.get(k) for k in ("매매", "연수익", "폭", "최대낙폭", "골 폭", "가동률", "승률", "보유중앙", "해마다")}
        res[side].update({"단순": s, "행운뺌": a, "큰2건뺌": b})
    return res


def lock_check():
    """캐시 · 표 내용 해시가 잠근 값과 같아야 셈을 시작함(다르면 멈춤)."""
    for path, key in LOCK.items():
        f = Path(path) if path.startswith("/") else ROOT / path
        h = hashlib.sha256()
        with f.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 24), b""):
                h.update(chunk)
        if h.hexdigest() != globals()[key]:
            sys.exit(f"자료 해시 다름 {path} — 셈하지 않음")


def label(b, s1):
    """S1 ÷ B — 앞 · 뒤 반 연수익 · 행운뺌 넷(엔진 출력 소수 둘째 자리 값 그대로 · ≥ 0.5 통과 · B ≤ 0이면 실패)."""
    checks = {}
    for side in ("앞", "뒤"):
        for k in ("연수익", "행운뺌"):
            bv, sv = (b.get(side) or {}).get(k), (s1.get(side) or {}).get(k)
            ratio = (sv / bv) if (bv and bv > 0 and sv is not None) else None
            checks[f"{side}_{k}"] = {"B": bv, "S1": sv, "ratio": None if ratio is None else round(ratio, 6),
                                     "pass": ratio is not None and ratio >= 0.5}
    lab_ = "CORE_RETAINED" if all(c["pass"] for c in checks.values()) else "CORE_WEAK"
    return checks, lab_


def main():
    lock_check()
    import nrl
    import rule
    ways = build(nrl)
    tags = sys.argv[1:] or ["S0", "S1", "S2", "S3"]
    out = {"task": "D1-SIMPLE-0041", "round": 2}
    for t in tags:
        t0 = time.time()
        out[t] = one(nrl, rule, ways[t])
        out[t]["초"] = round(time.time() - t0)
        print(t, json.dumps(out[t], ensure_ascii=False), file=sys.stderr, flush=True)
    if "S1" in out:
        b = out.get("B") or json.loads((BOX / "evidence/B_reproduce.json").read_text())["B"]
        out["B_source"] = "이번 실행" if "B" in out else "evidence/B_reproduce.json(잠금)"
        out["core_checks"], out["core_label"] = label(b, out["S1"])
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
