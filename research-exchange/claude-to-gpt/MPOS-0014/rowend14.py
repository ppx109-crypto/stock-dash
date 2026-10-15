"""MPOS-0014 GPT #438 고칠 것 1 감사: 후보 줄은 뒤로 5거래일이 있어야 생김(lab.py:317). 판단 구간(2017-01 ~ 2026-08)에서 이 조건이 실제로 줄을 지우는지 셈.
종목 가격이 자료 끝보다 일찍 끝나는(상장폐지 · 거래 정지) 종목 가운데, 끝나기 전 5 ~ 7거래일 안에 그날 100위였을(시총 순위 줄 정보) 날이 있는지."""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402

L = lab.lanes(nrl.prices)
end = max(l["날"][-1] for l in L.values())
pool_codes = {r["code"] for r in nrl.inside} | {r["code"] for r in nrl.early}
early_end = {c: L[c]["날"][-1] for c in pool_codes if L[c]["날"][-1] < end}
last_row = {}
for pool in (nrl.early, nrl.inside):
    for r in pool:
        last_row[r["code"]] = max(last_row.get(r["code"], ""), r["date"])
out = {"자료 끝": end, "후보 풀 종목": len(pool_codes), "자료 끝보다 일찍 끝나는 후보 종목": len(early_end),
       "그 종목들": {c: {"가격 끝": early_end[c], "마지막 후보 줄": last_row.get(c), "값 줄 길이": len(L[c]["날"])} for c in sorted(early_end)}}
# 판단 구간 안에서 '뒤로 7줄 없음'으로 줄이 없어지는 날: 각 종목 값 줄 끝 7줄의 날짜 중 2026-08-31 이전
hit = {c: [d for d in L[c]["날"][-7:] if d <= "20260831"] for c in pool_codes}
out["판단 구간 안에서 끝 7줄에 걸리는 종목 · 날 수"] = {c: len(v) for c, v in hit.items() if v}
json.dump(out, open(os.environ["OUT"], "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "그 종목들"}, ensure_ascii=False)[:1500])
