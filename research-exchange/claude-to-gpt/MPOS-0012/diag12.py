"""MPOS-0012 진단(키움 방식 부품 해부 · 고르기 · 판정 없음): 1일봉 495건을 문(규칙 · 정배열) · 칸 · 판단 전날 국면 · 같은 날 진입 수로 나눠
부품마다 건 · 추정 비용(perf2 · 500만 원 × 칸) 뒤 평균 · t · 앞(~2021) · 뒤(2022~) 평균 · P0 손실 달에 낸 몫(칸 가중 합)."""
import json, math, sys, statistics as S, collections
sys.path[:0] = ["research", "."]
import ntools as T, rule, perf2
SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos12/"
reg = json.load(open(SP + "regime.json")); st = reg["상태"]; p0 = reg["P0"]
ds = sorted(p0); mo = {}
for j in range(1, len(ds)):
    mo[ds[j][:6]] = mo.get(ds[j][:6], 1) * p0[ds[j]] / p0[ds[j - 1]]
loss_m = {m for m, v in mo.items() if v < 1 and "201703" <= m <= "202608"}
got = T.once("MPOS-0012 해부")
rows = []
for side in ("앞", "뒤"):
    for t in got[side]["매매목록"]:
        r = t["행"]; c, b, e, s = t["code"], t["산 날"], t["판 날"], int(t["자리"]) if t.get("자리") is not None else 1
        bb, ss = perf2.side_costs(c, b, e, 5e6 * s, 1.0)
        prev = [d for d in sorted(st) if d < b]
        rows.append(dict(c=c, b=b, e=e, s=s, net=float(float(t["손익"]) + 0.25 - float(bb + ss) * 100), door="규칙" if rule.holds(r) else "정배열",
                         reg=st[prev[-1]] if prev else "?", feat={k: r.get(k) for k in ("정배열일수", "단기이격", "중기이격", "기울기", "거래량비", "변동성", "시총순위") if k in r}))
same = collections.Counter(x["b"] for x in rows)
for x in rows:
    x["same"] = "같은날1" if same[x["b"]] == 1 else ("같은날2" if same[x["b"]] == 2 else "같은날3+")
def stat(xs):
    v = [x["net"] for x in xs]
    if len(v) < 2: return dict(건=len(v))
    m, sd = S.mean(v), S.stdev(v)
    f = [x["net"] for x in xs if x["e"] <= "20211231"]; bk = [x["net"] for x in xs if x["e"] > "20211231"]
    return dict(건=len(v), 평균=round(m, 3), t=round(m / (sd / math.sqrt(len(v))), 2), 승률=round(sum(a > 0 for a in v) / len(v) * 100, 1),
                앞=round(S.mean(f), 3) if f else None, 뒤=round(S.mean(bk), 3) if bk else None, 손실달몫=round(sum(x["net"] * x["s"] / 10 * 0.5 for x in xs if x["e"][:6] in loss_m), 2),
                믿을만=bool(len(v) >= 20 and m / (sd / math.sqrt(len(v))) >= 2 and (S.mean(f) if f else -1) > 0 and (S.mean(bk) if bk else -1) > 0))
out = {"전체": stat(rows)}
for key in ("door", "s", "reg", "same"):
    for val in sorted({str(x[key]) for x in rows}):
        out[f"{key}={val}"] = stat([x for x in rows if str(x[key]) == val])
for d in ("규칙", "정배열"):
    for rg in ("상승", "횡보", "하락"):
        out[f"{d}×{rg}"] = stat([x for x in rows if x["door"] == d and x["reg"] == rg])
print(json.dumps(out, ensure_ascii=False, indent=0))
json.dump({"부품": out, "매매": rows}, open(SP + "diag12.json", "w"), ensure_ascii=False)
