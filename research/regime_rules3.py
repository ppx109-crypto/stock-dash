"""REGIME-SW-0050 — REGIME-SW-0049 최종 규칙은 그대로 두고, 몫만 '가장 나쁜 달 −10% 이내'로 다시 고르기(사용자 2026-10-10 지시).
- 사용자 지시: "가장 나쁜 달 −10% 이내로 몫 다시 골라줘 · 고른 후 모의투자에 임시저장"
- 고정 규칙(0049 최종): n 30 · confirm r10m5 · persist 2 · up_need above_only · band None · exit_buf 0 · 하락 1일봉 1.0 · 인버스 0
- 몫 격자(231판): up_lev {0.30 ~ 0.80 · 0.05 간격} × lev_vt {None · 0.10 · 0.125 · 0.15 · 0.175 · 0.20 · 0.25} × side_inv {0 · 0.1 · 0.2}
- 손실 잣대(반올림 전 값): 상승 · 하락 · 횡보 해 각각 가장 나쁜 하루 ≥ −15% 그리고 **가장 나쁜 달 ≥ −10%**
- 고르기: 잣대 안에서 연수익(반올림 전) 가장 높은 것 · 같으면 격자 앞(작은 몫).
- 고원(사용자 2026-10-10 정의 · 0049와 같음): 몫 축은 뺌. 규칙 숫자 아주 조금(n 26 · 34 · persist 1 · 3 · r10m4 · r10m6 · lev_vt ±0.02) 이웃이 '1일봉만 대비 더 번 몫'의 절반 이상. 이웃 손실은 보고만.
- 판정: 연수익 > 1일봉만 + 1%p · 잣대 통과 · 고원 → ADOPT_CANDIDATE / 고원 실패 → PEAK_ONLY / 잣대 통과 몫 없음 · 나아짐 없음 → NO_IMPROVEMENT
REG_BOX=REGIME-SW-0050 python3 research/regime_rules3.py"""
import json
import os
import sys

os.environ.setdefault("REG_BOX", "REGIME-SW-0050")
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D  # noqa: E402
import regime_rules2 as R2  # noqa: E402

LOG = D.BOX / "LOG.md"
RULE = {"n": 30, "confirm": "r10m5", "persist": 2, "up_need": "above_only", "band": None, "exit_buf": 0.0,
        "down_base": 1.0, "down_inv": 0.0, "inv": "114800"}
LEVS = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
VTS = [None, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25]
SIDES = [0.0, 0.1, 0.2]
DAY_LIM, MONTH_LIM, ADOPT_MARGIN = -0.15, -0.10, 1.0


def ann(r):
    return r["annual_raw"] * 100


def within(r):
    """세 장 각각 하루 ≥ −15% · 달 ≥ −10%(반올림 전)."""
    return all(k["worst_day_raw"] >= DAY_LIM and k["worst_month_raw"] >= MONTH_LIM for k in r["by_kind"].values())


CACHE = {}


def run(cfg, note):
    r = D.evaluate(cfg, note)
    CACHE[json.dumps(cfg, sort_keys=True, ensure_ascii=False)] = r
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"| {D._started()} | {note} | {r['annual_pct']} | {r['worst_day_pct']} | {r['worst_month_pct']} | {within(r)} | {r['mdd_report_pct']} |\n")
    print(D._started(), note, r["annual_pct"], r["worst_month_pct"], flush=True)
    return r


def main():
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write("\n| 번호 | 판 | 연수익 | 가장 나쁜 하루 | 가장 나쁜 달 | 하루 −15 · 달 −10 안 | 고점 대비(보고) |\n|---|---|---|---|---|---|---|\n")
    base = run(dict(D.R0), "R0 출발점(1일봉만)")
    base_ann = ann(base)
    best = None
    for lev in LEVS:
        for vt in VTS:
            for side in SIDES:
                c = dict(D.R0, **RULE, up_lev=lev, lev_vt=vt, side_inv=side)
                r = run(c, f"몫 lev {lev} vt {vt} side {side}")
                if within(r) and (best is None or ann(r) > ann(best[1])):
                    best = (c, r)
    if best is None or ann(best[1]) <= base_ann + ADOPT_MARGIN:
        out = {"verdict": "NO_IMPROVEMENT", "final": best[0] if best else None, "final_res": best[1] if best else None, "base_res": base}
    else:
        inc, res = best
        R2.run = run                                   # 고원 이웃 평가도 이 기록 칸 · 이 표로
        pl_ok, pl = R2.plateau(inc, res, base_ann)
        for axis, val in R2.neighbors(inc):
            nb = CACHE.get(json.dumps(dict(inc, **{axis: val}), sort_keys=True, ensure_ascii=False))
            pl[f"{axis}={val}"]["within_10_report"] = within(nb) if nb else None
        edges = {"up_lev": inc["up_lev"] in (LEVS[0], LEVS[-1]), "lev_vt": inc["lev_vt"] in (VTS[0], VTS[-1]), "side_inv": inc["side_inv"] in (SIDES[0], SIDES[-1])}
        out = {"verdict": "ADOPT_CANDIDATE" if pl_ok else "PEAK_ONLY", "final": inc, "final_res": res, "base_res": base,
               "plateau_ok": pl_ok, "plateau": pl, "grid_edge_report": edges}
    out.update({"designated_period_gap": "NEEDS_DATA(2016-01 ~ 2017-01 장부 없음)", "evals": D._started(), "limits": {"day": DAY_LIM, "month": MONTH_LIM}})
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## 끝\n- 판정 {out['verdict']} · 최종 {json.dumps(out['final'], sort_keys=True, ensure_ascii=False)} · 평가 판 {D._started()} / 300\n")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
