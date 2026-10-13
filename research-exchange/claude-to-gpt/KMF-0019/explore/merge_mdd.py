"""KMF-0019 탐색 5 — exit_lab 상위 판을 v12a와 1계약 합병(v12a 우선 · KMF 몫 하루 한도 C)했을 때 계좌 MDD.
python3 merge_mdd.py <v12a 원장>"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exit_lab as E  # noqa: E402
K, M13, M14, M15, M16, M17, MC, ML, D, L = E.K, E.M13, E.M14, E.M15, E.M16, E.M17, E.MC, E.ML, E.D, E.L


def parse(tag):
    p = tag.split("_")
    comp = p[0]; N = int(p[1][1:]); B = int(p[2][1:]); n = int(p[3][1:]); X = int(p[4][1:]); DS = int(p[5][2:])
    LK = None if p[6] == "LKNone" else (40, 15)
    return comp, N, B, n, X, DS, LK


if __name__ == "__main__":
    rows = K._rows_before(M17.END); b = M17.prep(rows)
    T = M16.intent(b, M13.signals(b, M13.grid()[0])); R = M16.intent(b, M14.signals(b, M14.grid()[0])); W = M16.intent(b, M15.signals(b, M15.grid()[0]))
    vs = ML.v12a_spans(sys.argv[1], rows)
    V = []
    for r in rows:
        v = 0
        for e, x, s, _ in vs.get(r[0], []):
            if e <= r[1] < x:
                v = s
        V.append(v)
    vd, _ = MC.sim(rows, V, [0] * len(V), 999)
    print("v12a만", json.dumps(D.summ(vd), ensure_ascii=False))
    res = json.loads((HERE / "exit_lab_out.json").read_text())
    pick = sorted(res, key=lambda x: -x["MDD"])[:25] + sorted(res, key=lambda x: -x["합계"])[:10]
    pick.append([r for r in res if r["판"] == "TRW_N0_B0_n0_X1_DS25_LK(40, 15)"][0])
    seen, out = set(), []
    for r in pick:
        if r["판"] in seen:
            continue
        seen.add(r["판"])
        comp, N, B, n, X, DS, LK = parse(r["판"])
        _, desire = E.run(rows, E.intents(b, comp, T, R, W), N, B, n, X, DS, LK)
        for cap in (999, 10, 5, 3):
            dd, _ = MC.sim(rows, V, desire, cap)
            s = D.summ(dd)
            out.append({"판": r["판"], "KMF몫": cap, "혼자 합계": r["합계"], "혼자 MDD": r["MDD"], "합병 합계": s["합계"], "합병 MDD": s["MDD"],
                        "합병 하루 최악": s["하루 최악"], "합병 가장 나쁜 달": s["가장 나쁜 달"], "합병 177일": s["177일"]})
    (HERE / "merge_mdd_out.json").write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print("합병 판 수", len(out))
    out.sort(key=lambda x: -x["합병 MDD"])
    for x in out[:15]:
        print(json.dumps(x, ensure_ascii=False))
    for lim in (-10, -12, -15, -20, -25):
        c = [x for x in out if x["합병 MDD"] >= lim]
        if c:
            x = max(c, key=lambda x: x["합병 합계"]); print("합병 MDD", lim, "이내 최고:", json.dumps(x, ensure_ascii=False))
