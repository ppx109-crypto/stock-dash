"""MPOS-0022(정배열 진입 쪽 · 사용자 2026-10-17 "다음방향 계속 진행해 · 승인 안 해도 계속 연구"): 1일봉 장부 만들기.
진단(research/attr_mix54): 바탕 손실 달의 주원인은 1일봉 정배열 갈래. GPT H3(동조화) · H1 변형(구간 안 늦은 진입).
고정 나무(9743cb802) 엔진 lab.run을 그대로 쓰고 정배열 갈래의 살 문만 덧씌움(규칙 갈래 · 크기 · 청산 · 순서 그대로 · 엔진 수정 없음).
EX_MODE=BASE : 원판 — 장부가 z055_d1_raw.json(sha 0ec97a14…)과 같아야 함.
EX_MODE=K    : 동조화 문 — 정배열 갈래 후보가 지금 들고 있는 종목들과의 평균 상관(판단 날 d의 전 거래일까지 60거래일 하루 수익 ·
               시작 · 끝 날이 같은 수익끼리만 맞춤 · 겹친 구간 40 미만 · 상수면 그 쌍 뺌) ≥ EX_TH 이면 사지 않음(들고 있는 종목 없으면 막지 않음). 기존 닮은 종목 문(nrl.kin)은 그대로 먼저.
EX_MODE=KR   : 참고 대조(고정 20% 확률 제외 · 기전 검증용 아님) — 같은 자리(정배열 후보 · 들고 있는 종목 있음)에서 (종목, 날) 지문 고정 난수 < EX_P 이면 사지 않음.
EX_MODE=L    : 늦은 구간 진입 막기 — 정배열 갈래는 그 종목 정배열이 이어진 날 수(진입 날 포함 · nrl.shape) ≤ EX_N 일 때만 삼.
EX_MODE=KLEAK: 검사 도구 자체 시험 — K 문의 상관 창이 d 뒤 5거래일까지(일부러 미래).
판단 값: K · KR · KLEAK는 d 전 거래일까지 종가(KLEAK만 예외) · L은 원판과 같은 nrl.shape(상속 캐시).
EX_POISON=날 · EX_CUTMODE=scale|drop: 그 날 뒤 종가 0.7배(scale) 또는 처음부터 지움(drop) · 그 날 뒤엔 새로 사지 않음.
감사: parts22(= parts21 + 동조화 도우미).HeldAudit(날짜 접근 · 보유 칸) · Entries(요청 · 배정 칸) · 문 접근(읽은 날 ≥ 판단 날)을 EX_OUT.audit.json에.
cwd = 고정 나무 · tree_run. 출력: EX_OUT(json 장부 [(코드, 산 날, 판 날, 손익, 자리)])."""
import hashlib
import json
import os
import sys
import types

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
from pathlib import Path  # noqa: E402

_C = Path(os.environ["NRL_CACHE"])
assert _C.exists() and _C.stat().st_mtime > lab.CACHE.stat().st_mtime, "nrl 캐시를 다시 구울 상황 → 중단"
import nrl  # noqa: E402
import rule  # noqa: E402
import final_study as F  # noqa: E402

_SRC = open(os.environ["EX_PARTS"], "rb").read()
PARTS_SHA = hashlib.sha256(_SRC).hexdigest()
parts = types.SimpleNamespace()
exec(compile(_SRC, os.environ["EX_PARTS"], "exec"), parts.__dict__)

MODE = os.environ["EX_MODE"]
assert MODE in ("BASE", "K", "KR", "L", "KLEAK")
TH = float(os.environ.get("EX_TH", "9"))
P_RAND = float(os.environ.get("EX_P", "0"))
NL = int(os.environ.get("EX_N", "0"))
POISON = os.environ.get("EX_POISON", "")
CUTMODE = os.environ.get("EX_CUTMODE", "scale")
assert CUTMODE in ("scale", "drop")
BACK, MIN_OVERLAP, AHEAD = 60, 40, 5


def poisoned(rows):
    if POISON and CUTMODE == "scale":
        return [(d, x * 0.7 if d > POISON else x) for d, x in rows]
    if POISON and CUTMODE == "drop":
        return [(d, x) for d, x in rows if d <= POISON]
    return rows


PRICES = nrl.prices
if POISON:
    PRICES = {c: dict(b, rows=poisoned(b["rows"])) for c, b in nrl.prices.items()}
    PRICES = {c: b for c, b in PRICES.items() if b["rows"]}
DATA_END = max(d for b in PRICES.values() for d, _ in b["rows"])
DAYS = {c: [d for d, _ in b["rows"]] for c, b in PRICES.items()}
CLOSE = {c: [x for _, x in b["rows"]] for c, b in PRICES.items()}
GATE = {"판단 수": 0, "막음": 0, "읽은 날 ≥ 판단 날": 0, "쌍 뺌(겹친 구간 모자람 · 상수)": 0, "구간 어긋나 뺀 수익": 0}
VALS = []      # (판단 날, 종목, 평균 상관 또는 None) — 실제 판단 순간의 모집단(문턱 진단 · 성과와 무관)


def rets(code, d):
    """d 전 거래일까지 BACK개 하루 수익(KLEAK는 d 뒤 AHEAD거래일까지 · 일부러 미래). 모자라면 None. 읽은 날을 감사."""
    ds, xs = DAYS.get(code), CLOSE.get(code)
    if not ds:
        return None
    r, last = parts.window(ds, xs, d, BACK, AHEAD if MODE == "KLEAK" else None)
    if last is not None and last >= d:
        GATE["읽은 날 ≥ 판단 날"] += 1
    return r


def mean_corr(row, held):
    ra = rets(row["code"], row["date"])
    if ra is None:
        return None
    cs = []
    for h in held:
        rb = rets(h["code"], row["date"])
        v = parts.corr(ra, rb, MIN_OVERLAP) if rb is not None else None
        if rb is not None:
            GATE["구간 어긋나 뺀 수익"] += parts.gap_pairs(ra, rb)
        if v is None:
            GATE["쌍 뺌(겹친 구간 모자람 · 상수)"] += 1
        else:
            cs.append(v)
    return sum(cs) / len(cs) if cs else None


def apart(row, held):
    if not nrl.kin(row, held):                         # 기존 닮은 종목 문 그대로 먼저
        return False
    if MODE not in ("K", "KR", "KLEAK") or nrl.tier(row) != "정배열" or not held:
        return True
    GATE["판단 수"] += 1
    if MODE == "KR":
        hit = parts.unit(row["code"], row["date"]) < P_RAND
    else:
        mc = mean_corr(row, held)
        VALS.append([row["date"], row["code"], mc])
        hit = mc is not None and mc >= TH
    GATE["막음"] += hit
    return not hit


def seg_days(r):
    """그 종목 정배열이 이어진 날 수(진입 날 포함 · nrl.shape 정배열 줄 · 그날까지 칸만)."""
    f = nrl.shape[r["code"]]["정배열"]
    i = r["i"]
    k = i
    while k - 1 >= 0 and f[k - 1]:
        k -= 1
    return i - k + 1


holds = nrl.BASE_HOLD
if MODE == "L":
    holds = lambda r: (rule.holds(r) or (nrl.aligned(r) and seg_days(r) <= NL)) and nrl.teacher(r) and not nrl.target_cut(r)   # noqa: E731

rows, audit = [], {}
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    h = holds
    if POISON:
        h = (lambda hh: lambda r: r["date"] <= POISON and hh(r))(holds)
    ex = parts.HeldAudit(nrl.BASE_EXIT, DATA_END)
    ent = parts.Entries(nrl.BASE_SIZE)
    g = lab.run(pool, PRICES, h, ex, slots=nrl.SLOTS, rank=rule.order, since=since, apart=apart, realistic=True, cap=130,
                detail=True, size=ent)
    got = (g or {}).get("매매목록") or []
    assert g or POISON, side
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in got]
    lane_of = {c: [d for d, _ in b["rows"]] for c, b in PRICES.items()}
    held = {(c, lane_of[c][i]): z for (c, i), z in ex.held.items()}
    seen = [e for e in ent.rows if (e[0], e[1]) in held]
    bad = [e for e in seen if held[(e[0], e[1])] != e[3]]
    audit[side] = dict(ex.receipt(), **{"문": dict(GATE), "자리일(들고 × 자리)": sum(t["들고"] * (t.get("자리") or 1) for t in got),
                                       "진입(종목 · 산 날 · 요청 칸 · 배정 칸)": ent.rows, "판단 순간 평균 상관": list(VALS),
                                       "배정 칸 대조": {"다음 날 보유 칸을 본 진입": len(seen), "배정 칸 ≠ 보유 칸": len(bad), "예": bad[:3]}})
    GATE.update({k: 0 for k in GATE})
    VALS.clear()
    print(side, len(got), flush=True)
json.dump(rows, open(os.environ["EX_OUT"], "w"))
json.dump({"부품 지문": PARTS_SHA, "자료 끝": DATA_END, "자르기": CUTMODE if POISON else "없음", **audit}, open(os.environ["EX_OUT"] + ".audit.json", "w"),
          ensure_ascii=False, indent=1)
print("매매", len(rows))
