"""MPOS-0020 합성 시험(GPT #446 §2): 고정 나무의 진짜 lab.run을 작은 가짜 자료로 돌려 날짜 접근 감사(parts20.Audit)가
① 정지 · 결측 날 다음 바 앞당겨 읽기를 잡는지(기본 경로 = 잡혀야 함 · align_days=True = 0)
② 다음 칸 읽기(LEAK · LEAK2)를 잡는지 ③ 줄 끝 사라짐을 세는지 ④ NP · CH 경계(N−1/N · 같은 최저/엄격 이탈 · 앞 N칸 모자람 · 결측 날 뜻)를 확인.
cwd = 고정 나무 · tree_run으로 실행. 출력: EX_OUT(json 영수증)."""
import hashlib
import json
import os
import sys
import types

sys.path.insert(0, os.getcwd())
import lab  # noqa: E402

_SRC = open(os.environ["EX_PARTS"], "rb").read()
P = types.SimpleNamespace()
exec(compile(_SRC, os.environ["EX_PARTS"], "exec"), P.__dict__)
out = {"부품 지문": hashlib.sha256(_SRC).hexdigest(), "행": []}


def check(name, ok, **info):
    out["행"].append({"시험": name, "판정": "PASS" if ok else "FAIL", **info})


def prices(**lanes):
    return {c: {"rows": rows} for c, rows in lanes.items()}


def run(px, buys, fn, align=False):
    a = P.Audit(fn, max(d for b in px.values() for d, _ in b["rows"]))
    rows = [{"date": d, "code": c, "i": [x for x, _ in px[c]["rows"]].index(d)} for c, d in buys]
    # 엔진은 후보 줄의 마지막 날까지만 돎 → 자료 끝 날에 사지 않는 빈 줄(종목 '끝')을 하나 둠
    rows.append({"date": a.data_end, "code": "끝", "i": 0})
    lab._lanes_for = lab._days_for = None
    lab.run(rows, px, lambda r: r["code"] != "끝", a, slots=3, detail=True, **({"align_days": True} if align else {}))
    return a.receipt()


never = lambda *a: False      # noqa: E731
FULL = [("20200102", 100.0), ("20200103", 100.0), ("20200106", 100.0), ("20200107", 100.0), ("20200108", 100.0)]

# ① 결측 날: A는 01-03 바 없음 · B는 모든 날. A를 01-02에 삼.
px = prices(A=[("20200102", 100.0), ("20200106", 90.0), ("20200107", 95.0), ("20200108", 96.0)], B=FULL)
r0 = run(px, [("A", "20200102")], never)
r1 = run(px, [("A", "20200102")], never, align=True)
check("결측 날 · 기본 경로는 미래 바로 잡힘", r0["미래 바(오늘 바 날 > 판단 날)"] >= 1, 기본=r0["미래 바(오늘 바 날 > 판단 날)"], 예=r0["미래 바 예"][:1])
check("결측 날 · align_days=True는 미래 바 0", r1["미래 바(오늘 바 날 > 판단 날)"] == 0 and r1["판단 수"] >= 1, 정렬=r1["미래 바(오늘 바 날 > 판단 날)"])
# 결측 없는 자료는 기본 경로도 0
r2 = run(prices(A=FULL, B=FULL), [("A", "20200102")], never)
check("결측 없음 · 기본 경로 미래 바 0 · 미래 칸 0", r2["미래 바(오늘 바 날 > 판단 날)"] == 0 and r2["미래 칸(읽은 칸 > 오늘 칸)"] == 0 and r2["판단 수"] >= 3)

# ② 다음 칸 읽기
up = [("20200102", 100.0), ("20200103", 101.0), ("20200106", 99.0), ("20200107", 98.0), ("20200108", 97.0), ("20200109", 96.0)]
for mode in ("LEAK", "LEAK2"):
    r = run(prices(A=up, B=up), [("A", "20200102")], lambda ln, s, p, st, pk, row=None, m=mode: P.extra(m, 0, ln, s, p, st, pk))
    check(f"{mode} · 미래 칸 잡힘", r["미래 칸(읽은 칸 > 오늘 칸)"] >= 1, 미래칸=r["미래 칸(읽은 칸 > 오늘 칸)"])
for mode, n in (("NP", 3), ("CH", 2)):
    r = run(prices(A=up, B=up), [("A", "20200102")], lambda ln, s, p, st, pk, row=None, m=mode, k=n: P.extra(m, k, ln, s, p, st, pk))
    check(f"{mode}{n} · 미래 칸 0", r["미래 칸(읽은 칸 > 오늘 칸)"] == 0 and r["미래 바(오늘 바 날 > 판단 날)"] == 0)

# ③ 줄 끝 사라짐: A 줄이 01-06에서 끝남(자료 끝 01-08) · 안 팔면 엔진이 기록 없이 지움 → 1로 셈
short = [("20200102", 100.0), ("20200103", 100.0), ("20200106", 100.0)]
r = run(prices(A=short, B=FULL), [("A", "20200102")], never)
check("줄 끝 사라짐 셈", r["줄 끝 사라짐(보고 · 상속 한계)"] == 1, 셈=r["줄 끝 사라짐(보고 · 상속 한계)"])
r = run(prices(A=FULL, B=FULL), [("A", "20200102")], never)
check("자료 끝까지 있는 줄은 사라짐 0", r["줄 끝 사라짐(보고 · 상속 한계)"] == 0)

# ④ NP · CH 경계(직접 부름 · 칸 = 그 종목 바)
ln = {"closes": [100, 99, 98, 101, 97, 96]}
check("NP3 · 2번째 바는 안 팜", P.extra("NP", 3, ln, 0, 100, 2, 100) is False)
check("NP3 · 3번째 바 · 최고 ≤ 산 값이면 팜", P.extra("NP", 3, ln, 0, 100, 3, 100) is True)
check("NP3 · 3번째 바 · 이익 종가 있었으면 안 팜", P.extra("NP", 3, ln, 0, 100, 3, 101) is False)
ln = {"closes": [10, 9, 8, 8, 7]}
check("CH2 · 같은 최저는 안 팜(엄격)", P.extra("CH", 2, ln, 1, 9, 2, 9) is False)        # spot 3: 8 < min(9, 8)? 아니오
check("CH2 · 엄격 이탈이면 팜", P.extra("CH", 2, ln, 1, 9, 3, 9) is True)                # spot 4: 7 < min(8, 8)
check("CH4 · 앞 칸 모자라면 안 팜", P.extra("CH", 4, ln, 0, 10, 3, 10) is False)         # spot 3 − 4 < 0
check("CH · 산 날(step 0)은 안 팜", P.extra("CH", 1, ln, 2, 8, 0, 8) is False)
out["뜻"] = ("NP의 N · CH의 N은 그 종목 바 수(결측 날은 바가 없어 안 셈). 실제 7칸에서 결측 날이 보유 중에 끼었는지는 "
            "장부 단계 감사(미래 바 = 0이면 끼지 않음 · 그때 종목 바 수 = 시장 거래일 수)로 확인.")
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1)
print(sum(r["판정"] == "PASS" for r in out["행"]), "/", len(out["행"]))
sys.exit(0 if all(r["판정"] == "PASS" for r in out["행"]) else 3)
