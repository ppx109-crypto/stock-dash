"""D1-ROBUST-SLOPE-0002 — 1일봉 '새 82' 추세 규칙(①) 기울기를 더 긴 창으로 재면 덜 우연한가(사전등록: research-exchange/claude-to-gpt/D1-ROBUST-SLOPE-0002/PREREG.md).
판(모두 조용함 문턱은 '그 달 앞 자료로만' = nrl.CALM_MONTH):
  V0 기준: 180일 EMA 5거래일 기울기 ≥ 1.46%(표의 '추세 기울기'와 같음)
  V1: 180일 EMA 10거래일 기울기 ≥ (1.0146^2 − 1)%   V2: 180일 EMA 20거래일 기울기 ≥ (1.0146^4 − 1)%
이웃: 각 판 문턱 × 0.9 · × 1.0 · × 1.1. 튼튼함 R = 세 이웃 연수익(씨앗 가운데)의 가장 낮은 값.
순서(rule.order: 5일 기울기 순)와 그 밖 숫자 · 갈래는 그대로.
Z_STAGE=1: 앞 반(2017~2020) 세 판 × 세 이웃 + 참고(옛 전체 기간 조용함 문턱 V0) → 판정식으로 하나 고름(없으면 끝)
Z_STAGE=2: V0와 고른 판의 뒤 반(2021~) 세 이웃 + 계좌 손실 셈 + 자르기 시험(T까지만의 일봉으로 기울기도 다시 셈) + dguard 8겹.
기울기는 그날까지의 종가로만 셉니다(미래 자료 없음).
python3 research/z077.py   (Z_STAGE · Z_OUT 환경 변수)"""
import bisect
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
import caps  # noqa: E402
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-ROBUST-SLOPE-0002/evidence"))
BASE = rule.SLOPE                       # 1.46 (5거래일)
STEPS = {"V0": 5, "V1": 10, "V2": 20}
THRESH = {v: ((1 + BASE / 100) ** (n / 5) - 1) * 100 for v, n in STEPS.items()}   # V0는 정확히 1.46
NEIGH = (0.9, 1.0, 1.1)
FULL_CALM = rule._calm
ORIG_HOLDS = rule.holds

LANES = {"now": nrl.lanes}              # 자르기 시험에서 T까지만의 일봉으로 바꿈
_EMA = {}


def slope(r, step):
    """그날까지의 종가로 센 180일 EMA의 step거래일 기울기(%). step 5는 표의 '추세 기울기'와 같음(실행 전 점검: 3,000건 차 0)."""
    if step == 5:
        return r.get("추세 기울기")
    lanes = LANES["now"]
    code = r["code"]
    if code not in lanes:
        return None
    key = (id(lanes), code)
    if key not in _EMA:
        _EMA[key] = (lanes[code]["날"], lab.ema_series(lanes[code]["closes"], 180))
    days, e = _EMA[key]
    i = bisect.bisect_left(days, r["date"])
    if i >= len(days) or days[i] != r["date"] or i < step or e[i] is None or not e[i - step]:
        return None
    return (e[i] / e[i - step] - 1) * 100


def calm_past(r):
    """그 달 첫날 앞 자료로만 잰 조용함 문턱. 없는 달이면 멈춤(전체 기간 문턱으로 몰래 돌아가지 않음)."""
    return nrl.CALM_MONTH[r["date"][:6]]


def make_holds(step, thr, past_calm=True):
    def holds(r):
        if not caps.inside(r, rule.TOP):
            return False
        edge = calm_past(r) if past_calm else FULL_CALM
        if (r.get("변동성") or 99) > edge:
            return False
        s = slope(r, step)
        return s is not None and s >= thr and (r.get("60일 전 대비") or -99) >= rule.SIXTY
    return holds


class use:
    """rule.holds를 잠시 바꿈(nrl.BASE_HOLD · tier · BASE_SIZE · dguard가 모두 부를 때마다 rule.holds를 찾음)."""
    def __init__(self, fn):
        self.fn = fn

    def __enter__(self):
        rule.holds = self.fn

    def __exit__(self, *a):
        rule.holds = ORIG_HOLDS


def one(name, mult, which, past_calm=True):
    pool, since = (nrl.early, rule.SINCE) if which == "앞" else (nrl.inside, rule.MID)
    with use(make_holds(STEPS[name], THRESH[name] * mult, past_calm)):
        g = lab.wobble(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, tries=8, slots=nrl.SLOTS, since=since,
                       apart=nrl.kin, realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE, rank=rule.order)
        s, a, b = nrl.luck(g, nrl.SLOTS, since)
        led = g["매매목록"]
        trend_n = sum(1 for t in led if rule.holds(t["행"])) if led and "행" in led[0] else None
    return {"매매": g["매매"], "추세줄": trend_n, "연수익": g["연수익"], "폭": g["폭"], "골": g["최대낙폭"], "골폭": g["골 폭"],
            "가동률": g["가동률"], "승률": g["승률"], "단순": s, "행운뺌": a, "큰2건뺌": b, "해마다": g["해마다"],
            "account": account(led), "ledger_keys": sorted([t["code"], t["산 날"], t["판 날"], t["자리"], round(t["손익"], 4)] for t in led)}


def account(led):
    """씨앗 0번 매매목록 → 날마다 단순 계좌 손익(%) · 하루 최악 · 달력월 최악(z076과 같은 셈)."""
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


def grid(name, which):
    return {m: one(name, m, which) for m in NEIGH}


def R(gr):
    return min(gr[m]["연수익"] for m in NEIGH)


def diff(b, v):
    kb, kv = {tuple(x) for x in b["ledger_keys"]}, {tuple(x) for x in v["ledger_keys"]}
    f = lambda xs: round(sum(x[4] * x[3] for x in xs) / nrl.SLOTS, 2)
    return {"기준에만": len(kb - kv), "기준에만_손익": f(kb - kv), "새로만": len(kv - kb), "새로만_손익": f(kv - kb)}


def brief(v):
    return {k: v[k] for k in ("매매", "추세줄", "연수익", "폭", "골", "골폭", "가동률", "승률", "단순", "행운뺌", "큰2건뺌", "account")}


def train_ok(gv, g0):
    """PREREG 4절 1단계 조건 A1 ~ A4."""
    v, b = gv[1.0], g0[1.0]
    return {"A1_R": R(gv) > R(g0),
            "A2_center": v["연수익"] >= b["연수익"] - 2 * b["폭"],
            "A3_dd": v["골"] >= b["골"] - b["골폭"],
            "A4_luck": v["행운뺌"] >= b["행운뺌"] - b["폭"] and v["큰2건뺌"] >= b["큰2건뺌"] - b["폭"]}


def test_ok(gv, g0):
    """PREREG 4절 2단계 조건 T1 ~ T4."""
    v, b = gv[1.0], g0[1.0]
    return {"T1_center": v["연수익"] >= b["연수익"] - b["폭"],
            "T2_R": R(gv) >= R(g0) - b["폭"],
            "T3_dd": v["골"] >= b["골"] - b["골폭"],
            "T4_luck": v["행운뺌"] >= b["행운뺌"] - b["폭"] and v["큰2건뺌"] >= b["큰2건뺌"] - b["폭"]}


def say(tag, name, gr):
    for m in NEIGH:
        r = gr[m]
        print(f"[{tag}] {name} ×{m} 문턱 {THRESH[name] * m:.3f} 매매 {r['매매']}(추세 {r['추세줄']}) 연 {r['연수익']} (폭 {r['폭']}) 골 {r['골']} (골폭 {r['골폭']}) "
              f"행운뺌 {r['행운뺌']} 큰2건뺌 {r['큰2건뺌']} 하루최악 {r['account']['worst_day']} 달최악 {r['account']['worst_month']}", flush=True)
    print(f"[{tag}] {name} 튼튼함 R = {R(gr)}", flush=True)


def stage1():
    ref = one("V0", 1.0, "앞", past_calm=False)          # 참고만: 옛 전체 기간 조용함 문턱(RULESET 수치) — 판정에 안 씀
    print(f"[앞] 참고 V0(전체 기간 조용함 문턱) 연 {ref['연수익']} (폭 {ref['폭']}) 골 {ref['골']} 행운뺌 {ref['행운뺌']} 큰2건뺌 {ref['큰2건뺌']}", flush=True)
    got = {n: grid(n, "앞") for n in STEPS}
    for n in STEPS:
        say("앞", n, got[n])
    judge = {n: {**train_ok(got[n], got["V0"]), "diff_vs_V0": diff(got["V0"][1.0], got[n][1.0])} for n in ("V1", "V2")}
    for n in judge:
        judge[n]["pass"] = all(judge[n][k] for k in ("A1_R", "A2_center", "A3_dd", "A4_luck"))
    cands = [n for n in ("V1", "V2") if judge[n]["pass"]]
    cands.sort(key=lambda n: (-R(got[n]), -got[n][1.0]["연수익"], n))
    choice = cands[0] if cands else None
    out = {"stage": 1, "side": "앞(2017~2020)", "thresholds": THRESH, "reference_full_calm_V0": brief(ref),
           "results": {n: {str(m): brief(got[n][m]) for m in NEIGH} for n in got}, "R": {n: R(got[n]) for n in got},
           "years": {n: got[n][1.0]["해마다"] for n in got}, "judge": judge, "candidates": cands, "choice": choice}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stage1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for n in judge:
        print(f"[앞] {n} 판정 {({k: judge[n][k] for k in judge[n] if k != 'diff_vs_V0'})} · {judge[n]['diff_vs_V0']}", flush=True)
    print(f"[앞] 고른 판: {choice}", flush=True)
    return 0


def cut_check(name):
    """dguard 7겹과 같은 자르기 시험. 다만 T까지만의 일봉(lanes)으로 기울기도 다시 셈(dguard 7겹은 lanes를 바꾸지 않아 이 판의 새 셈을 못 봄)."""
    import dguard  # noqa: E402
    res = []
    for Tday, since in (("20190630", rule.SINCE), ("20231231", rule.MID), ("20250630", rule.MID)):
        with use(make_holds(STEPS[name], THRESH[name])):
            full = [t for t in dguard._ledger(nrl.prices, nrl.inside, nrl.kin, since) if t["판 날"] <= Tday]
            world = dguard._cut_world(Tday)
            saved = (nrl.shape, nrl.BR, nrl.FLOW, nrl.TARGETS, LANES["now"])
            try:
                nrl.shape, nrl.BR, nrl.FLOW, nrl.TARGETS = world[2], world[3], world[4], world[5]
                LANES["now"] = lab.lanes(world[0])
                cut = [t for t in dguard._ledger(world[0], world[1], world[6], since) if t["판 날"] <= Tday]
            finally:
                nrl.shape, nrl.BR, nrl.FLOW, nrl.TARGETS, LANES["now"] = saved
                _EMA.clear()          # 잘린 일봉으로 센 EMA를 남기지 않음
        key = lambda t: (t["code"], t["산 날"], t["판 날"], t["자리"], round(t["손익"], 6))
        a, b = sorted(map(key, full)), sorted(map(key, cut))
        res.append({"T": Tday, "full": len(a), "cut": len(b), "different": len(set(a) ^ set(b)), "ok": a == b and len(a) > 0})
    return res


def stage2():
    s1 = json.loads((OUT / "stage1.json").read_text())
    choice = s1["choice"]
    if not choice:
        print("앞 반 탈락 — 뒤 반 실행 안 함", flush=True)
        return 0
    got = {n: grid(n, "뒤") for n in ("V0", choice)}
    for n in got:
        say("뒤", n, got[n])
    t = test_ok(got[choice], got["V0"])
    acc = [got[choice][1.0]["account"]["worst_day"][1], got[choice][1.0]["account"]["worst_month"][1],
           s1["results"][choice]["1.0"]["account"]["worst_day"][1], s1["results"][choice]["1.0"]["account"]["worst_month"][1]]
    acc_ok = all(x is not None and x > -15 for x in acc)
    cuts = cut_check(choice)
    import dguard  # noqa: E402
    before = len(dguard.FAILS)
    with use(make_holds(STEPS[choice], THRESH[choice])):
        dguard.layer8()
    fill_ok = len(dguard.FAILS) == before
    guard_ok = all(c["ok"] for c in cuts) and fill_ok
    ok = all(t.values()) and acc_ok and guard_ok
    verdict = "ROBUST_CANDIDATE(사용자 결정 → 모의투자)" if ok else "REJECTED"
    out = {"stage": 2, "side": "뒤(2021~)", "choice": choice, "results": {n: {str(m): brief(got[n][m]) for m in NEIGH} for n in got},
           "R": {n: R(got[n]) for n in got}, "years": {n: got[n][1.0]["해마다"] for n in got}, "test": t,
           "diff_vs_V0": diff(got["V0"][1.0], got[choice][1.0]), "account_ok_both_halves": acc_ok, "cut_check": cuts,
           "fill_audit_ok": fill_ok, "dguard_fails": dguard.FAILS, "verdict": verdict}
    (OUT / "stage2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"[뒤] 판정 {t} · 계좌 한도 {acc_ok} · 자르기 {cuts} · 체결 감사 {fill_ok} → {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(stage1() if os.environ.get("Z_STAGE", "1") == "1" else stage2())
