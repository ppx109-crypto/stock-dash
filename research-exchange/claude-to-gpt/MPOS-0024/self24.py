"""MPOS-0024 보조 장부 합성 시험(성과 출력 없음 · 가짜 자료만). 출력: self24_out.json. 끝 상태 0 = 모두 PASS."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sleeve import run_sleeve  # noqa: E402

out = {"행": []}


def check(name, ok, **info):
    out["행"].append({"시험": name, "판정": "PASS" if ok else "FAIL", **info})


def days(n, start=(2020, 1, 28)):
    y, m, d = start
    ds = []
    for _ in range(n):
        ds.append(f"{y}{m:02d}{d:02d}")
        d += 1
        if d > 28:
            d, m = 1, m + 1
            if m > 12:
                m, y = 1, y + 1
    return ds


# 1. GPT #455 반례: B=100 · slack 10 · 달 첫날 H=8 사들임(K=−8 근처) → 다음 날 slack 0 · 값 −10% → 다 팔아도 모자람 → 자금 불능
ds = ["20200131", "20200203", "20200204"]
base = [(ds[0], 100.0, 10.0), (ds[1], 100.0, 10.0), (ds[2], 100.0, 0.0)]
price = {ds[0]: 100.0, ds[1]: 100.0, ds[2]: 90.0}
r = run_sleeve(base, price, [], x=0.08, b=0.0, cost=0.0005)
H1, K1 = r["행"][1]["H"], r["행"][1]["K"]
expect_K = K1 + H1 * 0.9 * (1 - 0.0005)
check("GPT 반례: 다 팔아도 모자라면 FUNDING_INFEASIBLE(메우지 않음)", len(r["자금 불능 날"]) == 1 and r["자금 불능 날"][0]["날"] == ds[2]
      and abs(r["행"][2]["K"] - expect_K) < 1e-9 and r["행"][2]["q"] == 0.0, 날2_K=round(r["행"][2]["K"], 6), 기대=round(expect_K, 6),
      모자람=round(r["자금 불능 날"][0]["모자람"], 6) if r["자금 불능 날"] else None)
check("반례: 보유를 넘겨 팔지 않음(q ≥ 0)", all(x["q"] >= 0 for x in r["행"]))

# 2. 남는 현금 0이면 사지 않음 · 목표가 남는 현금 − b·B로 잘림
ds = days(40)
base = [(d, 1.0, 0.0) for d in ds]
price = {d: 10.0 for d in ds}
r = run_sleeve(base, price, [], x=0.2, b=0.02)
check("slack 0이면 사지 않음 · 계좌 = BASE", all(x["q"] == 0 and x["계좌"] == x["B"] for x in r["행"]) and not r["자금 불능 날"])
base = [(d, 1.0, 0.05) for d in ds]
r = run_sleeve(base, price, [], x=0.2, b=0.02)
first = next(x for x in r["행"] if x["q"] > 0)
check("목표 = min(x·B, (slack − b·B) ÷ (1+비용)) · 0.2 아닌 0.03 근처", abs(first["H"] - 0.03 / 1.0005) < 1e-12, H=first["H"])
r = run_sleeve([(d, 1.0, 0.01) for d in ds], price, [], x=0.2, b=0.02)
check("slack < b·B면 목표 0(음수 목표 없음)", all(x["q"] == 0 for x in r["행"]))

# 3. x = 0이면 거래 0 · 비용 0 · 계좌 = BASE(바이트)
r = run_sleeve([(d, 1.0 + i * 0.001, 0.3) for i, d in enumerate(ds)], price, [], x=0.0, b=0.02)
check("x = 0: 거래 · 비용 0 · 계좌 = B", r["회전"] == 0 and r["비용"] == 0 and all(x["계좌"] == x["B"] for x in r["행"]))

# 4. BASE 입력을 바꾸지 않음
base = [(d, 1.0, 0.3) for d in ds]
keep = copy.deepcopy(base)
run_sleeve(base, price, [], x=0.2, b=0.02)
check("BASE 입력 불변", base == keep)

# 5. 갑작스러운 BASE 현금 수요 → 억지 팔기로 메움(보유 안에서)
ds = ["20200131", "20200203", "20200204"]
base = [(ds[0], 1.0, 0.3), (ds[1], 1.0, 0.3), (ds[2], 1.0, 0.05)]
price = {d: 10.0 for d in ds}
r = run_sleeve(base, price, [], x=0.2, b=0.02)
check("BASE 현금 수요: 억지 팔기 1번 · 빚 없음", r["억지 팔기"] == 1 and not r["자금 불능 날"] and abs(r["행"][2]["slack"] + r["행"][2]["K"]) < 1e-9)

# 6. 거래 안 된 날 모자람 → 자금 불능(미루어 메우지 않음)
price = {ds[0]: 10.0, ds[1]: 10.0}
r = run_sleeve(base, price, [], x=0.2, b=0.02)
check("거래 안 된 날 모자람 = 자금 불능 · 마지막 값으로 평가", len(r["자금 불능 날"]) == 1 and r["자금 불능 날"][0]["값 있음"] is False
      and abs(r["행"][2]["H"] - r["행"][1]["H"]) < 1e-12)

# 7. 분배 권리: 전날 장 끝 수량 · 건별 · 지급일에만 현금
ds = days(70, (2020, 1, 27))
base = [(d, 1.0, 0.3) for d in ds]
price = {d: 10.0 for d in ds}
buy_day = next(d for i, d in enumerate(ds) if i > 0 and d[:6] != ds[i - 1][:6])          # 첫 맞춤 날
i0 = ds.index(buy_day)
ex1, pay1, ex2, pay2 = ds[i0 + 3], ds[i0 + 10], ds[i0 + 5], ds[i0 + 8]                    # 지급일이 거꾸로 겹치는 두 건
r = run_sleeve(base, price, [{"분배락": ex1, "지급일": pay1, "주당": 0.1}, {"분배락": ex2, "지급일": pay2, "주당": 0.2}], x=0.2, b=0.02)
R = {x["날"]: x for x in r["행"]}
q = R[buy_day]["q"]
check("분배락 날 받을 돈 = 전날 수량 × 주당 · 현금 아님", abs(R[ex1]["받을 분배"] - q * 0.1) < 1e-12 and R[ex1]["K"] == R[ds[i0 + 2]]["K"])
check("겹치는 두 건: 지급일 이른 건만 먼저 현금", abs(R[pay2]["받을 분배"] - q * 0.1) < 1e-12 and abs(R[pay2]["K"] - (R[buy_day]["K"] + q * 0.2)) < 1e-12)
check("나머지 건은 자기 지급일에", abs(R[pay1]["받을 분배"]) < 1e-15 and abs(R[pay1]["K"] - (R[buy_day]["K"] + q * 0.3)) < 1e-12)
# 분배락 날 새로 산 수량은 권리 없음
r = run_sleeve(base, price, [{"분배락": buy_day, "지급일": ds[i0 + 4], "주당": 0.1}], x=0.2, b=0.02)
check("분배락 날 새로 산 수량은 권리 없음", all(x["받을 분배"] == 0 for x in r["행"]))
# 분배락 날 판 수량은 권리 있음 + 지급 전 전량 청산해도 받을 돈 남음
nxt = next(d for i, d in enumerate(ds) if i > i0 and d[:6] != ds[i - 1][:6])              # 다음 달 첫날(맞춤)
i1 = ds.index(nxt)
base2 = [(d, 1.0, 0.3 if i < i1 else 0.0) for i, d in enumerate(ds)]                      # 다음 달 첫날부터 BASE가 현금을 다 씀 → 전량 팔기
r = run_sleeve(base2, price, [{"분배락": nxt, "지급일": ds[i1 + 3], "주당": 0.1}], x=0.2, b=0.02)
R = {x["날"]: x for x in r["행"]}
q0 = R[ds[i1 - 1]]["q"]
check("분배락 날 판 수량도 권리 · 지급 전 청산해도 받을 돈 남음", R[nxt]["q"] < q0 and abs(R[ds[i1 + 1]]["받을 분배"] - q0 * 0.1) < 1e-12)
# 받을 돈만 남은 날 모자람 → 자금 불능
check("받을 돈만 남고 현금 모자람 = 자금 불능", any(b_["날"] == ds[i1 + 1] and b_["받을 분배"] > 0 for b_ in r["자금 불능 날"]))

# 8. 자르기: 어느 날 뒤 값을 0.7배(P) · 지움(D)해도 그날까지 기록이 같음
ds = days(200)
import random  # noqa: E402
rnd = random.Random(3)
px, pv = {}, 10.0
for d in ds:
    pv *= 1 + rnd.gauss(0, 0.01)
    px[d] = pv
base = [(d, 1.0 + 0.0005 * i, max(0.0, 0.2 + 0.15 * rnd.gauss(0, 1))) for i, d in enumerate(ds)]
divs = [{"분배락": ds[50], "지급일": ds[55], "주당": 0.05}, {"분배락": ds[120], "지급일": ds[126], "주당": 0.05}]
full = run_sleeve(base, px, divs, x=0.2, b=0.02)["행"]
ok = True
for c in (ds[30], ds[90], ds[150]):
    for mode in ("P", "D"):
        p2 = {d: (v * 0.7 if d > c else v) for d, v in px.items()} if mode == "P" else {d: v for d, v in px.items() if d <= c}
        b2 = base if mode == "P" else [t for t in base if t[0] <= c]
        cut = run_sleeve(b2, p2, divs, x=0.2, b=0.02)["행"]
        ok &= [x for x in full if x["날"] <= c] == [x for x in cut if x["날"] <= c]
check("자르기 P(0.7배) · D(안 읽기) × 3날: 그날까지 기록 같음", ok)
# 누수 대조: 목표에 다음 날 값을 쓰면 잡혀야 함
leak_base = [(d, B, (base[i + 1][2] if i + 1 < len(base) else s)) for i, (d, B, s) in enumerate(base)]   # slack을 하루 앞당김(일부러 미래)
caught = 0
for c in (ds[30], ds[90], ds[150]):
    a = run_sleeve(leak_base, px, divs, x=0.2, b=0.02)["행"]
    lb2 = [(d, B, s) for d, B, s in leak_base if d <= c]
    lb2[-1] = (lb2[-1][0], lb2[-1][1], base[[t[0] for t in base].index(c)][2])               # 자른 자료에선 다음 날을 모름
    bcut = run_sleeve(lb2, px, divs, x=0.2, b=0.02)["행"]
    caught += [x for x in a if x["날"] <= c] != [x for x in bcut if x["날"] <= c]
check("누수 대조(남는 현금 하루 앞당김)는 자르기에서 잡힘(3날 중 1날 이상)", caught >= 1, 잡힘=caught)

# 9. 목표는 d−1 장 끝 값만: 맞춤 날 d의 남는 현금을 바꿔도(억지 팔기 안 생길 만큼) 그날 산 수량이 같아야 함
ds = days(40)
price = {d: 10.0 for d in ds}
base = [(d, 1.0, 0.15) for d in ds]
md = next(d for i, d in enumerate(ds) if i > 0 and d[:6] != ds[i - 1][:6])
base_b = [(d, B, 0.6 if d == md else s) for d, B, s in base]
qa = {x["날"]: x["q"] for x in run_sleeve(base, price, [], x=0.2, b=0.02)["행"]}
qb = {x["날"]: x["q"] for x in run_sleeve(base_b, price, [], x=0.2, b=0.02)["행"]}
check("목표는 전날 값만(맞춤 날 그날 slack을 바꿔도 산 수량 같음)", qa[md] == qb[md] and qa[md] > 0)

# 10. 거래 전후 총자산 차이 = 거래 비용(같은 값 날)
ds = days(40)
price = {d: 10.0 for d in ds}
r = run_sleeve([(d, 1.0, 0.3) for d in ds], price, [], x=0.2, b=0.02)
R = r["행"]
md = next(i for i, x in enumerate(R) if x["q"] > 0)
diff = R[md - 1]["계좌"] - R[md]["계좌"]
check("거래 전후 총자산 차이 = 산 금액 × 비용", abs(diff - R[md]["H"] * 0.0005) < 1e-15 and abs(r["비용"] - R[md]["H"] * 0.0005) < 1e-15,
      차이=diff, 기대=R[md]["H"] * 0.0005)

# 11. 분배: 권리 생성 · 지급은 외부 입금 아님 → 분배락 값이 정확히 D만큼 내리면 계좌 그대로 · 지급일도 그대로
ds = days(70, (2020, 1, 27))
D_ = 0.3
ex_i, pay_i = 40, 46
price = {d: (10.0 - D_ if i >= ex_i else 10.0) for i, d in enumerate(ds)}
r = run_sleeve([(d, 1.0, 0.3) for d in ds], price, [{"분배락": ds[ex_i], "지급일": ds[pay_i], "주당": D_}], x=0.2, b=0.02)
R = r["행"]
check("분배락: 값 −D · 받을 돈 +q·D → 계좌 변화 0", abs(R[ex_i]["계좌"] - R[ex_i - 1]["계좌"]) < 1e-15 and R[ex_i]["받을 분배"] > 0)
check("지급일: 받을 돈 → 현금 · 계좌 변화 0", abs(R[pay_i]["계좌"] - R[pay_i - 1]["계좌"]) < 1e-15 and R[pay_i]["받을 분배"] == 0)
# 같은 지급일 두 건
r = run_sleeve([(d, 1.0, 0.3) for d in ds], {d: 10.0 for d in ds},
               [{"분배락": ds[40], "지급일": ds[46], "주당": 0.1}, {"분배락": ds[42], "지급일": ds[46], "주당": 0.2}], x=0.2, b=0.02)
R = r["행"]
check("같은 지급일 두 건: 그날 둘 다 현금 · 전날까지 둘 다 받을 돈", abs(R[45]["받을 분배"] - R[39]["q"] * 0.3) < 1e-12 and R[46]["받을 분배"] == 0
      and abs(R[46]["K"] - R[45]["K"] - R[39]["q"] * 0.3) < 1e-12)

# 12. 자금 자격 FAIL 유지(뒤에 현금 회복돼도) · 실패 뒤 행은 진단 전용 표시
ds = ["20200131", "20200203", "20200204", "20200205", "20200206"]
base = [(ds[0], 100.0, 10.0), (ds[1], 100.0, 10.0), (ds[2], 100.0, 0.0), (ds[3], 100.0, 50.0), (ds[4], 100.0, 50.0)]
r = run_sleeve(base, {ds[0]: 100.0, ds[1]: 100.0, ds[2]: 90.0, ds[3]: 90.0, ds[4]: 90.0}, [], x=0.08, b=0.0)
check("합성 PASS ≠ 자격 PASS: 반례 경로 자금 자격 FAIL 유지 · 실패 뒤 '빚 허용 진단'", r["자금 자격"] == "FAIL" and r["첫 자금 불능 날"] == ds[2]
      and r["행"][4]["빚 허용 진단"] is True and r["행"][1]["빚 허용 진단"] is False and len(r["자금 불능 날"]) == 1)

# 13. 자르기에 BASE 미래 교란 · 자금 불능 경로 포함 · 다음 날 값 고의 누수
ds = days(200)
rnd = random.Random(5)
px, pv = {}, 10.0
for d in ds:
    pv *= 1 + rnd.gauss(0, 0.02)
    px[d] = pv
base = [(d, 1.0 + 0.0005 * i, (0.0 if i % 37 == 36 else max(0.0, 0.2 + 0.15 * rnd.gauss(0, 1)))) for i, d in enumerate(ds)]   # 가끔 slack 0 → 자금 불능 경로
divs = [{"분배락": ds[50], "지급일": ds[55], "주당": 0.05}, {"분배락": ds[120], "지급일": ds[126], "주당": 0.05}]
full = run_sleeve(base, px, divs, x=0.2, b=0.02)
ok, n_bad = True, len(full["자금 불능 날"])
for c in (ds[30], ds[90], ds[150]):
    for mode in ("P", "D"):
        if mode == "P":                                       # 값 · BASE(B · slack) · 분배를 c 뒤로 교란(c 당일 포함 안 바꿈)
            p2 = {d: (v * 0.7 if d > c else v) for d, v in px.items()}
            b2 = [(d, (B * 1.3 if d > c else B), (s * 0.1 if d > c else s)) for d, B, s in base]
            v2 = [dict(v, 주당=v["주당"] * 5) if v["분배락"] > c else v for v in divs]
        else:                                                 # c 뒤 자료를 처음부터 안 읽음(c 당일 포함)
            p2 = {d: v for d, v in px.items() if d <= c}
            b2 = [t for t in base if t[0] <= c]
            v2 = [v for v in divs if v["분배락"] <= c]
        cut = run_sleeve(b2, p2, v2, x=0.2, b=0.02)
        ok &= [x for x in full["행"] if x["날"] <= c] == [x for x in cut["행"] if x["날"] <= c]
        ok &= [x for x in full["자금 불능 날"] if x["날"] <= c] == [x for x in cut["자금 불능 날"] if x["날"] <= c]
check("자르기(값 · BASE · 분배 미래 교란 P / 안 읽기 D · c 당일 포함 · 3날): 상태 q · H · R · K · 자금 불능까지 같음", ok and n_bad > 0, 자금_불능_날=n_bad)


def leak_price(px):
    """고의 누수: 각 날 값 자리에 다음 날 값을 넣음(실제로 다음 날을 읽음)."""
    ks = sorted(px)
    return {k: px[ks[i + 1]] if i + 1 < len(ks) else px[k] for i, k in enumerate(ks)}


held = [x["날"] for x in full["행"] if x["q"] > 0]
cuts = [held[len(held) // 4], held[len(held) // 2], held[3 * len(held) // 4]]      # 보유 중인 날에서 자름(값이 실제로 쓰이는 날)
caught = 0
for c in cuts:
    a = run_sleeve(base, leak_price(px), divs, x=0.2, b=0.02)["행"]
    bcut = run_sleeve([t for t in base if t[0] <= c], leak_price({d: v for d, v in px.items() if d <= c}), divs, x=0.2, b=0.02)["행"]
    caught += [x for x in a if x["날"] <= c] != [x for x in bcut if x["날"] <= c]
check("고의 누수(다음 날 값을 읽음)는 보유 중인 자르기 3날 모두에서 잡힘", caught == 3, 잡힘=caught, 자른_날=cuts)

json.dump(out, open(HERE / "self24_out.json", "w"), ensure_ascii=False, indent=1)
for x in out["행"]:
    print(x["판정"], x["시험"])
print(sum(x["판정"] == "PASS" for x in out["행"]), "/", len(out["행"]))
sys.exit(0 if all(x["판정"] == "PASS" for x in out["행"]) else 3)
