"""MPOS-0020(키움 부품 → 1일봉 정배열 갈래 청산 · 사용자 2026-10-16 승인 '안 해 본 키움 부품 시험'): 장부 만들기.
고정 나무(9743cb802) 엔진 lab.run을 그대로 쓰고 나가기(exit_at)의 '정배열' 갈래에만 조건 하나를 더함(엔진 수정 없음).
살 때 · 크기 · 순서 · '규칙' 갈래 청산은 원판(nrl.BASE_HOLD · BASE_SIZE · rule.order · half_rule) 그대로.
EX_MODE=IMM : 원판 — 장부가 z055_d1_raw.json(sha 0ec97a14…)과 같아야 함(재현 검사).
EX_MODE=NP  : 원판 정배열 청산(nrl.broken) + '무익 N일' — 산 뒤 N거래일(step ≥ N)이 지났는데 그때까지 최고 종가가 산 값 이하
              (peak ≤ price · 한 번도 이익 종가가 없음)이면 그날 종가에 팜. 키움 추세봇 '무익 75분'을 일봉으로 옮김.
EX_MODE=CH  : 원판 정배열 청산 + 'N일 채널 저점' — 오늘 종가 < 오늘 앞 N거래일 종가의 최저(오늘 제외)이면 그날 종가에 팜.
              키움 추세봇 '채널 저점 이탈'을 일봉 종가로 옮김(일봉엔 저가 줄이 없어 종가 채널).
EX_MODE=LEAK: 검사 도구 자체 시험 전용 — 내일 종가 < 오늘 종가면 오늘 팜(일부러 미래를 봄 · 자르기 시험이 잡아야 함).
판단에 쓰는 값: 그날(spot)까지의 종가 · 산 값 · 그날까지 최고 종가(peak) — 그날 종가 뒤 값 안 씀(LEAK만 예외).
EX_POISON=날: 그 날 뒤 종가를 모두 0.7배로 바꾸고 그 날 뒤엔 새로 사지 않음(자르기 시험 · 그날까지 장부가 같아야 함).
cwd = 고정 나무 · tree_run으로 실행. 출력: EX_OUT(json 장부 [(코드, 산 날, 판 날, 손익, 자리)])."""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
from pathlib import Path  # noqa: E402

_C = Path(os.environ["NRL_CACHE"])
assert _C.exists() and _C.stat().st_mtime > lab.CACHE.stat().st_mtime, "nrl 캐시를 다시 구울 상황 → 중단"
import nrl  # noqa: E402
import rule  # noqa: E402

MODE = os.environ["EX_MODE"]
assert MODE in ("IMM", "NP", "CH", "LEAK")
N = int(os.environ.get("EX_N", "0"))
POISON = os.environ.get("EX_POISON", "")
PRICES = nrl.prices
if POISON:
    PRICES = {c: dict(b, rows=[(d, x * 0.7 if d > POISON else x) for d, x in b["rows"]]) for c, b in nrl.prices.items()}


def extra(lane, start, price, step, peak):
    spot = start + step
    c = lane["closes"]
    if MODE == "NP":
        return step >= N and peak <= price
    if MODE == "CH":
        return spot - N >= 0 and step >= 1 and c[spot] < min(c[spot - N:spot])
    if MODE == "LEAK":
        return spot + 1 < len(c) and c[spot + 1] < c[spot]
    return False


def aligned_exit(lane, start, price, step, peak, row=None):
    return nrl.broken(lane, start, price, step, peak, row) or extra(lane, start, price, step, peak)


rows = []
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    holds = nrl.BASE_HOLD
    exit_at = nrl.BASE_EXIT if MODE == "IMM" else lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": aligned_exit})
    if POISON:
        holds = (lambda h: lambda r: r["date"] <= POISON and h(r))(holds)
    g = lab.run(pool, PRICES, holds, exit_at, slots=nrl.SLOTS, rank=rule.order, since=since, apart=nrl.kin, realistic=True, cap=130,
                detail=True, size=nrl.BASE_SIZE)
    got = (g or {}).get("매매목록") or []
    assert g or POISON, side
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in got]
    print(side, len(got), flush=True)
json.dump(rows, open(os.environ["EX_OUT"], "w"))
print("매매", len(rows))
