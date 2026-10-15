"""MPOS-0014 결과 보고 더하기(GPT #438 요청 · 판정에 안 씀): 실제 진입 수(종목 + 산 날) · 자리일 · 비용 누계 · 놓친 IMM 정배열 진입.
놓친 진입 = IMM 진입(종목 + 산 날 b) 가운데 그 칸에 같은 종목 진입이 b ~ b+3거래일 안에 없는 것 · 그 IMM 줄 손익(왕복 0.25% 뒤)의 합 · 이긴 수."""
import csv
import json
from pathlib import Path

HERE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos14")
CELLS = ["IMM", "DELAY", "RAND", "C0", "CM1", "CP1"]
days = [r["날"] for r in csv.DictReader(open(HERE / "base_IMM.csv"))]
ix = {d: i for i, d in enumerate(days)}
led = {c: json.load(open(HERE / f"led_{c}.json")) for c in CELLS}


def entries(rows):
    e = {}
    for c, b, x, p, s in rows:
        k = (c, b)
        e.setdefault(k, [0, 0.0, 0])
        e[k][0] += s
        e[k][1] += p * s
        e[k][2] = max(e[k][2], ix.get(x, len(days)) - ix.get(b, 0))
    return e


out = {}
E = {c: entries(led[c]) for c in CELLS}
for c in CELLS:
    rows = led[c]
    slotdays = sum(s * (ix.get(x, len(days)) - ix.get(b, 0)) for _, b, x, _, s in rows)
    cost = float(list(csv.DictReader(open(HERE / f"base_{c}.csv")))[-1]["비용누계"])
    have = {}
    for (code, b) in E[c]:
        have.setdefault(code, []).append(ix.get(b, -99))
    miss = [(k, v) for k, v in E["IMM"].items() if not any(0 <= j - ix.get(k[1], -99) <= 3 for j in have.get(k[0], []))]
    out[c] = {"청산 줄": len(rows), "실제 진입(종목 + 산 날)": len(E[c]), "자리일(자리 × 거래일)": slotdays,
              "바탕 비용 누계(빌드 전체 구간 · 원)": round(cost),
              "IMM 진입 중 놓친 수": len(miss), "놓친 진입의 이긴 수": sum(v[1] > 0 for _, v in miss),
              "놓친 진입 손익 합(자리 가중 % · IMM 줄)": round(sum(v[1] for _, v in miss), 1)}
json.dump(out, open(HERE / "extra14.json", "w"), ensure_ascii=False, indent=1)
for c, v in out.items():
    print(c, json.dumps(v, ensure_ascii=False))
