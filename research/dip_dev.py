"""DIP-DEEP-0042 개발 도구 — 2022-12-29 뒤 자료를 물리적으로 잘라 낸 1일봉 엔진(계획: research-exchange/claude-to-gpt/DIP-DEEP-0042/PLAN.md).
- 일봉(prices) · 표 줄(inside) · 수급(FLOW) · 시장 폭(BR) · 069500을 CUT까지로 잘라 새로 만들고, 어디에도 CUT 뒤 날짜가 없음을 assert로 확인.
- 표 줄의 'ahead' · 'met'(뒷날 결과 칸)은 지움.
- 개발 끝에 열린 매매는 마지막 날 종가에 판 것으로 셈(팔 조건 감싸기 · last_close).
- 엔진: lab.wobble(씨앗 8번 · 시총 100위 · 신호 날 종가 · realistic · 왕복 0.25% · cap 130) — 1일봉과 같음.
- round 2(GPT #192 6095347272): 시작 때 자료 해시 잠금(다르면 멈춤) · 평가 판 수 전체 상한 300(EVAL_LOG에 하나하나 적고 넘으면 멈춤) ·
  받아들이는 식 accept() · 잠금 기간(2022-12-30 ~)을 읽는 길은 이 파일에 없음.
쓰는 법: import dip_dev as D → D.evaluate(tag, holds, exits, size=..., rank=..., note=...) → {"D1": {...}, "D2": {...}}"""
import bisect
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
LOCK = {"/tmp/nrl-cache.pkl": "4ec07fae1acb8ec516ee98befb89c25961171a78dc4d8b9e54a9a44f31cfda57",
        "study/features.json": "9e5818196117059980750de779eebb28981971465cfc0875c9b6f9ca03e1a82e",
        "etf-ohlc/069500.json": "a29e65143fa1494ec8406fbb8893939720e6b2a90cbeb6801b75a6129b20d7de"}


def _lock_check():
    if os.getenv("DIP_SKIP_LOCK") == "sentinel-test-only":   # 합성 센티널 시험만(자료를 일부러 바꿔 넣음)
        return
    for path, want in LOCK.items():
        f = Path(path) if path.startswith("/") else ROOT / path
        h = hashlib.sha256()
        with f.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 24), b""):
                h.update(chunk)
        if h.hexdigest() != want:
            sys.exit(f"자료 해시 다름 {path} — 셈하지 않음")


_lock_check()
sys.path.insert(0, str(ROOT))
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402

CUT = "20221229"
D1 = ("20170102", "20191230")
D2 = ("20200102", "20221229")
COST, SLOTS, CAP = 0.25, 10, 130
EVAL_CAP = 300
EVAL_LOG = ROOT / "research-exchange/claude-to-gpt/DIP-DEEP-0042/evals.jsonl"

# ── 자료 자르기 ──────────────────────────────────────────────
prices = {c: {**b, "rows": [r for r in b["rows"] if r[0] <= CUT]} for c, b in nrl.prices.items()}
prices = {c: b for c, b in prices.items() if b["rows"]}
lanes = lab.lanes(prices)
rows = [{k: v for k, v in r.items() if k not in ("ahead", "met")} for r in nrl.inside if r["date"] <= CUT]
rows = [r for r in rows if r["code"] in lanes and r["i"] < len(lanes[r["code"]]["closes"])]
FLOW = {}
for code, (days, acc, ok, closes) in nrl.FLOW.items():
    k = bisect.bisect_right(days, CUT)
    FLOW[code] = (days[:k], {c: v[:k + 1] for c, v in acc.items()}, ok[:k + 1], closes[:k])
BR = {d: v for d, v in nrl.BR.items() if d <= CUT}
_ix = json.loads((ROOT / "etf-ohlc/069500.json").read_text())
_ix["raw"] = [x for x in _ix["raw"] if x[0] <= CUT]
IX = {x[0]: x[4] for x in _ix["raw"] if x[0] <= CUT}
IXD = sorted(IX)
kin = rule.apart(prices)


def _guard():
    assert max(r[0] for b in prices.values() for r in b["rows"]) <= CUT
    assert max(r["date"] for r in rows) <= CUT
    assert all(not d or d[-1] <= CUT for d, _, _, _ in FLOW.values())
    assert max(BR) <= CUT and IXD[-1] <= CUT
    assert all(len(l["날"]) == 0 or l["날"][-1] <= CUT for l in lanes.values())
    assert not any("ahead" in r or "met" in r for r in rows[:1000])


_guard()


# ── 부품(모두 그날까지 · 수급은 전날까지) ──────────────────────
def flow_sum(row, n, col, lag=1):
    got = FLOW.get(row["code"])
    if not got:
        return None
    days, acc, ok, _ = got
    k = bisect.bisect_left(days, row["date"]) - (lag - 1)
    if lag == 0:
        k = bisect.bisect_right(days, row["date"])
    lo = k - n
    if lo < 0 or ok[k] - ok[lo] < n:
        return None
    return acc[col][k] - acc[col][lo]


def ret(row, n):
    """그날 종가 ÷ n거래일 전 종가 − 1(%)."""
    c = lanes[row["code"]]["closes"]
    i = row["i"]
    return None if i < n else (c[i] / c[i - n] - 1) * 100


def ma_gap(row, n):
    c = lanes[row["code"]]["closes"]
    i = row["i"]
    if i < n - 1:
        return None
    return (c[i] / (sum(c[i - n + 1:i + 1]) / n) - 1) * 100


def ix_ret(day, n):
    """069500 원주가 그날까지 n거래일 수익(%)."""
    k = bisect.bisect_right(IXD, day) - 1
    if k < n:
        return None
    return (IX[IXD[k]] / IX[IXD[k - n]] - 1) * 100


def last_close(exit_at):
    """자료 끝(CUT) 칸에 오면 그날 종가에 팜 — 엔진이 열린 매매를 버리지 않게."""
    def go(lane, start, price, step, peak, row=None):
        if start + step >= len(lane["closes"]) - 1:
            return True
        return exit_at(lane, start, price, step, peak, row)
    return go


def fixed_exit(take, stop, days):
    def go(lane, start, price, step, peak, row=None):
        now = (lane["closes"][start + step] / price - 1) * 100
        return now >= take or now <= -stop or step >= days
    return go


# ── 돌리기 ───────────────────────────────────────────────────
KEYS = ("매매", "연수익", "폭", "최대낙폭", "골 폭", "가동률", "승률", "보유중앙", "해마다")


def run_way(holds, exits, size=lambda r: 2, rank=None, tries=8):
    out = {}
    for tag, (lo, hi) in (("D1", D1), ("D2", D2)):
        pool = [r for r in rows if lo <= r["date"] <= hi]
        g = lab.wobble(pool, prices, holds, last_close(exits), tries=tries, rank=rank or (lambda r: 0), slots=SLOTS,
                       since=lo, per_day=None, apart=kin, realistic=True, cap=CAP, detail=True, size=size, cost=COST)
        if not g:
            out[tag] = None
            continue
        s, a, b = nrl.luck(g, SLOTS, lo)
        out[tag] = {k: g.get(k) for k in KEYS}
        out[tag].update({"행운뺌": a, "큰2건뺌": b})
    return out


def _count():
    if not EVAL_LOG.exists():
        return 0
    return sum(1 for ln in EVAL_LOG.read_text(encoding="utf-8").splitlines() if ln.strip())


def evaluate(tag, holds, exits, size=lambda r: 2, rank=None, note=""):
    """평가 판 하나 = run_way 한 번(D1 · D2 함께). 진 것 · 다시 돌린 것까지 모두 EVAL_LOG에 한 줄씩. 300번째 뒤에는 멈춤."""
    n = _count()
    if n >= EVAL_CAP:
        sys.exit(f"평가 판 상한 {EVAL_CAP} 다 씀 — 더 셈하지 않음")
    res = run_way(holds, exits, size=size, rank=rank)
    rec = {"n": n + 1, "tag": tag, "note": note, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "res": res}
    with EVAL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return res


def accept(cand, inc, removal=False):
    """받아들이는 식(엔진 출력 소수 둘째 자리 값 그대로 · inc = 지금 채택판).
    보탬(removal=False): D1 · D2 각각 ① 매매 ≥ 60 ② 연수익 차 > max(두 판 폭) ③ 행운뺌 ≥ inc · 큰2건뺌 ≥ inc
      ④ 최대낙폭 ≥ inc 최대낙폭 − max(두 판 골 폭) — 넷 모두 두 토막에서.
    덜어냄(removal=True · 조건 빼기): D1 · D2 각각 ① 매매 ≥ 60 ② 연수익 차 ≥ −max(두 판 폭)
      ③ 행운뺌 ≥ inc − max(두 판 폭) · 큰2건뺌 ≥ inc − max(두 판 폭) ④ ④와 같음 — 같으면 단순한 쪽."""
    why = {}
    for h in ("D1", "D2"):
        c, i = cand.get(h), inc.get(h)
        if not c or not i:
            why[h] = "결과 없음(60건 미만)"
            continue
        w, g = max(c["폭"], i["폭"]), max(c["골 폭"], i["골 폭"])
        d = c["연수익"] - i["연수익"]
        ok = [c["매매"] >= 60, (d >= -w) if removal else (d > w),
              (c["행운뺌"] >= i["행운뺌"] - (w if removal else 0)) and (c["큰2건뺌"] >= i["큰2건뺌"] - (w if removal else 0)),
              c["최대낙폭"] >= i["최대낙폭"] - g]
        why[h] = ok
    passed = all(isinstance(v, list) and all(v) for v in why.values())
    return passed, why


def line(tag, res):
    parts = [f"{tag:28s}"]
    for k in ("D1", "D2"):
        x = res.get(k)
        parts.append(f"{k} 60건 미만" if not x else
                     f"{k} {x['매매']:>4}건 연 {x['연수익']:>6} (폭 {x['폭']:>5}) 골 {x['최대낙폭']:>6} 가동 {x['가동률']:>5} "
                     f"승 {x['승률']} 행운뺌 {x['행운뺌']} 큰2뺌 {x['큰2건뺌']}")
    return " | ".join(parts)
