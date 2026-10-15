"""MPOS-0014(HB · GPT H1): 1일봉 정배열 문 진입을 '회복 확인 뒤'로 바꾼 장부 만들기. 고정 나무(9743cb802) 엔진 lab.run을 그대로 쓰고
매수 조건(holds)만 이틀 밀어 씀(엔진 수정 없음 · brk_final 방식).
HB_MODE=IMM   : 원판(nrl.BASE_HOLD · BASE_SIZE · rule.order · BASE_EXIT) — 장부가 z055_d1_raw.json(sha 0ec97a14…)과 같아야 함.
HB_MODE=DELAY : 정배열 문 신호(t)를 t+2 종가에 삼(확인 없음 · 단순 지연 대조).
HB_MODE=CONFIRM: 정배열 문 신호(t) 뒤 t+1 종가 / t 종가 − 1 > HB_TH%(회복 확인 · t+1 종가로 확정) → t+2 종가에 삼(확인한 종가로 바로 체결하지 않음 · GPT #437).
HB_MODE=RAND  : DELAY 후보에서 C0가 버리는 몫만큼 고정 씨앗 동전으로 버림(무작위 버림 대조 · 대리 검토 1).
지연 경로(DELAY · CONFIRM · RAND) 공통: 사는 날(t+2) 종가 기준 정배열 유지(nrl.shape) — 같은 날 정배열이 깨져 판 종목을 다시 사는 헛매매를 막음(대리 검토 1).
공통: 규칙 문(rule.holds)은 원판 그대로 신호 날 종가에 삼(같은 종목이면 규칙 문이 먼저). 크기 · 순서 · 나가기 층은 신호 줄(t) 값으로.
미확인 · t+2 줄 없음(그날 100위 밖) → 그 신호는 버림(넘겨 기다리지 않음 · 다음 날 새 신호는 따로 봄).
t+2 날 판단에 쓰는 값: 신호 줄(t)의 값 · t · t+1 종가 · t+2 줄의 존재(100위 안) — t+2 종가 이후 값 안 씀(엔진의 상한가 건너뛰기는 원판과 같음).
cwd = 고정 나무 · tree_run으로 실행(바깥 코드 못 부름). 출력: HB_OUT(json 장부 [(코드, 산 날, 판 날, 손익, 자리)])."""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402

import random  # noqa: E402

MODE = os.environ["HB_MODE"]
assert MODE in ("IMM", "DELAY", "CONFIRM", "RAND")
GAP = int(os.environ.get("HB_GAP", "2"))       # 대리 검토 5: GAP=0이면 DELAY 경로가 원판과 같아야 함(재현 검사)
TH = float(os.environ.get("HB_TH", "0"))      # 확인 문턱(%): t+1 종가 / t 종가 − 1 > TH / 100
SEED = 20261016                               # RAND(무작위 버림 대조)의 고정 씨앗
LEAK = os.environ.get("HB_LEAK", "")           # 검사 도구 자체 시험 전용 · 실제 칸에는 쓰지 않음: "1" 다음 날 종가 · "R" 미래 종가 둘의 비율
POISON = os.environ.get("HB_POISON", "")      # 독 시험: 이 날 뒤 종가를 모두 0.7배로 바꾸고 이 날 뒤엔 새로 사지 않음
SIGTEST = os.environ.get("HB_SIGTEST") == "1"  # 신호 단위 접근 감사(엔진 없이 모든 줄): 판단이 읽는 종가 · 모양 · 줄 번호가 그 줄 날짜를 넘는지
PRICES = nrl.prices
if POISON:
    PRICES = {c: dict(b, rows=[(d, x * 0.7 if d > POISON else x) for d, x in b["rows"]]) for c, b in nrl.prices.items()}
LANE = lab.lanes(PRICES)              # lab.run과 같은 값 줄(r["i"]가 가리키는 줄)
AUDIT = {"now": 0, "max": -10 ** 9}


def _see(j):
    AUDIT["max"] = max(AUDIT["max"], j - AUDIT["now"])


def build(pool):
    rowmap = {(r["code"], r["i"]): r for r in pool}
    bad = [r for r in pool if LANE[r["code"]]["날"][r["i"]] != r["date"]]          # 대리 검토 참고 4: 모든 줄
    assert not bad, "줄 번호와 날짜가 안 맞음"

    def row_at(code, j):
        _see(j)
        return rowmap.get((code, j))

    def close(code, j):
        _see(j)
        return LANE[code]["closes"][j]

    def aligned_now(code, j):
        _see(j)
        return bool(nrl.shape[code]["정배열"][j])

    def delayed(r):
        """지연 경로 후보면 신호 줄(t), 아니면 None — 확인 · 무작위 버림 전 단계(t+2 날 정배열 유지 포함 · 대리 검토 1)."""
        s = row_at(r["code"], r["i"] - GAP)
        if s is None or not nrl.BASE_HOLD(s) or rule.holds(s):
            return None
        if not aligned_now(r["code"], r["i"]):          # 사는 날(t+2) 종가 기준 정배열 유지(원판이 신호 날 종가로 보는 것과 같은 시점)
            return None
        return s

    def confirmed(r):
        c0 = close(r["code"], r["i"] - GAP)
        if LEAK == "1":
            return close(r["code"], min(r["i"] + 1, len(LANE[r["code"]]["closes"]) - 1)) / c0 - 1 > TH / 100
        if LEAK == "R":
            n = len(LANE[r["code"]]["closes"]) - 1
            return close(r["code"], min(r["i"] + 2, n)) / close(r["code"], min(r["i"] + 1, n)) > 1
        return close(r["code"], r["i"] - 1) / c0 - 1 > TH / 100

    # RAND: 지연 후보 가운데 확인에 떨어지는 몫 p(이 반 전체에서 셈 · 대조 전용이라 전 기간 값을 씀)만큼 고정 씨앗 동전으로 버림
    P_DROP = None
    if MODE == "RAND":
        cand = [r for r in pool if not (nrl.BASE_HOLD(r) and rule.holds(r)) and delayed(r) is not None]
        P_DROP = sum(not confirmed(r) for r in cand) / max(1, len(cand))
        print("RAND 버림 몫", round(P_DROP, 4), "후보", len(cand), flush=True)

    def src(r):
        """이 줄(t+2)에서 산다면 그 크기 · 순서 · 나가기 층을 정하는 신호 줄. 같은 종목에서 규칙 문 즉시 신호가 먼저."""
        AUDIT["now"] = r["i"]
        if nrl.BASE_HOLD(r) and rule.holds(r):
            return r
        s = delayed(r)
        if s is None:
            return None
        if MODE == "CONFIRM" and not confirmed(r):
            return None
        if MODE == "RAND" and random.Random(f"{SEED}|{r['code']}|{r['i']}").random() < P_DROP:
            return None
        return s

    if SIGTEST:
        AUDIT["max"] = -10 ** 9
        n = sum(src(r) is not None for r in pool)
        return {"줄": len(pool), "산다고 본 줄": n, "판단이 읽은 가장 먼 앞날(줄 수)": AUDIT["max"]}

    holds = lambda r: src(r) is not None
    size = lambda r: nrl.BASE_SIZE(src(r) or r)
    rank = lambda r: rule.order(src(r) or r)
    tier = lambda r: "규칙" if rule.holds(src(r) or r) else "정배열"

    def half(first=5, take=13, stop=5, days=10):          # nrl.half_rule와 같은 판 · 반 칸 수만 신호 줄 기준
        def go(lane, start, price, step, peak, row=None):
            now = (lane["closes"][start + step] / price - 1) * 100
            if now >= take or now <= -stop or step >= days:
                return True
            if first and nrl.first_cross(lane, start, price, step, first):
                return max(1, nrl.BASE_SIZE(src(row) or row) // 2)
            return False
        return go
    exit_at = lab.exit_per_tier(tier, {"규칙": half(), "정배열": nrl.broken})
    return holds, size, rank, exit_at


if SIGTEST:
    out = {side: build(pool) for side, pool in (("앞", nrl.early), ("뒤", nrl.inside))}
    json.dump(out, open(os.environ["HB_OUT"], "w"), ensure_ascii=False)
    print(out)
    sys.exit(0)
rows = []
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    if MODE == "IMM":
        holds, size, rank, exit_at = nrl.BASE_HOLD, nrl.BASE_SIZE, rule.order, nrl.BASE_EXIT
    else:
        holds, size, rank, exit_at = build(pool)
    if POISON:                                    # 자른 날 뒤엔 새로 사지 않음(날은 계속 흘러 들고 있던 것은 독 값으로 나감)
        holds = (lambda h: lambda r: r["date"] <= POISON and h(r))(holds)
    g = lab.run(pool, PRICES, holds, exit_at, slots=nrl.SLOTS, rank=rank, since=since, apart=nrl.kin, realistic=True, cap=130,
                detail=True, size=size)
    got = (g or {}).get("매매목록") or []                 # 독 시험에서 자른 날 앞 반이면 뒤 반은 빈 판
    assert g or POISON, side
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in got]
    print(side, len(got), flush=True)
json.dump(rows, open(os.environ["HB_OUT"], "w"))
print("매매", len(rows))
