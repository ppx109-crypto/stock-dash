"""통합 매매 규칙 DNA · RNA 시험(사용자 2026-10-03 "DNA인지 RNA인지 테스트 · RNA면 흔들면서 RNA 테스트").
1일봉 · 15분봉 후보의 '조용함'(① 추세 문 조건1) 문턱:
  DNA      = 지금 규칙 — 모든 종목 · 모든 날 변동성을 한 번에 줄 세운 아래 40% 자리(고정 숫자 ≈ 2.15)
  DNA_past = 그 달 앞 자료로만 다시 잰 같은 문턱(dguard 아홉째 겹)
  RNA q    = 그날 시총 100위 안 종목끼리 견준 아래 q(날마다 움직임 · 그날 값만 씀 · 미래 참조 없음)
  RNA_jit  = 날마다 q를 30 ~ 50% 사이에서 무작위로 흔듦(씨앗별)
I_VAR=DNA | DNA_past | RNA30 | RNA35 | RNA40 | RNA45 | RNA50 | JIT0 ~ JIT4 · 결과는 한 줄."""
import os
import random
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash")
import lab
import nrl
import rule

var = os.environ.get("I_VAR", "DNA")
full = rule._calm
by_day = {}
for r in nrl.inside:
    if r.get("변동성") is not None:
        by_day.setdefault(r["date"], []).append(r["변동성"])
by_day = {d: np.sort(np.array(v)) for d, v in by_day.items()}


def cut(d, q):
    v = by_day.get(d)
    return float(v[min(len(v) - 1, int(len(v) * q))]) if v is not None and len(v) >= 20 else full


if var.startswith("SHK"):
    # DNA 흔들기: 고정 숫자 셋을 ±20% 안에서 무작위로 한 번 바꿈(씨앗별) — 추세 기울기 · 60일 오름 · 조용함 자리
    rng = random.Random(100 + int(var[3:]))
    rule.SLOPE = 1.46 * rng.uniform(0.8, 1.2)
    rule.SIXTY = 20.0 * rng.uniform(0.8, 1.2)
    cq = 0.4 * rng.uniform(0.8, 1.2)
    allv = np.sort(np.array([r["변동성"] for r in nrl.inside if r.get("변동성") is not None]))
    full_shk = float(allv[int(len(allv) * cq)])
    edge = lambda d: full_shk
    print(f"  흔든 값: 기울기 {rule.SLOPE:.2f} · 60일 {rule.SIXTY:.1f}% · 조용함 자리 {cq * 100:.0f}%", flush=True)
elif var == "DNA":
    edge = lambda d: full
elif var == "DNA_past":
    edge = lambda d: (nrl.CALM_MONTH or {}).get(d[:6], full)
elif var.startswith("RNA"):
    q = int(var[3:]) / 100
    edge = lambda d: cut(d, q)
else:
    rng = random.Random(int(var[3:]))
    qs = {d: rng.uniform(0.30, 0.50) for d in sorted(by_day)}
    edge = lambda d: cut(d, qs.get(d, 0.4))
inner = rule.holds


def holds(r):
    rule._calm = edge(r["date"])
    try:
        return inner(r)
    finally:
        rule._calm = full


if var != "DNA":
    # 추세 문(rule.holds) 안의 문턱만 바꿈 — 사는 조건 전체(nrl.BASE_HOLD = (추세 문 또는 정배열 문) · 수급 · 목표가 거름)와 크기(BASE_SIZE)는 그대로(dguard 아홉째 겹과 같은 방식)
    rule.holds = holds


out = []
for side, since, pool in (("앞 2017 ~ 2020", rule.SINCE, nrl.early), ("뒤 2021 ~", rule.MID, nrl.inside)):
    g = lab.wobble(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, tries=8, rank=rule.order,
                   slots=nrl.SLOTS, since=since, apart=nrl.kin, realistic=True, cap=130, size=nrl.BASE_SIZE)
    if g and side.startswith("앞") and var == "DNA": print("열쇠", sorted(g.keys()), flush=True)
    out.append(f"{side} 연 {g['연수익']:+.1f} 골 {g.get('최대낙폭', g.get('골', float('nan')))} 매매 {g.get('매매', '?')}" if g else f"{side} 없음")
mid = [cut(d, 0.4) for d in sorted(by_day) if d >= "20170101"]
print(f"[{var}] " + " | ".join(out) + (f" | RNA40 문턱 범위 {min(mid):.2f} ~ {max(mid):.2f} (DNA {full:.2f})" if var == "RNA40" else ""), flush=True)
