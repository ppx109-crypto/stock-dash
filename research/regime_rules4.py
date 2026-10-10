"""REGIME-SW-0051 — '손실까지 튼튼한 후보' 찾기(REGIME-SW-0050 ADOPT_CANDIDATE의 남은 약점: 작은 규칙 이웃 4/6이 달 −10%를 넘음).
- 규칙 틀은 0050과 같음: confirm r10m5 · up_need above_only · band None · exit_buf 0 · 하락 1일봉 1.0 · 인버스 0 · lev_vt None.
- 1단계 격자(210판): n {20 · 24 · 28 · 30 · 32 · 36 · 40} × persist {1 · 2 · 3} × up_lev {0.10 · 0.15 · 0.20 · 0.25 · 0.30} × side_inv {0 · 0.2}
- 손실 잣대(반올림 전 · 0050과 같음): 세 장 각각 하루 ≥ −15% · 달 ≥ −10%
- 2단계(손실 고원 · 새 잣대): 잣대 안 격자 칸을 연수익(반올림 전) 높은 순으로 보며, 작은 규칙 이웃(n × 0.85 · × 1.15 반올림 · persist ± 1 · r10m4 · r10m6)
  **모두가 같은 손실 잣대 안**이고 '1일봉만 대비 더 번 몫'의 절반 이상이면 그 칸이 최종(ROBUST_CANDIDATE). 이웃 평가 포함 총 300판 상한 안에서만 봄.
- 판정: ROBUST_CANDIDATE(위 모두 · 연수익 > 1일봉만 + 1%p) / NO_ROBUST(상한 안에서 못 찾음 · 그때까지 본 칸과 이웃 전부 공개)
REG_BOX=REGIME-SW-0051 python3 research/regime_rules4.py"""
import json
import os
import sys

os.environ.setdefault("REG_BOX", "REGIME-SW-0051")
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D  # noqa: E402

LOG = D.BOX / "LOG.md"
FIXED = {"confirm": "r10m5", "up_need": "above_only", "band": None, "exit_buf": 0.0, "down_base": 1.0, "down_inv": 0.0,
         "inv": "114800", "lev_vt": None}
NS = [20, 24, 28, 30, 32, 36, 40]
PS = [1, 2, 3]
LEVS = [0.10, 0.15, 0.20, 0.25, 0.30]
SIDES = [0.0, 0.2]
DAY_LIM, MONTH_LIM, ADOPT_MARGIN, CAP = -0.15, -0.10, 1.0, 300
CACHE = {}


def key(c):
    return json.dumps(c, sort_keys=True, ensure_ascii=False)


def ann(r):
    return r["annual_raw"] * 100


def within(r):
    return all(k["worst_day_raw"] >= DAY_LIM and k["worst_month_raw"] >= MONTH_LIM for k in r["by_kind"].values())


def run(cfg, note):
    k = key(cfg)
    if k in CACHE:
        return CACHE[k]
    r = D.evaluate(cfg, note)
    CACHE[k] = r
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"| {D._started()} | {note} | {r['annual_pct']} | {r['worst_day_pct']} | {r['worst_month_pct']} | {within(r)} |\n")
    print(D._started(), note, r["annual_pct"], r["worst_month_pct"], flush=True)
    return r


def neighbors(cfg):
    out = [("n", m) for m in sorted({round(cfg["n"] * 0.85), round(cfg["n"] * 1.15)} - {cfg["n"]})]
    out += [("persist", p) for p in (cfg["persist"] - 1, cfg["persist"] + 1) if p >= 1]
    out += [("confirm", "r10m4"), ("confirm", "r10m6")]
    return out


def main():
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write("\n| 번호 | 판 | 연수익 | 가장 나쁜 하루 | 가장 나쁜 달 | 하루 −15 · 달 −10 안 |\n|---|---|---|---|---|---|\n")
    base = run(dict(D.R0), "R0 출발점(1일봉만)")
    base_ann = ann(base)
    grid = []
    for n in NS:
        for p in PS:
            for lev in LEVS:
                for side in SIDES:
                    c = dict(D.R0, **FIXED, n=n, persist=p, up_lev=lev, side_inv=side)
                    grid.append((c, run(c, f"격자 n {n} 버팀 {p} lev {lev} side {side}")))
    ok = sorted([(c, r) for c, r in grid if within(r) and ann(r) > base_ann + ADOPT_MARGIN], key=lambda z: (-ann(z[1]), key(z[0])))
    checked, final = [], None
    for c, r in ok:
        nbs = neighbors(c)
        need = sum(1 for a, v in nbs if key(dict(c, **{a: v})) not in CACHE)
        if D._started() + need > CAP:
            break
        rows, good = {}, True
        for a, v in nbs:
            nr = run(dict(c, **{a: v}), f"손실 고원 이웃 {a}={v} (n {c['n']} 버팀 {c['persist']} lev {c['up_lev']} side {c['side_inv']})")
            w, g = within(nr), (ann(nr) - base_ann) >= (ann(r) - base_ann) / 2
            rows[f"{a}={v}"] = {"annual_pct": nr["annual_pct"], "worst_month_pct": nr["worst_month_pct"], "worst_day_pct": nr["worst_day_pct"], "within": w, "half_gain": g}
            good = good and w and g
        checked.append({"cfg": c, "annual_pct": r["annual_pct"], "worst_month_pct": r["worst_month_pct"], "neighbors": rows, "robust": good})
        if good:
            final = (c, r)
            break
    out = {"verdict": "ROBUST_CANDIDATE" if final else "NO_ROBUST", "final": final[0] if final else None, "final_res": final[1] if final else None,
           "base_res": base, "grid_within": len(ok), "checked": checked, "evals": D._started(),
           "designated_period_gap": "NEEDS_DATA(2016-01 ~ 2017-01 장부 없음)", "limits": {"day": DAY_LIM, "month": MONTH_LIM}}
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## 끝\n- 판정 {out['verdict']} · 최종 {key(out['final']) if final else '없음'} · 살펴본 칸 {len(checked)} · 평가 판 {D._started()} / {CAP}\n")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
