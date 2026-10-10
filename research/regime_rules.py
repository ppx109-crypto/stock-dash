"""REGIME-SW-0048 개발 실행기(round 2) — PLAN에 적은 단계 · 축 · 받아들이기 · 덜어냄 · 고원을 그대로 코드로.
- 평가는 regime_dev.evaluate()로만(STARTED 기록 · 상한 300 · 끝난 설정은 기록에서 다시 씀 → 재시작해도 같은 설정 한 번).
- 모든 비교는 반올림 전 값(annual_raw · loss_ok · kinds_ok)으로 함. 출력만 반올림.
- 1단계(판정기 격자 · GPT #211 지적: R0는 ETF 몫이 0이라 판정 축만 바꾸면 계좌가 같음):
  시험용 몫 PROBE(하락: 1일봉 0.5 + 인버스 0.5 · 상승: 레버리지 0.3)를 고정하고 n × confirm × persist 격자를 모두 셈.
  가장 높은 연수익(손실 한도 안 · 같으면 표 앞)의 판정기를 2단계 출발점으로.
- 2단계(좌표 하강 · 최대 3바퀴): 모든 축. 받아들이기 = 연수익이 채택판보다 0.3%p 넘게 높고 하루 · 달 −15% 이내.
- 덜어냄: 몫 축(down_base · down_inv · up_lev · side_inv · exit_buf)을 R0 값으로 되돌려 0.3%p 넘게 안 떨어지면 되돌림.
- 고원: 순서 있는 축의 이웃이 '1일봉만 대비 더 번 몫'의 절반 이상 · 손실 한도 안. 격자 끝은 한쪽만(따로 표시).
- 판정: 연수익 > 1일봉만 + 1%p · 세 장 각각 하루 · 달 −15% · 고원 → ADOPT_CANDIDATE / 고원 실패 → PEAK_ONLY / 나머지 NO_IMPROVEMENT.
  기간 결손(2016-01 ~ 2017-01)은 따로 designated_period_gap = NEEDS_DATA로 적음.
python3 research/regime_rules.py"""
import json
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D  # noqa: E402

LOG = D.BOX / "LOG.md"
CONFIRMS = ["none", "br40", "br30", "F20neg", "FI20neg", "vol15", "r5m3", "r10m5", "sbr30"]
AXES = [("n", [20, 60, 120, 200]), ("confirm", CONFIRMS), ("persist", [1, 3, 5]), ("exit_buf", [0.0, 0.02, 0.05]),
        ("up_need", ["ma_rising", "above_only", "br50"]), ("down_base", [1.0, 0.5, 0.0]), ("down_inv", [0.0, 0.3, 0.5, 1.0]),
        ("inv", ["114800", "252670"]), ("up_lev", [0.0, 0.3, 0.6, 1.0]), ("side_inv", [0.0, 0.2, 0.4])]
ORDERED = ("n", "persist", "exit_buf", "down_base", "down_inv", "up_lev", "side_inv")
SIZE_AXES = ("down_base", "down_inv", "up_lev", "side_inv", "exit_buf")
PROBE = {"down_base": 0.5, "down_inv": 0.5, "inv": "114800", "up_lev": 0.3}
STEP, MAX_PASS, ADOPT_MARGIN = 0.3, 3, 1.0
SEEN = {}


def key(c):
    return json.dumps(c, sort_keys=True, ensure_ascii=False)


def ann(r):
    return r["annual_raw"] * 100


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
    return c["loss_ok"] and ann(c) > ann(i) + STEP


def plateau(cfg, res, base_ann):
    gain = ann(res) - base_ann
    out = {}
    for axis, values in AXES:
        if axis not in ORDERED:
            continue
        k = values.index(cfg[axis])
        side = "양쪽" if 0 < k < len(values) - 1 else "한쪽(격자 끝)"
        for j in (k - 1, k + 1):
            if 0 <= j < len(values):
                r = run(dict(cfg, **{axis: values[j]}), f"고원 이웃 {axis}={values[j]}")
                out[f"{axis}={values[j]}"] = {"annual_pct": r["annual_pct"], "ok": r["loss_ok"] and (ann(r) - base_ann) >= gain / 2, "sides": side}
    return all(v["ok"] for v in out.values()), out


def main():
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write("\n| 번호 | 판(바꾼 것) | 연수익 | 가장 나쁜 하루 | 가장 나쁜 달 | 고점 대비(보고) | 앞 반 / 뒤 반(보고) | 국면 몫 % |\n|---|---|---|---|---|---|---|---|\n")
    base_res = run(dict(D.R0), "R0 출발점(1일봉만)")
    base_ann = ann(base_res)
    # 1단계: 판정기 격자(시험용 몫 고정)
    best = None
    for n in AXES[0][1]:
        for cf in CONFIRMS:
            for ps in AXES[2][1]:
                c = dict(D.R0, **PROBE, n=n, confirm=cf, persist=ps)
                r = run(c, f"1단계 n={n} {cf} 버팀{ps}")
                if r["loss_ok"] and (best is None or ann(r) > ann(best[1])):
                    best = (c, r)
    if best is None:
        inc, inc_res = dict(D.R0), base_res
    else:
        inc, inc_res = best
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"|  | **1단계 고른 판정기** → {key(inc)} |  |  |  |  |  |  |\n")
    # 2단계: 좌표 하강
    for p in range(1, MAX_PASS + 1):
        moved = False
        for axis, values in AXES:
            cands = []
            for v in values:
                if v == inc[axis]:
                    continue
                c = dict(inc, **{axis: v})
                r = run(c, f"2단계 {p}바퀴 {axis}={v}")
                if better(r, inc_res):
                    cands.append((ann(r), -values.index(v), c, r))
            if cands:
                _, _, inc, inc_res = max(cands, key=lambda z: (z[0], z[1]))
                moved = True
                with LOG.open("a", encoding="utf-8") as fh:
                    fh.write(f"|  | **받아들임: {axis}={inc[axis]}** → {key(inc)} |  |  |  |  |  |  |\n")
        if not moved:
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(f"|  | 2단계 {p}바퀴 받아들인 값 없음 → 멈춤 |  |  |  |  |  |  |\n")
            break
    # 덜어냄(몫 축)
    for axis in SIZE_AXES:
        if inc[axis] == D.R0[axis]:
            continue
        c = dict(inc, **{axis: D.R0[axis]})
        r = run(c, f"덜어냄 {axis}={D.R0[axis]}")
        if r["loss_ok"] and ann(r) >= ann(inc_res) - STEP:
            inc, inc_res = c, r
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(f"|  | **덜어냄 받아들임: {axis}={D.R0[axis]}** |  |  |  |  |  |  |\n")
    same_as_base = all(inc[a] == D.R0[a] for a in SIZE_AXES)
    if same_as_base or not (ann(inc_res) > base_ann + ADOPT_MARGIN and inc_res["kinds_ok"]):
        verdict, pl = "NO_IMPROVEMENT", (False, {})
    else:
        pl = plateau(inc, inc_res, base_ann)
        verdict = "ADOPT_CANDIDATE" if pl[0] else "PEAK_ONLY"
    out = {"final": inc, "final_res": inc_res, "base_res": base_res, "plateau": pl[1], "plateau_ok": pl[0], "verdict": verdict,
           "designated_period_gap": "NEEDS_DATA(2016-01 ~ 2017-01 장부 없음)", "evals": D._started()}
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## 개발 끝\n- 판정 {verdict} · 최종 {key(inc)} · 평가 판 {D._started()} / 300 · 기간 결손 NEEDS_DATA(2016-01 ~ 2017-01)\n")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
