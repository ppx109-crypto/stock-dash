"""MPOS-0022 합성 시험: 동조화 문 도우미(parts22: 상관 창 · 상관 · 고정 난수)와 앞 기간 고르기. 성과 출력 없음. 출력: self_out.json."""
import json
import random
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.argv = [sys.argv[0]]
sys.path.insert(0, str(HERE))
import mpos22 as P  # noqa: E402

src = (HERE / "parts22.py").read_bytes()
Q = types.SimpleNamespace()
exec(compile(src, "parts22.py", "exec"), Q.__dict__)
out = {"행": []}


def check(name, ok, **info):
    out["행"].append({"시험": name, "판정": "PASS" if ok else "FAIL", **info})


ds = [f"2020{m:02d}{d:02d}" for m in range(1, 7) for d in range(1, 29)]
rnd = random.Random(7)
xs = [100.0]
for _ in ds[1:]:
    xs.append(xs[-1] * (1 + rnd.gauss(0, 0.02)))
d = ds[100]
w, last = Q.window(ds, xs, d, 60)
check("창은 판단 날 전 거래일까지(그날 종가 안 씀) · 열쇠 = (시작, 끝)", last == ds[99] and max(k[1] for k in w) == ds[99] and len(w) == 60 and (ds[98], ds[99]) in w)
w2, last2 = Q.window(ds, xs, d, 60, ahead=5)
check("누수 시험 창은 판단 날 뒤까지 읽음", last2 == ds[105] and last2 > d)
check("앞 자료 모자라면 None", Q.window(ds, xs, ds[30], 60) == (None, None))
a = {k: v for k, v in w.items()}
check("자기 자신과 상관 1", abs(Q.corr(a, a) - 1) < 1e-12)
check("부호 뒤집으면 상관 −1", abs(Q.corr(a, {k: -v for k, v in a.items()}) + 1) < 1e-12)
part = dict(list(a.items())[:39])
check("겹친 날 40 미만이면 None", Q.corr(a, part) is None)
shifted = {k: v for k, v in list(a.items())[5:]}
check("구간으로 맞춤(빠진 구간은 빼고 셈)", abs(Q.corr(a, shifted) - 1) < 1e-12)
# 결측 바: B는 ds[50] 바가 없음 → B의 (ds[49], ds[51]) 수익은 A의 (ds[50], ds[51])와 짝짓지 않음(GPT #453 3)
ds_b = [x for i, x in enumerate(ds) if i != 50]
xs_b = [x for i, x in enumerate(xs) if i != 50]
wb, _ = Q.window(ds_b, xs_b, d, 60)
wa, _ = Q.window(ds, xs, d, 60)
check("결측 바: 끝 날만 같고 시작 날 다른 수익은 짝 안 지음", (ds[49], ds[51]) in wb and (ds[50], ds[51]) in wa and Q.gap_pairs(wa, wb) == 1
      and abs(Q.corr(wa, wb) - 1) < 1e-12)
check("상수 수익열은 None", Q.corr(a, {k: 0.01 for k in a}) is None)
u = [Q.unit(f"{i:06d}", "20200102") for i in range(20000)]
check("고정 난수: 같은 입력 같은 값 · [0, 1)", Q.unit("005930", "20200102") == Q.unit("005930", "20200102") and min(u) >= 0 and max(u) < 1)
frac = sum(1 for x in u if x < 0.2) / len(u)
check("고정 난수 < 0.2 몫이 0.2 근처(±0.01)", abs(frac - 0.2) < 0.01, 몫=round(frac, 4))
# 앞 기간 고르기(반올림 없음 · 가까운 동률 · 완전 동률 고정 순서)
months = [f"{y}{m:02d}" for y in range(2017, 2027) for m in range(1, 13) if "201703" <= f"{y}{m:02d}" <= "202608"]
R = {c: {"달": {m: 0.0 for m in months}, "앞손실": 5, "뒤손실": 5} for c in P.CAND + ["BASE"]}
R["K80"]["달"]["201703"] += 1e-12
pick = P.front_pick(R)
check("앞 기간 고르기 · 가까운 동률이면 앞 반 연이 큰 칸", pick["K"]["고른 칸"] == "K80", 얻음=pick["K"]["고른 칸"])
check("앞 기간 고르기 · 완전 동률이면 고정 순서 첫 칸", pick["L"]["고른 칸"] == "L5")
json.dump(out, open(HERE / "self_out.json", "w"), ensure_ascii=False, indent=1)
print(sum(r["판정"] == "PASS" for r in out["행"]), "/", len(out["행"]))
sys.exit(0 if all(r["판정"] == "PASS" for r in out["행"]) else 3)
