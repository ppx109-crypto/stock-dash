"""MPOS-0026 작은 원자료 PIT 샘플 컷(설계 research/pit26/DESIGN.md · 손익 안 봄).
정직판 H(c): 원가격을 c까지 잘라 종목 하나씩 lab.build(horizons=(0,)) → 문턱 모집단(c까지 모든 행 변동성) · 창 W(c 앞 20거래일 · c 포함) 행.
비교판 F: 지금 캐시(nrl · 2026-09-25 표 · 전체 문턱 G · 캐시 shape/BR). 대조 (a) 문턱 (b) inside 행 존재 (c) 칸 값 (d) 후보 · 거절 이유.
EX_CUT · EX_OUT. cwd = 고정 나무 · tree_run."""
import hashlib
import json
import math
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import caps  # noqa: E402
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402
import final_study as F  # noqa: E402

C = os.environ["EX_CUT"]
WN = 20
P = study.load_prices()
# 가격이 캐시와 같은 판인지(같지 않으면 i가 어긋남)
same_px = sum(1 for c in P if c in nrl.prices and P[c]["rows"] == nrl.prices[c]["rows"])
cal = [d for d, _ in P["005930"]["rows"] if d <= C]
W = set(cal[-WN:])
Pc = {c: dict(b, rows=[x for x in b["rows"] if x[0] <= C]) for c, b in P.items()}
Pc = {c: b for c, b in Pc.items() if b["rows"]}
vols, Hrows = [], []
for c in sorted(Pc):
    for r in lab.build({c: Pc[c]}, horizons=(0,)):
        if r.get("변동성") is not None:
            vols.append(r["변동성"])
        if r["date"] in W:
            r.pop("ahead", None)
            Hrows.append(r)
vols.sort()
T_H = vols[int(len(vols) * rule.CALM)]
caps.tag(Hrows, rule.TOP)
H_in = {(r["code"], r["date"]): r for r in Hrows if caps.inside(r, rule.TOP)}
lanes_c = lab.lanes(Pc)
shape_c = F.shapes(lanes_c, {r["code"] for r in Hrows})
BR_c = F.breadth_by_day(Hrows, shape_c)
F_in = {(r["code"], r["date"]): r for r in nrl.inside if r["date"] in W}
nm = f"{int(C[:4]) + 1}01" if C[4:6] == "12" else f"{C[:4]}{int(C[4:6]) + 1:02d}"
th = {"정직 문턱 T_H(c까지 행 40% 자리)": T_H, "모집단 행 수": len(vols), "CALM_MONTH[" + nm + "]": nrl.CALM_MONTH.get(nm), "전체 문턱 G": rule._calm}
# (b) 행 존재
onlyH, onlyF = sorted(set(H_in) - set(F_in)), sorted(set(F_in) - set(H_in))
# (c) 칸 값
SKIP = {"ahead", "i"}
bad_cols, n_cmp = {}, 0
for k in set(H_in) & set(F_in):
    h, f = H_in[k], F_in[k]
    n_cmp += 1
    for col, hv in h.items():
        if col in SKIP or col not in f:
            continue
        fv = f[col]
        if isinstance(hv, float) and isinstance(fv, (int, float)):
            ok = (math.isnan(hv) and math.isnan(fv)) if (isinstance(fv, float) and (math.isnan(hv) or math.isnan(fv))) else abs(hv - fv) <= 1e-9 * max(1.0, abs(hv), abs(fv))
        else:
            ok = hv == fv
        if not ok:
            bad_cols.setdefault(col, []).append(k)
missing_cols = sorted({col for k in set(H_in) & set(F_in) for col in H_in[k] if col not in F_in[k] and col not in SKIP})


# (d) 후보 · 거절 이유
def gates(r, calm, shp, br):
    old = (rule._calm, nrl.shape, nrl.BR)
    rule._calm, nrl.shape, nrl.BR = calm, shp, br
    try:
        g = {"holds": bool(rule.holds(r)), "aligned": bool(nrl.aligned(r)), "teacher": bool(nrl.teacher(r)), "target_cut": bool(nrl.target_cut(r))}
        g["BASE_HOLD"] = bool(nrl.BASE_HOLD(r))
        g["갈래"] = nrl.tier(r) if g["BASE_HOLD"] else None
        return g
    finally:
        rule._calm, nrl.shape, nrl.BR = old


dd = {}
for k in sorted(set(H_in) & set(F_in)):
    gh = gates(H_in[k], T_H, shape_c, BR_c)
    gf = gates(F_in[k], rule._calm, nrl.shape, nrl.BR)
    for g in gh:
        if gh[g] != gf[g]:
            dd.setdefault(g, []).append(k)
calm_only = None
if dd:
    # 다른 행이 문턱 차이로만 설명되는지: H 쪽을 G 문턱으로 다시 셈
    rest = {}
    for k in sorted({x for v in dd.values() for x in v}):
        gh = gates(H_in[k], rule._calm, shape_c, BR_c)
        gf = gates(F_in[k], rule._calm, nrl.shape, nrl.BR)
        for g in gh:
            if gh[g] != gf[g]:
                rest.setdefault(g, []).append(k)
    calm_only = {"문턱을 G로 맞춘 뒤에도 남는 차이": {g: len(v) for g, v in rest.items()}, "예": {g: v[:5] for g, v in rest.items()}}
fail = bool(onlyH or onlyF or bad_cols or (calm_only and calm_only["문턱을 G로 맞춘 뒤에도 남는 차이"]))
out = {"자르는 날": C, "창 W": [min(W), max(W)], "가격 판 캐시와 같은 종목": [same_px, len(P)],
       "(a) 문턱": th,
       "(b) inside 행": {"H": len(H_in), "F": len(F_in), "H만": len(onlyH), "F만": len(onlyF), "H만 예": onlyH[:10], "F만 예": onlyF[:10]},
       "(c) 칸 값": {"비교 행": n_cmp, "다른 칸": {c: len(v) for c, v in bad_cols.items()}, "예": {c: v[:3] for c, v in bad_cols.items()}, "H에만 있는 칸": missing_cols},
       "(d) 문 다름(H: T_H · 다시 센 shape/BR · F: G · 캐시)": {g: len(v) for g, v in dd.items()}, "(d) 예": {g: v[:5] for g, v in dd.items()},
       "(d) 문턱 설명": calm_only,
       "판정": "PIT_SAMPLE_FAIL" if fail else "PIT_SAMPLE_PASS"}
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
