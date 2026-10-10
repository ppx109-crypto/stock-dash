"""D1-HALF-BREAKEVEN-0001 — 1일봉 '새 82' 추세 규칙(①)의 반익 뒤 본전 지키기(사전등록: research-exchange/claude-to-gpt/D1-HALF-BREAKEVEN-0001/PREREG.md).
판: V0 기준 · V1 반익 뒤 종가 ≤ 산 값이면 남은 절반 팜 · V2 반익 뒤 종가 < +1%면 남은 절반 팜. 다른 숫자 · 갈래는 그대로.
Z_STAGE=1: 앞 반(2017~2020)만 세 판 → 판정식으로 하나 고름(없으면 끝) · Z_STAGE=2: 고른 판과 V0의 뒤 반(2021~) + 계좌 손실 셈 + dguard 7 · 8겹.
'반익 뒤' = 산 날부터 어제까지 종가 가운데 +5% 이상이 있었음. 오늘 종가와 산 값만 씀(미래 자료 없음).
python3 research/z076.py   (Z_STAGE · Z_OUT 환경 변수)"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-HALF-BREAKEVEN-0001/evidence"))
FIRST, TAKE, STOP, DAYS = 5, 13, 5, 10          # 지금 추세 규칙 숫자(nrl.half_rule 기본값과 같음)


def half_be(floor_ok):
    """floor_ok(now) 가 참이면 반익 뒤 남은 절반을 팜. None이면 기준(V0)."""
    def go(lane, start, price, step, peak, row=None):
        c = lane["closes"]
        now = (c[start + step] / price - 1) * 100
        if now >= TAKE or now <= -STOP or step >= DAYS:
            return True
        if nrl.first_cross(lane, start, price, step, FIRST):
            return max(1, nrl.BASE_SIZE(row) // 2)
        if floor_ok is not None and max((c[start + k] / price - 1) * 100 for k in range(0, step)) >= FIRST and floor_ok(now):
            return True
        return False
    return go


VARIANTS = {
    "V0": half_be(None),
    "V1": half_be(lambda now: now <= 0.0),
    "V2": half_be(lambda now: now < 1.0),
}


def exits(name):
    return lab.exit_per_tier(nrl.tier, {"규칙": VARIANTS[name], "정배열": nrl.broken})


def side(name, which):
    pool, since = (nrl.early, rule.SINCE) if which == "앞" else (nrl.inside, rule.MID)
    g = lab.wobble(pool, nrl.prices, nrl.BASE_HOLD, exits(name), tries=8, slots=nrl.SLOTS, since=since,
                   apart=nrl.kin, realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE, rank=rule.order)
    s, a, b = nrl.luck(g, nrl.SLOTS, since)
    led = g["매매목록"]
    return {"매매": g["매매"], "연수익": g["연수익"], "폭": g["폭"], "골": g["최대낙폭"], "골폭": g["골 폭"], "가동률": g["가동률"],
            "승률": g["승률"], "단순": s, "행운뺌": a, "큰2건뺌": b, "해마다": g["해마다"], "account": account(led),
            "ledger_keys": sorted([t["code"], t["산 날"], t["판 날"], t["자리"], round(t["손익"], 4)] for t in led)}


def account(led):
    """씨앗 0번 매매목록 → 날마다 단순 계좌 손익(%) · 하루 최악 · 달력월 최악(PREREG 5절)."""
    day = defaultdict(float)
    for t in led:
        lane = nrl.lanes[t["code"]]
        d, c = lane["날"], lane["closes"]
        i0, i1 = d.index(t["산 날"]), d.index(t["판 날"])
        w = t["자리"] / nrl.SLOTS
        for j in range(i0 + 1, i1 + 1):
            day[d[j]] += (c[j] / c[j - 1] - 1) * 100 * w
        day[d[i1]] += (t["손익"] - (c[i1] / c[i0] - 1) * 100) * w
    month = defaultdict(float)
    for k, v in day.items():
        month[k[:6]] += v
    wd = min(day.items(), key=lambda kv: kv[1]) if day else (None, None)
    wm = min(month.items(), key=lambda kv: kv[1]) if month else (None, None)
    return {"worst_day": [wd[0], round(wd[1], 3) if wd[1] is not None else None],
            "worst_month": [wm[0], round(wm[1], 3) if wm[1] is not None else None], "days": len(day)}


def same_or_better(v, b):
    return v["연수익"] >= b["연수익"] - b["폭"] and v["골"] >= b["골"] - b["골폭"] and v["행운뺌"] >= b["행운뺌"] and v["큰2건뺌"] >= b["큰2건뺌"]


def improved(v, b):
    return v["연수익"] > b["연수익"] or v["골"] > b["골"]


def diff(b, v):
    kb, kv = {tuple(x) for x in b["ledger_keys"]}, {tuple(x) for x in v["ledger_keys"]}
    f = lambda xs: round(sum(x[4] * x[3] for x in xs) / nrl.SLOTS, 2)
    return {"기준에만": len(kb - kv), "기준에만_손익": f(kb - kv), "새로만": len(kv - kb), "새로만_손익": f(kv - kb)}


def brief(v):
    return {k: v[k] for k in ("매매", "연수익", "폭", "골", "골폭", "가동률", "승률", "단순", "행운뺌", "큰2건뺌", "account")}


def stage1():
    got = {n: side(n, "앞") for n in VARIANTS}
    b = got["V0"]
    judge = {n: {"S": same_or_better(got[n], b), "I": improved(got[n], b), "diff_vs_V0": diff(b, got[n])} for n in ("V1", "V2")}
    cands = [n for n in ("V1", "V2") if judge[n]["S"] and judge[n]["I"]]
    cands.sort(key=lambda n: (-got[n]["연수익"], -got[n]["골"], n))
    choice = cands[0] if cands else None
    out = {"stage": 1, "side": "앞(2017~2020)", "results": {n: brief(got[n]) for n in got}, "years": {n: got[n]["해마다"] for n in got},
           "judge": judge, "candidates": cands, "choice": choice}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stage1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for n in got:
        r = got[n]
        print(f"[앞] {n} 매매 {r['매매']} 연 {r['연수익']} (폭 {r['폭']}) 골 {r['골']} (골폭 {r['골폭']}) 가동 {r['가동률']} 승률 {r['승률']} "
              f"행운뺌 {r['행운뺌']} 큰2건뺌 {r['큰2건뺌']} 하루최악 {r['account']['worst_day']} 달최악 {r['account']['worst_month']}"
              + (f" · S {judge[n]['S']} I {judge[n]['I']} · {judge[n]['diff_vs_V0']}" if n in judge else ""), flush=True)
    print(f"[앞] 고른 판: {choice}", flush=True)
    return 0


def stage2():
    s1 = json.loads((OUT / "stage1.json").read_text())
    choice = s1["choice"]
    if not choice:
        print("앞 반 탈락 — 뒤 반 실행 안 함", flush=True)
        return 0
    got = {n: side(n, "뒤") for n in ("V0", choice)}
    b, v = got["V0"], got[choice]
    S, I = same_or_better(v, b), improved(v, b)
    acc_ok = all(x is not None and x > -15 for x in (v["account"]["worst_day"][1], v["account"]["worst_month"][1],
                                                     s1["results"][choice]["account"]["worst_day"][1], s1["results"][choice]["account"]["worst_month"][1]))
    import dguard  # noqa: E402  (7 · 8겹을 고른 판의 청산으로)
    keep = nrl.BASE_EXIT
    nrl.BASE_EXIT = exits(choice)
    try:
        before = len(dguard.FAILS)
        dguard.layer7()
        dguard.layer8()
        guard_ok = len(dguard.FAILS) == before
    finally:
        nrl.BASE_EXIT = keep
    if S and I and acc_ok and guard_ok:
        verdict = "ADOPT_CANDIDATE(사용자 결정)"
    elif S and not I:
        verdict = "SAME_NOT_ADOPTED(기준 유지)"
    else:
        verdict = "REJECTED"
    out = {"stage": 2, "side": "뒤(2021~)", "choice": choice, "results": {n: brief(got[n]) for n in got}, "years": {n: got[n]["해마다"] for n in got},
           "S": S, "I": I, "diff_vs_V0": diff(b, v), "account_ok_both_halves": acc_ok, "dguard_7_8_ok": guard_ok,
           "dguard_fails": dguard.FAILS, "verdict": verdict}
    (OUT / "stage2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for n in got:
        r = got[n]
        print(f"[뒤] {n} 매매 {r['매매']} 연 {r['연수익']} (폭 {r['폭']}) 골 {r['골']} (골폭 {r['골폭']}) 가동 {r['가동률']} 승률 {r['승률']} "
              f"행운뺌 {r['행운뺌']} 큰2건뺌 {r['큰2건뺌']} 하루최악 {r['account']['worst_day']} 달최악 {r['account']['worst_month']}", flush=True)
    print(f"[뒤] S {S} I {I} · {out['diff_vs_V0']} · 계좌 한도 {acc_ok} · dguard 7·8 {guard_ok} → {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(stage1() if os.environ.get("Z_STAGE", "1") == "1" else stage2())
