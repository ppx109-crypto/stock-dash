"""BRK-FLOW-0044 개발 실행기 — PLAN round 2 고침 1(유한 실험 공간 · 좌표 하강 · 멈춤 · 덜어냄 · 최종 후보)을 그대로 코드로 따름.
- 축 · 값 · 순서는 PLAN에 적은 그대로입니다. 평가는 brk_dev.evaluate()(STARTED 기록 · 상한 200)로만 합니다.
- 받아들이기: brk_dev.accept()(보탬 · 덜어냄) · 여러 값 통과 시 'D1 · D2 연수익 차의 작은 쪽' 큰 순 · 같으면 표의 앞 값 · 고원(격자 이웃 ③).
- 같은 설정은 한 번만 평가(이미 본 값은 결과를 다시 씀).
python3 research/brk_rules.py            → 끝나면 최종 후보 설정과 결과를 출력 · LOG.md에 판마다 한 줄"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash/research")
import brk_dev as D  # noqa: E402

LOG = D.BOX / "LOG.md"
AXES = [("hb", [20, 40, 60, 120]), ("flown", [3, 5, 10]), ("cols", ["FT", "F", "FI"]), ("mkt", ["none", "br40", "br50", "ix200"]),
        ("take", [5, 8, 12]), ("stop", [5, 7, 10]), ("days", [10, 20]), ("size", [2, 3])]
COLS = {"FT": ("외국인", "투신"), "F": ("외국인",), "FI": ("외국인", "기관")}
R0 = {"hb": 60, "flown": 5, "cols": "FT", "mkt": "none", "take": 5, "stop": 7, "days": 10, "size": 2, "flow": True}
MAX_PASS = 3


def high_break(r, n):
    c = D.LANES[r["code"]]["closes"]
    i = r["i"]
    return i >= n and c[i] >= max(c[i - n:i])


def ix_above(day, n=200):
    import bisect
    k = bisect.bisect_right(D.IXD, day) - 1
    if k < n - 1:
        return False
    return D.IX[D.IXD[k]] > sum(D.IX[D.IXD[j]] for j in range(k - n + 1, k + 1)) / n


def rel20(r):
    a, b = D.ret(r, 20), D.ix_ret(r["date"], 20)
    return (a - b) if a is not None and b is not None else 0.0


def market_ok(r, m):
    if m == "none":
        return True
    if m == "ix200":
        return ix_above(r["date"])
    return D.BR.get(r["date"], 0) >= (40 if m == "br40" else 50)


def build(cfg):
    def holds(r):
        if not high_break(r, cfg["hb"]) or not market_ok(r, cfg["mkt"]):
            return False
        if not cfg["flow"]:
            return True
        vals = [D.flow_sum(r, cfg["flown"], c) for c in COLS[cfg["cols"]]]
        return None not in vals and all(v > 0 for v in vals)
    return holds, D.next_exit(cfg["take"], cfg["stop"], cfg["days"]), (lambda r, k=cfg["size"]: k), (lambda r: -rel20(r))


def key(cfg):
    return json.dumps(cfg, sort_keys=True, ensure_ascii=False)


SEEN = {}


def run(cfg, note):
    k = key(cfg)
    if k in SEEN:
        return SEEN[k]
    holds, exits, size, rank = build(cfg)
    res = D.evaluate(k, holds, exits, size=size, rank=rank, note=note)
    SEEN[k] = res
    n = D._started()
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"| {n} | {note} | {cell(res.get('D1'))} | {cell(res.get('D2'))} |\n")
    print(n, note, D.line("", res), flush=True)
    return res


def cell(x):
    if not x:
        return "60건 미만"
    y = " · ".join(f"{k[2:]}:{v}" for k, v in sorted((x.get("해마다") or {}).items()))
    return f"{x['매매']} · {x['연수익']} · {x['폭']} · {x['최대낙폭']} · {x['행운뺌']} · {x['큰2건뺌']} · 해마다 {y}"


def mindiff(c, i):
    return min(c["D1"]["연수익"] - i["D1"]["연수익"], c["D2"]["연수익"] - i["D2"]["연수익"])


def plateau(cfg, axis, values, inc_res):
    k = values.index(cfg[axis])
    for j in (k - 1, k + 1):
        if 0 <= j < len(values):
            nb = dict(cfg, **{axis: values[j]})
            res = run(nb, f"고원 이웃 {axis}={values[j]}")
            for h in ("D1", "D2"):
                c, i = res.get(h), inc_res.get(h)
                if not c or not i or c["행운뺌"] < i["행운뺌"] or c["큰2건뺌"] < i["큰2건뺌"]:
                    if nb != INC[0]:
                        return False
    return True


INC = [None]


def main():
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write("\n| 번호 | 판(바꾼 것) | D1 매매 · 연 · 폭 · 골 · 행운뺌 · 큰2뺌 · 해마다 | D2 같은 칸 |\n|---|---|---|---|\n")
    inc = dict(R0)
    inc_res = run(inc, "R0 출발점")
    INC[0] = inc
    for p in range(1, MAX_PASS + 1):
        any_acc = False
        for axis, values in AXES:
            cands = []
            for v in values:
                if v == inc[axis]:
                    continue
                cfg = dict(inc, **{axis: v})
                res = run(cfg, f"{p}바퀴 {axis}={v}")
                ok, _ = D.accept(res, inc_res)
                if ok:
                    cands.append((mindiff(res, inc_res), -values.index(v), cfg, res))
            for _, _, cfg, res in sorted(cands, key=lambda z: (z[0], z[1]), reverse=True):
                if plateau(cfg, axis, values, inc_res):
                    inc, inc_res = cfg, res
                    INC[0] = inc
                    any_acc = True
                    with LOG.open("a", encoding="utf-8") as fh:
                        fh.write(f"|  | **받아들임: {axis}={cfg[axis]}** → 채택판 {key(inc)} |  |  |\n")
                    break
                with LOG.open("a", encoding="utf-8") as fh:
                    fh.write(f"|  | 봉우리(고원 이웃 ③ 못 함): {axis}={cfg[axis]} |  |  |\n")
        if not any_acc:
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(f"|  | {p}바퀴에서 받아들인 값 없음 → 멈춤 |  |  |\n")
            break
    # 덜어냄 점검
    for name, cfg in (("시장 거르기 없음", dict(inc, mkt="none")), ("수급 조건 뺌", dict(inc, flow=False))):
        if cfg == inc:
            continue
        res = run(cfg, f"덜어냄: {name}")
        ok, _ = D.accept(res, inc_res, removal=True)
        if ok:
            inc, inc_res = cfg, res
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(f"|  | **덜어냄 받아들임: {name}** |  |  |\n")
    out = {"final": inc, "final_res": inc_res, "evals": D._started()}
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## 개발 끝 · 최종 후보\n- {key(inc)}\n- 평가 판 {D._started()} / 200\n")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
