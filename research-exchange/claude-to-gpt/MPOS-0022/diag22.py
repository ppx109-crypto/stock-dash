"""MPOS-0022 준비 진단(앞 기간 문턱 분위 포함)(성과 안 봄 · 건수 · 겹침 · 빠진 자료만 · GPT #446/#450 순서): 1일봉 원판 정배열 진입 402건에 대해
H1: 같은 정배열 구간(그 종목 정배열이 이어진 날들) 안에서 몇 번째 진입인지 · 구간 시작에서 며칠째 진입인지.
H3: 진입 날 들고 있던 종목들과의 평균 상관(진입 날까지 60거래일 하루 수익 · 두 종목 같은 날짜로 맞춤) 분포 · 빠짐.
기존 닮은 종목 문(rule.apart = lab.unlike: 쌍별 최대 상관 < 0.6 · 든 종목은 산 날 창)과 겹침: 새 평균 상관이 0.6을 넘는 건수(그 문이 이미 막았을 수 없는지 확인용).
cwd = 고정 나무 · tree_run. 출력: EX_OUT json."""
import bisect, json, os, sys
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402
t = [x for x in json.load(open(os.environ["TIERS"]))]
al = [x for x in t if x[5] == "정배열"]
days = {c: [d for d, _ in b["rows"]] for c, b in nrl.prices.items()}
closes = {c: [x for _, x in b["rows"]] for c, b in nrl.prices.items()}
out = {"정배열 진입": len(al)}
# H1
seg_n, seg_day, prev_trade_same_seg = {}, [], 0
seen = {}
for c, b, s, g, z, tier, h in sorted(al, key=lambda x: x[1]):
    i = days[c].index(b)
    f = nrl.shape[c]["정배열"]
    k = i
    while k - 1 >= 0 and f[k - 1]:
        k -= 1
    start = days[c][k]
    seg_day.append(i - k + 1)
    key = (c, start)
    seen[key] = seen.get(key, 0) + 1
    if seen[key] > 1:
        prev_trade_same_seg += 1
out["H1 같은 구간 안 두 번째 이상 진입"] = prev_trade_same_seg
out["H1 구간 시작에서 며칠째(진입 날 · 1 = 첫날) 분포"] = {f"{lo}~{hi}": sum(1 for x in seg_day if lo <= x <= hi) for lo, hi in ((1, 1), (2, 5), (6, 10), (11, 20), (21, 60), (61, 9999))}
out["H1 구간 진입 횟수 분포"] = {str(n): sum(1 for v in seen.values() if v == n) for n in sorted(set(seen.values()))}
# H3
def rets(c, d, back=60):
    ds, xs = days[c], closes[c]
    j = bisect.bisect_left(ds, d) - 1           # d 전 거래일까지(그날 종가 안 씀 · 기존 닮은 종목 문보다 하루 엄격)
    if j - back < 0:
        return None
    return {ds[q]: xs[q] / xs[q - 1] - 1 for q in range(j - back + 1, j + 1)}
def corr(a, b):
    ks = sorted(set(a) & set(b))
    if len(ks) < 40:
        return None
    x = [a[k] for k in ks]; y = [b[k] for k in ks]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    top = sum((p - mx) * (q - my) for p, q in zip(x, y))
    w = (sum((p - mx) ** 2 for p in x) ** 0.5) * (sum((q - my) ** 2 for q in y) ** 0.5)
    return top / w if w else None
held_all = [(x[0], x[1], x[2]) for x in t]          # 두 갈래 모두 보유
vals, empty, miss, FR = [], 0, 0, []
for c, b, s, g, z, tier, h in al:
    held = {hc for hc, hb, hs in held_all if hb < b <= hs and hc != c}
    if not held:
        empty += 1
        continue
    ra = rets(c, b)
    cs = [corr(ra, rets(o, b)) for o in held] if ra else []
    cs = [v for v in cs if v is not None]
    if not cs:
        miss += 1
        continue
    vals.append(sum(cs) / len(cs)); FR.append((b, sum(cs) / len(cs)))
vals.sort()
q = lambda p: round(vals[int(p * (len(vals) - 1))], 3)
out["H3 들고 있는 종목 없음(정의 안 됨)"] = empty
out["H3 자료 모자람(60일 · 겹친 날 40 미만)"] = miss
out["H3 평균 상관 셈한 진입"] = len(vals)
out["H3 평균 상관 분위(10 · 25 · 50 · 75 · 90%)"] = [q(.1), q(.25), q(.5), q(.75), q(.9)]
out["H3 평균 상관 ≥ 0.3 · 0.4 · 0.5 · 0.6 건수"] = [sum(1 for v in vals if v >= th) for th in (0.3, 0.4, 0.5, 0.6)]
fr = sorted(v for b, v in FR if b <= "20211231")
qf = lambda p: round(fr[int(p * (len(fr) - 1))], 4)
out["H3 앞 기간(산 날 ≤ 2021-12-31) 진입 수"] = len(fr)
out["H3 앞 기간 평균 상관 70 · 80 · 90% 분위(문턱 후보)"] = [qf(.7), qf(.8), qf(.9)]
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
