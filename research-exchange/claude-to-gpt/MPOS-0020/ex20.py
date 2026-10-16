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
EX_ALIGN=1: lab.run(align_days=True)로 같은 칸을 다시 돌림(대조 · 장부가 같아야 함).
EX_POISON=날: 그 날 뒤 종가를 모두 0.7배로 바꾸고 그 날 뒤엔 새로 사지 않음(자르기 시험 · 그날까지 장부가 같아야 함).
EX_MODE=LEAK2: 검사 도구 자체 시험 전용 — 모레 종가 < 내일 종가면 오늘 팜(미래 두 값의 비율만 봄 · GPT #446 §2).
EX_CUTMODE=scale(기본 · 그 날 뒤 종가 0.7배) | drop(그 날 뒤 종가 줄을 처음부터 지움 = 안 읽기 · I_CUT).
날짜 접근 감사(parts20.Audit): 모든 청산 판단을 감싸 '읽은 바 날 ≤ 판단 날' · '읽은 칸 ≤ 오늘 칸'을 세어 EX_OUT.audit.json에 씀(장부는 안 바뀜).
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
import hashlib  # noqa: E402
import types  # noqa: E402

# 부품 파일(parts20.py · lock.json에 지문)은 모듈로 불러오지 않고 원문을 읽어 실행(tree_run은 scratchpad 모듈을 막음) · 읽은 원문 지문을 감사 영수증에 적음
_SRC = open(os.environ["EX_PARTS"], "rb").read()
PARTS_SHA = hashlib.sha256(_SRC).hexdigest()
parts20 = types.SimpleNamespace()
exec(compile(_SRC, os.environ["EX_PARTS"], "exec"), parts20.__dict__)

MODE = os.environ["EX_MODE"]
assert MODE in ("IMM", "NP", "CH", "LEAK", "LEAK2")
N = int(os.environ.get("EX_N", "0"))
POISON = os.environ.get("EX_POISON", "")
ALIGN = os.environ.get("EX_ALIGN") == "1"   # 달력 정렬 대조(GPT #446 §2): 켜도 장부가 바이트까지 같아야 함(정지 · 결측 날 미래 종가 경로 없음)
PRICES = nrl.prices
CUTMODE = os.environ.get("EX_CUTMODE", "scale")
assert CUTMODE in ("scale", "drop")
if POISON and CUTMODE == "scale":
    PRICES = {c: dict(b, rows=[(d, x * 0.7 if d > POISON else x) for d, x in b["rows"]]) for c, b in nrl.prices.items()}
if POISON and CUTMODE == "drop":     # 그 날 뒤 종가 줄을 처음부터 안 읽음(그 날까지 줄이 없는 종목은 뺌)
    PRICES = {c: dict(b, rows=[(d, x) for d, x in b["rows"] if d <= POISON]) for c, b in nrl.prices.items()}
    PRICES = {c: b for c, b in PRICES.items() if b["rows"]}
DATA_END = max(d for b in PRICES.values() for d, _ in b["rows"])


WHY = {"정배열 갈래 판단": 0, "원판 조건(nrl.broken)으로 팜": 0, "더한 조건만으로 팜": 0}     # 기전 진단(보고 · GPT #446 §3)


def aligned_exit(lane, start, price, step, peak, row=None):
    WHY["정배열 갈래 판단"] += 1
    if nrl.broken(lane, start, price, step, peak, row):
        WHY["원판 조건(nrl.broken)으로 팜"] += 1
        return True
    if parts20.extra(MODE, N, lane, start, price, step, peak):
        WHY["더한 조건만으로 팜"] += 1
        return True
    return False


rows, audit = [], {}
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    holds = nrl.BASE_HOLD
    exit_at = nrl.BASE_EXIT if MODE == "IMM" else lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": aligned_exit})
    exit_at = parts20.Audit(exit_at, DATA_END)
    if POISON:
        holds = (lambda h: lambda r: r["date"] <= POISON and h(r))(holds)
    g = lab.run(pool, PRICES, holds, exit_at, slots=nrl.SLOTS, rank=rule.order, since=since, apart=nrl.kin, realistic=True, cap=130,
                detail=True, size=nrl.BASE_SIZE, **({"align_days": True} if ALIGN else {}))
    got = (g or {}).get("매매목록") or []
    assert g or POISON, side
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in got]
    audit[side] = dict(exit_at.receipt(), **{"청산 사유": dict(WHY), "자리일(들고 × 자리)": sum(t["들고"] * (t.get("자리") or 1) for t in got)})
    WHY.update({k: 0 for k in WHY})
    print(side, len(got), flush=True)
json.dump(rows, open(os.environ["EX_OUT"], "w"))
json.dump({"부품 지문": PARTS_SHA, "자료 끝": DATA_END, "자르기": CUTMODE if POISON else "없음", **audit}, open(os.environ["EX_OUT"] + ".audit.json", "w"), ensure_ascii=False, indent=1)
print("매매", len(rows))
