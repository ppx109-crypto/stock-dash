"""H-USD 주상품 · 대조 상품 고르기(GPT #455 3): 수익이 아닌 거래 가능성 기준 — 앞 기간(2017-02-01 ~ 2021-12-31) 원주가 자료의 하루 거래대금 가운데 값.
모집단(셈 전에 고정): 달러선물 1배 = 138230 · 261240 / 단기채 대조 = 153130 · 157450(etf-data 29개 가운데 이 두 무리에 드는 전부).
결측 처리: 거래대금 칸이 비거나 0인 날은 세고(보고) 가운데 값에서 뺌. 같은 무리에서 가운데 값이 큰 쪽을 고름.
입력: etf-ohlc/{코드}.json @ 51826765c(git show · 지문 기록). 출력: select_liquidity_out.json. 이 선택은 설계 단계의 사후 선택이며 독립 검증이 아님."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True, cwd=HERE).stdout.strip()   # git 경로는 저장소 뿌리 기준
OHLC = "51826765c"
GROUPS = {"달러선물 1배": ("138230", "261240"), "단기채 대조": ("153130", "157450")}
LO, HI = "20170201", "20211231"
out = {"기준": f"{LO} ~ {HI} 하루 거래대금(원) 가운데 값 · 원주가 자료", "입력 지문": {}, "무리": {}}
for g, codes in GROUPS.items():
    rows = {}
    for c in codes:
        raw = subprocess.run(["git", "show", f"{OHLC}:etf-ohlc/{c}.json"], capture_output=True, check=True, cwd=ROOT).stdout
        out["입력 지문"][f"{OHLC}:etf-ohlc/{c}.json"] = hashlib.sha256(raw).hexdigest()
        o = json.loads(raw)
        cols = o["columns"]
        k = cols.index("거래대금")
        span = [r for r in o["raw"] if LO <= r[0] <= HI]
        v = sorted(r[k] for r in span if r[k])
        rows[c] = {"날 수": len(span), "빈칸 · 0 날": len(span) - len(v), "가운데 거래대금(원)": v[len(v) // 2] if v else None,
                   "상장 첫날": o["raw"][0][0]}
    pick = max(codes, key=lambda c: rows[c]["가운데 거래대금(원)"] or -1)
    out["무리"][g] = {"종목": rows, "고름": pick}
json.dump(out, open(HERE / "select_liquidity_out.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out["무리"], ensure_ascii=False, indent=1))
