"""MPOS-0025 감사 준비 셈(GPT #455 · 손익 안 봄 · 지금 고정 캐시로 셀 수 있는 것만 · 원자료 재생 아님).
H-CALM: rule._calm(받은 표 전체 · 2002 ~ 2026 모든 종목 · 날 변동성의 40% 자리 · 한 번)을 nrl.CALM_MONTH(그 달 첫날 앞 자료만)로 바꾸면
  rule.holds · BASE_HOLD · 갈래(규칙/정배열)가 몇 줄 뒤집히는지 · 원판 장부(0ec97a14…) 진입 줄 가운데 몇 줄이 뒤집히는 줄인지.
H-PRESENCE: 표(lab.build horizons=(5,10,20,60))는 줄마다 뒤 5개 가격 · 종목 전체 길이 > 180을 요구 →
  ① 종목마다 마지막 표 줄 날 대 마지막 가격 날의 차(바 수) ② 자료 끝 전에 가격이 끝난 종목(그 마지막 5바는 백테스트 안에서 미래 존재로 빠짐)
  ③ 가격은 있으나 줄이 하나도 없는 종목(길이 문턱). cwd = 고정 나무 · tree_run. 출력: EX_OUT."""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402

RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"
G = rule._calm
CM = nrl.CALM_MONTH or {}
rows = [r for r in nrl.inside if r["date"] >= rule.SINCE]


def with_calm(v, f, r):
    old = rule._calm
    rule._calm = v
    try:
        return f(r)
    finally:
        rule._calm = old


flip = {"holds": 0, "BASE_HOLD": 0, "BASE_HOLD 참 줄에서 갈래": 0, "달 문턱 없음": 0}
side = {"앞": {"holds": 0, "BASE_HOLD": 0}, "뒤": {"holds": 0, "BASE_HOLD": 0}}
flipped = set()
for r in rows:
    m = CM.get(r["date"][:6])
    if m is None:
        flip["달 문턱 없음"] += 1
        continue
    hg, hm = rule.holds(r), with_calm(m, rule.holds, r)
    bg, bm = nrl.BASE_HOLD(r), with_calm(m, nrl.BASE_HOLD, r)
    s = "앞" if r["date"] < rule.MID else "뒤"
    if hg != hm:
        flip["holds"] += 1
        side[s]["holds"] += 1
    if bg != bm:
        flip["BASE_HOLD"] += 1
        side[s]["BASE_HOLD"] += 1
        flipped.add((r["code"], r["date"]))
    if bg and bm and nrl.tier(r) != with_calm(m, nrl.tier, r):
        flip["BASE_HOLD 참 줄에서 갈래"] += 1
        flipped.add((r["code"], r["date"]))
# 원판 장부(엔진 다시 안 돌림 · 장부 파일 지문으로 확인)
led = json.load(open(os.environ["EX_LEDGER"]))
assert hashlib.sha256(json.dumps(led).encode()).hexdigest() == RAW_SHA
entries = {(c, b) for c, b, _, _, _ in [tuple(x) for x in led]}
months = sorted(CM)
cal = {"전체 문턱 G": G, "달 문턱 범위(SINCE ~)": [min(v for k, v in CM.items() if k >= rule.SINCE[:6]), max(v for k, v in CM.items() if k >= rule.SINCE[:6])],
       "달 문턱 > G인 달 · < G인 달": [sum(1 for k, v in CM.items() if k >= rule.SINCE[:6] and v > G), sum(1 for k, v in CM.items() if k >= rule.SINCE[:6] and v < G)]}
# H-PRESENCE
last_price = {c: b["rows"][-1][0] for c, b in nrl.prices.items() if b["rows"]}
gmax = max(last_price.values())
last_row = {}
for r in nrl.inside:
    if r["date"] > last_row.get(r["code"], ""):
        last_row[r["code"]] = r["date"]
gap = {}
for c, d in last_row.items():
    ds = [x for x, _ in nrl.prices[c]["rows"]]
    gap[c] = len(ds) - 1 - ds.index(d) if d in ds else None
stopped = sorted(c for c, d in last_price.items() if d < gmax and c in last_row)
stop_in = [c for c in stopped if last_price[c] >= rule.SINCE]
norows = sorted(c for c, b in nrl.prices.items() if c not in last_row and b["rows"] and b["rows"][-1][0] >= rule.SINCE)
from collections import Counter  # noqa: E402
out = {"장부 지문": RAW_SHA, "H-CALM": {"문턱": cal, "뒤집힌 줄(SINCE ~ · inside)": flip, "앞 · 뒤": side, "inside 줄": len(rows),
                                     "원판 진입(종목 · 산 날) 가운데 뒤집힌 줄": len(entries & flipped), "원판 진입 수": len(entries)},
       "H-PRESENCE": {"자료 끝(가격)": gmax, "마지막 표 줄 뒤 가격 바 수 분포": dict(Counter(gap.values()).most_common(8)),
                      "자료 끝 전에 가격이 끝난 종목(줄 있음)": len(stopped), "그중 끝이 SINCE 뒤": len(stop_in),
                      "그 종목들 마지막 가격 날(앞 10)": {c: last_price[c] for c in stop_in[:10]},
                      "가격은 SINCE 뒤까지 있으나 표 줄 없음(inside 기준)": len(norows)}}
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
