"""MPOS-0009 진단(GPT #424 가설 A · B · 고르기 · 판정 없음): MPOS-0008 고정 장부를 다시 셈.
A: 장부 손익(왕복 0.25% 가정) vs 실제 비용(perf2 side_costs · 칸 금액) → 실제 비용 뒤 평균 · 혼자 계좌와 대조.
B: 신호 날 t 종가 → 산 날 b 종가(건너뛴 1일) · b → 판 날 e(보유) 수익을 나눠, 되돌림이 체결 전에 이미 소진되는지."""
import json, statistics as S, sys
from pathlib import Path
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
LED = SP / "mpos8" / "ledgers"
sys.path[:0] = [str(SP / "m54tree"), str(SP / "m54tree/research")]
import nrl, perf2 as P
px = {c: dict(v["rows"]) for c, v in nrl.prices.items()}
OLD_N, UNIT = 495, 1e8 * 0.5 / 10
def gross(r): return r[3] + 0.25
def one(name, rows, meta=None):
    sh = [r for r in rows if r[2] != "99999999"]
    rt = []
    for c, b, e, p, s in sh:
        bb, ss = P.side_costs(c, b, e, UNIT * s, 1.0)
        rt.append((bb + ss) * 100)
    g = [gross(r) for r in sh]
    net = [x - y for x, y in zip(g, rt)]
    out = dict(건=len(sh), 장부평균_0_25뺌=S.mean(r[3] for r in sh), 실제왕복비용평균=S.mean(rt), 실제비용뒤평균=S.mean(net),
               실제비용뒤_앞반=S.mean([n for n, r in zip(net, sh) if r[2] <= "20211231"] or [0]), 실제비용뒤_뒤반=S.mean([n for n, r in zip(net, sh) if r[2] > "20211231"] or [0]),
               금액가중_실제비용뒤=sum(n * r[4] for n, r in zip(net, sh)) / sum(r[4] for r in sh))
    if meta:
        gap, hold = [], []
        for m, r in zip(meta, rows):
            if r[2] == "99999999": continue
            t, b, e, c = m["신호 날"], r[1], r[2], r[0]
            if px[c].get(t) and px[c].get(b) and px[c].get(e):
                gap.append((px[c][b] / px[c][t] - 1) * 100); hold.append((px[c][e] / px[c][b] - 1) * 100)
        out.update(건너뛴1일_평균=S.mean(gap), 보유_평균=S.mean(hold), 건너뛴1일_양수비=sum(x > 0 for x in gap) / len(gap) * 100)
    return out
res = {}
res["P0 1일봉(495)"] = one("old", json.load(open(SP / "z055_d1_raw.json")))
for nm in ("g2_raw_K2.0_H10", "g2_rv_K2.0_H10", "g2_rv_K2.5_H10", "g2_noconf_K2.0_H10"):
    led = json.load(open(LED / f"{nm}.json"))[OLD_N:]
    meta = json.load(open(LED / f"{nm}.meta.json"))
    res[nm] = one(nm, led, meta)
print(json.dumps(res, ensure_ascii=False, indent=1))
json.dump(res, open(SP / "mpos9" / "diag9.json", "w"), ensure_ascii=False, indent=1)
