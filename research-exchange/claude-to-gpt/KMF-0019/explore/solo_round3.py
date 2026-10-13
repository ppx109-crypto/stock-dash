"""KMF-0019 탐색 7 — 신규봇(W 출구판) 혼자: 하루 멈춤 DS · KMF 누적 내림 쉼(X, P) 으로 MDD ≤ −15p 되는지. python3 solo_round3.py"""
import itertools, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exit_lab as E  # noqa: E402
K, M13, M14, M15, M16, M17, D = E.K, E.M13, E.M14, E.M15, E.M16, E.M17, E.D
if __name__ == "__main__":
    rows = K._rows_before(M17.END); b = M17.prep(rows)
    T = M16.intent(b, M13.signals(b, M13.grid()[0])); R = M16.intent(b, M14.signals(b, M14.grid()[0])); W = M16.intent(b, M15.signals(b, M15.grid()[0]))
    itW = E.intents(b, "W", T, R, W); res = []
    rules = [("none",)] + [("dd", x, p) for x in (6, 10, 15) for p in (3, 5, 10)] + [("mo", 10), ("mo", 15), ("wk", 6), ("wk", 10)]
    for N, B, n, ds in itertools.product((0, 10, 20, 30), (0, 1), (10, 15, 20), (25, 10, 6)):
        days, _ = E.run(rows, itW, N, B, n, 1, ds, (40, 15))
        for rule in rules:
            s = D.summ(D.throttle(days, rule))
            res.append({"판": f"W_N{N}_B{B}_n{n}_DS{ds}_{'_'.join(map(str, rule))}", **s})
    (HERE / "solo_round3_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res)); res.sort(key=lambda x: -x["MDD"])
    for x in res[:8]: print(json.dumps(x, ensure_ascii=False))
    for lim in (-15, -20, -25):
        c = [x for x in res if x["MDD"] >= lim]; print("MDD", lim, "이내", len(c))
        for x in sorted(c, key=lambda x: -x["합계"])[:4]: print("  ", json.dumps(x, ensure_ascii=False))
