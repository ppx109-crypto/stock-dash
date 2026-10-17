"""MPOS-0025 A(H-CALM) 손익 없는 부분: ① 도구 시험(합성) ② 자르는 날 4개에서 '자른 표의 문턱'(= CALM_MONTH[c 다음 달] · 동치)로
c까지 줄의 holds · BASE_HOLD · 갈래를 다시 셈 → 전체 문턱 G 판과 다른 줄 수 · 원판 진입과 겹침. 엔진은 다시 돌리지 않음.
cwd = 고정 나무 · tree_run. 출력: EX_OUT."""
import bisect
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import nrl  # noqa: E402
import rule  # noqa: E402

RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"
CUTS = ("20181228", "20201230", "20221229", "20241230")


# ---- ① 도구 시험(합성 · 실제 자료 안 씀) ----
def global_edge(rows, q=rule.CALM):
    v = sorted(x for _, x in rows)
    return v[int(len(v) * q)]


def month_edge(rows, month, q=rule.CALM):
    """그달 첫날 앞 줄만(nrl._calm_by_month와 같은 식)."""
    got = sorted(rows)
    k = bisect.bisect_left([d for d, _ in got], month + "01")
    v = sorted(x for _, x in got[:k])
    return v[int(k * q)] if k else None


rnd = random.Random(11)
days = [f"{y}{m:02d}{d:02d}" for y in (2019, 2020) for m in range(1, 13) for d in (5, 15, 25)]
syn = [(d, rnd.uniform(1.0, 3.0)) for d in days for _ in range(20)]
cut = "20191231"
fut = [(d, x * (2.0 if d > cut else 1.0)) for d, x in syn]                 # c 뒤 변동성만 바꿈
past = [(d, x) for d, x in syn if d <= cut]
honest_same = all(month_edge(syn, m) == month_edge(fut, m) for m in sorted({d[:6] for d in days}) if m <= "201912")
g0, g1 = global_edge(syn), global_edge(fut)
dec0 = [x <= g0 for _, x in past]
dec1 = [x <= g1 for _, x in past]
tool = {"정직 대조(달 문턱 · c 뒤 바꿔도 c까지 달 문턱 같음)": honest_same,
        "고의 누수(전체 한 번 문턱 · c 뒤 바꾸면 c 앞 판단이 바뀜)": dec0 != dec1, "누수로 바뀐 c 앞 판단 수": sum(a != b for a, b in zip(dec0, dec1))}
assert tool["정직 대조(달 문턱 · c 뒤 바꿔도 c까지 달 문턱 같음)"] and tool["고의 누수(전체 한 번 문턱 · c 뒤 바꾸면 c 앞 판단이 바뀜)"], tool

# ---- ② 자르는 날 4개 ----
G = rule._calm
CM = nrl.CALM_MONTH
rows = [r for r in nrl.inside if r["date"] >= rule.SINCE]
led = json.load(open(os.environ["EX_LEDGER"]))
assert hashlib.sha256(json.dumps(led).encode()).hexdigest() == RAW_SHA
entries = {(x[0], x[1]) for x in led}


def with_calm(v, f, r):
    old = rule._calm
    rule._calm = v
    try:
        return f(r)
    finally:
        rule._calm = old


res = {}
for c in CUTS:
    nm = f"{int(c[:4]) + (c[4:6] == '12')}{'01' if c[4:6] == '12' else int(c[4:6]) + 1:02d}" if False else (f"{int(c[:4]) + 1}01" if c[4:6] == "12" else f"{c[:4]}{int(c[4:6]) + 1:02d}")
    T = CM[nm]
    sub = [r for r in rows if r["date"] <= c]
    fh = [r for r in sub if rule.holds(r) != with_calm(T, rule.holds, r)]
    fb = [r for r in sub if nrl.BASE_HOLD(r) != with_calm(T, nrl.BASE_HOLD, r)]
    ft = [r for r in sub if nrl.BASE_HOLD(r) and with_calm(T, nrl.BASE_HOLD, r) and nrl.tier(r) != with_calm(T, nrl.tier, r)]
    keys = {(r["code"], r["date"]) for r in fb + ft}
    res[c] = {"자른 표 문턱(= CALM_MONTH[" + nm + "])": T, "전체 문턱 G": G, "c까지 inside 줄": len(sub),
              "holds 다름": len(fh), "BASE_HOLD 다름": len(fb), "갈래 다름(BASE_HOLD 둘 다 참)": len(ft),
              "원판 진입과 겹침": len(keys & entries), "다른 줄(BASE_HOLD · 갈래 · 앞 10)": sorted(keys)[:10]}
out = {"장부 지문": RAW_SHA, "도구 시험": tool, "자르는 날": res,
       "범위": "엔진 다시 안 돌림 · 자른 표의 미래 존재 조건(c 앞 5바 줄 빠짐)은 반영 안 함 · 손익 없음"}
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
