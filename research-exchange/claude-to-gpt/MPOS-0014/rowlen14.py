"""감사 2: 종목 전체 길이 문턱(120 + max(horizons) = 180 · lab.build) — 가격이 121 ~ 185개인 종목은 줄이 하나도 없음(고친 조건이면 120번째부터 생김).
그런 종목의 120번째 날이 판단 구간(~ 2026-08-31) 안에 있는지 · 그 종목이 시총 상위였을지 단서(가격 파일 이름만)."""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402

L = lab.lanes(nrl.prices)
short = {c: {"길이": len(l["날"]), "120번째 날": l["날"][120], "끝": l["날"][-1]} for c, l in L.items() if 120 < len(l["날"]) <= 186}
inwin = {c: v for c, v in short.items() if v["120번째 날"] <= "20260831"}
pool_codes = {r["code"] for r in nrl.inside} | {r["code"] for r in nrl.early}
out = {"전체 종목": len(L), "길이 121 ~ 186 종목": len(short), "그중 120번째 날이 판단 구간 안": inwin,
       "그중 후보 풀(100위)에 한 번이라도 든 종목": sorted(set(inwin) & pool_codes)}
json.dump(out, open(os.environ["OUT"], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:2000])
