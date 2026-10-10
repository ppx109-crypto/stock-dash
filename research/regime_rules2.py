"""REGIME-SW-0049 개발 실행기 — 레버리지 몫을 그날까지 흔들림으로 줄이는 판(REGIME-SW-0048 PEAK_ONLY 뒤).
- 평가: regime_dev.evaluate()(REG_BOX=REGIME-SW-0049 · STARTED 기록 · 상한 300 · 끝난 설정 다시 씀). 비교는 모두 반올림 전 값.
- 출발 판정기 = REGIME-SW-0048 최종(n 20 · br30 · 버팀 3 · above_only · 하락 1일봉 1.0 · 인버스 0 · 횡보 0).
- 1단계(63판): 레버리지 상한 up_lev 9 × 목표 흔들림 lev_vt 7(None = 줄이지 않음) · band 0.05로 모두 셈 → 손실 한도 안 최고(같으면 표 앞).
- 2단계(좌표 하강 · 최대 3바퀴): 아래 모든 축 · 받아들이기 = +0.3%p 넘게 · 하루 · 달 −15% 이내.
- 덜어냄: band → None · side_inv → 0 · down_inv → 0(down_base → 1.0) 쪽으로 되돌려 0.3%p 넘게 안 떨어지면 되돌림.
- 고원(round 2 · 사용자 2026-10-10 "고원의 정의를 다시 해"): **규칙 숫자만, 아주 조금 바꾼 이웃**으로 잼.
  · 몫 축(up_lev · side_inv · down_inv · down_base)은 고원에서 뺌 — 몫을 키우면 손실이 커지는 것은 당연하므로, 몫은 손실 한도(−15%)로만 정함.
  · 이웃: n × 0.85 · × 1.15(반올림) · persist ± 1 · 확인 문턱(폭 ± 5 · 5일 ± 0.5%p · 10일 ± 1%p · 흔들림 비 ± 0.2) · lev_vt ± 0.02 · band ± 0.02 · exit_buf ± 0.01
  · 통과: 이웃마다 '1일봉만 대비 더 번 몫'의 절반 이상. 손실 한도는 최종 설정에만 적용하고, 이웃의 손실은 보고만 함.
- 판정: 연수익 > 1일봉만 + 1%p · 세 장 각각 −15% · 고원 → ADOPT_CANDIDATE / 고원 실패 → PEAK_ONLY / NO_IMPROVEMENT. 기간 결손 NEEDS_DATA 따로.
REG_BOX=REGIME-SW-0049 python3 research/regime_rules2.py"""
import json
import os
import sys

os.environ.setdefault("REG_BOX", "REGIME-SW-0049")
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D  # noqa: E402

LOG = D.BOX / "LOG.md"
CAPS = [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8]
VTS = [None, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25]
START = {"n": 20, "confirm": "br30", "persist": 3, "down_base": 1.0, "down_inv": 0.0, "inv": "114800", "up_lev": 0.3,
         "side_inv": 0.0, "up_need": "above_only", "exit_buf": 0.0, "lev_vt": None, "band": 0.05}
CONFIRMS = ["none", "br40", "br30", "F20neg", "FI20neg", "vol15", "r5m3", "r10m5", "sbr30"]
AXES = [("n", [10, 15, 20, 30, 40]), ("persist", [2, 3, 4]), ("confirm", CONFIRMS), ("up_need", ["ma_rising", "above_only", "br50"]),
        ("band", [None, 0.05, 0.10]), ("up_lev", CAPS), ("lev_vt", VTS), ("side_inv", [0.0, 0.1, 0.2]), ("down_inv", [0.0, 0.3, 0.5])]
SIMPLER = {"band": None, "side_inv": 0.0, "down_inv": 0.0}
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


def with_down(cfg, v):
    """down_inv를 바꾸면 하락 때 1일봉 몫도 맞춤: 0 → 1.0 · 0.3 / 0.5 → 0.5."""
    return dict(cfg, down_inv=v, down_base=(1.0 if v == 0.0 else 0.5))


def change(cfg, axis, v):
    return with_down(cfg, v) if axis == "down_inv" else dict(cfg, **{axis: v})


def better(c, i):
    return c["loss_ok"] and ann(c) > ann(i) + STEP


def neighbors(cfg):
    """규칙 숫자를 아주 조금 바꾼 이웃(몫 축은 뺌)."""
    out = []
    n = cfg["n"]
    for m in sorted({round(n * 0.85), round(n * 1.15)} - {n}):
        out.append(("n", m))
    for p in (cfg["persist"] - 1, cfg["persist"] + 1):
        if p >= 1:
            out.append(("persist", p))
    c = cfg["confirm"]
    for pre, step in (("sbr", 5), ("br", 5), ("r10m", 1), ("r5m", 0.5), ("vol", 2)):
        if c.startswith(pre):
            x = float(c[len(pre):])
            for y in (x - step, x + step):
                out.append(("confirm", f"{pre}{y:g}"))
            break
    if cfg.get("lev_vt") is not None:
        for y in (cfg["lev_vt"] - 0.02, cfg["lev_vt"] + 0.02):
            out.append(("lev_vt", round(y, 4)))
    if cfg.get("band") is not None:
        for y in (cfg["band"] - 0.02, cfg["band"] + 0.02):
            if y > 0:
                out.append(("band", round(y, 4)))
    if cfg.get("exit_buf", 0) > 0:
        for y in (cfg["exit_buf"] - 0.01, cfg["exit_buf"] + 0.01):
            if y >= 0:
                out.append(("exit_buf", round(y, 4)))
    return out


def plateau(cfg, res, base_ann):
    gain = ann(res) - base_ann
    out = {}
    for axis, v in neighbors(cfg):
        r = run(dict(cfg, **{axis: v}), f"고원 이웃 {axis}={v}")
        out[f"{axis}={v}"] = {"annual_pct": r["annual_pct"], "worst_day_pct": r["worst_day_pct"], "worst_month_pct": r["worst_month_pct"],
                              "loss_ok_report": r["loss_ok"], "ok": (ann(r) - base_ann) >= gain / 2}
    return (bool(out) and all(v["ok"] for v in out.values())), out


def main():
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write("\n| 번호 | 판(바꾼 것) | 연수익 | 가장 나쁜 하루 | 가장 나쁜 달 | 고점 대비(보고) | 앞 반 / 뒤 반(보고) | 국면 몫 % |\n|---|---|---|---|---|---|---|---|\n")
    base_res = run(dict(D.R0), "R0 출발점(1일봉만)")
    base_ann = ann(base_res)
    best = None
    for cap in CAPS:
        for vt in VTS:
            c = dict(START, up_lev=cap, lev_vt=vt)
            r = run(c, f"1단계 상한 {cap} 목표 흔들림 {vt}")
            if r["loss_ok"] and (best is None or ann(r) > ann(best[1])):
                best = (c, r)
    inc, inc_res = best if best else (dict(START), run(dict(START), "출발"))
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"|  | **1단계 고른 판** → {key(inc)} |  |  |  |  |  |  |\n")
    for p in range(1, MAX_PASS + 1):
        moved = False
        for axis, values in AXES:
            cands = []
            for v in values:
                if v == inc[axis]:
                    continue
                c = change(inc, axis, v)
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
    for axis, v in SIMPLER.items():
        if inc[axis] == v:
            continue
        c = change(inc, axis, v)
        r = run(c, f"덜어냄 {axis}={v}")
        if r["loss_ok"] and ann(r) >= ann(inc_res) - STEP:
            inc, inc_res = c, r
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(f"|  | **덜어냄 받아들임: {axis}={v}** |  |  |  |  |  |  |\n")
    if not (ann(inc_res) > base_ann + ADOPT_MARGIN and inc_res["kinds_ok"]):
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
