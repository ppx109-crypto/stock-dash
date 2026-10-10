"""REGIME-SW-0048 개발 실행기 — PLAN에 적은 축 · 순서 · 받아들이기 · 덜어냄 · 고원을 그대로 코드로.
- 평가는 regime_dev.evaluate()(STARTED 기록 · 상한 300)로만. 같은 설정은 한 번만 평가.
- 받아들이기: 연수익이 채택판보다 0.3%p 넘게 높고 · 하루 · 달 손실 −15% 이내. 한 축에서 여럿이면 연수익 가장 높은 값(같으면 표 앞).
- 최대 3바퀴 · 한 바퀴에 받아들인 값이 없으면 멈춤.
- 덜어냄: 각 축을 출발값(R0)으로 되돌려 연수익이 0.3%p 넘게 떨어지지 않으면 되돌림(쉬운 쪽).
- 고원: 순서 있는 축(n · persist · down_base · down_inv · up_lev · side_inv)의 양 이웃이 '1일봉만 대비 더 번 몫'의 절반 이상을 내고 손실 한도 안이어야 함.
- 판정: 연수익 > 1일봉만 + 1%p · 세 장(상승 · 하락 · 횡보 해) 각각 하루 · 달 −15% 이내 · 고원 통과 → ADOPT_CANDIDATE
  (운영 반영은 사용자 직접 승인) · 고원 실패 → PEAK_ONLY · 나아짐 없음 → NO_IMPROVEMENT.
python3 research/regime_rules.py     → LOG.md에 판마다 한 줄 · 끝에 결과 JSON"""
import json
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D  # noqa: E402

LOG = D.BOX / "LOG.md"
AXES = [("n", [20, 60, 120, 200]), ("confirm", ["none", "br40", "br30", "F20neg", "FI20neg", "vol15"]), ("persist", [1, 3, 5]),
        ("up_need", ["ma_rising", "above_only", "br50"]), ("down_base", [1.0, 0.5, 0.0]), ("down_inv", [0.0, 0.3, 0.5, 1.0]),
        ("inv", ["114800", "252670"]), ("up_lev", [0.0, 0.3, 0.6, 1.0]), ("side_inv", [0.0, 0.2, 0.4])]
ORDERED = ("n", "persist", "down_base", "down_inv", "up_lev", "side_inv")
STEP, MAX_PASS, ADOPT_MARGIN = 0.3, 3, 1.0
SEEN = {}


def key(c):
    return json.dumps(c, sort_keys=True, ensure_ascii=False)


def run(cfg, note):
    k = key(cfg)
    if k in SEEN:
        return SEEN[k]
    r = D.evaluate(cfg, note)
    SEEN[k] = r
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"| {D._started()} | {note} | {r['annual_pct']} | {r['worst_day_pct']} | {r['worst_month_pct']} | {r['mdd_report_pct']} | "
                 f"{r['halves_report']['2017~2021']} / {r['halves_report']['2022~2026']} | {r['state_share_pct']} |\n")
    print(D._started(), note, r["annual_pct"], r["worst_month_pct"], flush=True)
    return r


def better(c, i):
    return c["loss_ok"] and c["annual_pct"] > i["annual_pct"] + STEP


def plateau(cfg, res, base_ann):
    gain = res["annual_pct"] - base_ann
    out = {}
    for axis, values in AXES:
        if axis not in ORDERED:
            continue
        k = values.index(cfg[axis])
        for j in (k - 1, k + 1):
            if 0 <= j < len(values):
                nb = dict(cfg, **{axis: values[j]})
                r = run(nb, f"고원 이웃 {axis}={values[j]}")
                ok = r["loss_ok"] and (r["annual_pct"] - base_ann) >= gain / 2
                out[f"{axis}={values[j]}"] = {"annual_pct": r["annual_pct"], "ok": ok}
    return all(v["ok"] for v in out.values()), out


def main():
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write("\n| 번호 | 판(바꾼 것) | 연수익 | 가장 나쁜 하루 | 가장 나쁜 달 | 고점 대비(보고) | 앞 반 / 뒤 반(보고) | 국면 몫 % |\n|---|---|---|---|---|---|---|---|\n")
    inc = dict(D.R0)
    base_res = inc_res = run(inc, "R0 출발점(1일봉만)")
    base_ann = base_res["annual_pct"]
    for p in range(1, MAX_PASS + 1):
        moved = False
        for axis, values in AXES:
            cands = []
            for v in values:
                if v == inc[axis]:
                    continue
                c = dict(inc, **{axis: v})
                r = run(c, f"{p}바퀴 {axis}={v}")
                if better(r, inc_res):
                    cands.append((r["annual_pct"], -values.index(v), c, r))
            if cands:
                _, _, inc, inc_res = max(cands, key=lambda z: (z[0], z[1]))
                moved = True
                with LOG.open("a", encoding="utf-8") as fh:
                    fh.write(f"|  | **받아들임: {axis}={inc[axis]}** → {key(inc)} |  |  |  |  |  |  |\n")
        if not moved:
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(f"|  | {p}바퀴 받아들인 값 없음 → 멈춤 |  |  |  |  |  |  |\n")
            break
    for axis, _ in AXES:
        if inc[axis] == D.R0[axis]:
            continue
        c = dict(inc, **{axis: D.R0[axis]})
        r = run(c, f"덜어냄 {axis}={D.R0[axis]}")
        if r["loss_ok"] and r["annual_pct"] >= inc_res["annual_pct"] - STEP:
            inc, inc_res = c, r
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(f"|  | **덜어냄 받아들임: {axis}={D.R0[axis]}** |  |  |  |  |  |  |\n")
    if inc == D.R0:
        verdict, pl = "NO_IMPROVEMENT", (False, {})
    else:
        pl = plateau(inc, inc_res, base_ann)
        kinds_ok = all(v["worst_day_pct"] >= -15 and v["worst_month_pct"] >= -15 for v in inc_res["by_kind"].values())
        if not (inc_res["annual_pct"] > base_ann + ADOPT_MARGIN and kinds_ok):
            verdict = "NO_IMPROVEMENT"
        else:
            verdict = "ADOPT_CANDIDATE" if pl[0] else "PEAK_ONLY"
    out = {"final": inc, "final_res": inc_res, "base_res": base_res, "plateau": pl[1], "plateau_ok": pl[0], "verdict": verdict, "evals": D._started()}
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## 개발 끝\n- 판정 {verdict} · 최종 {key(inc)} · 평가 판 {D._started()} / 300\n")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
