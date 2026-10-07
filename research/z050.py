"""추천 세 판(공격 · 균형 · 보수)을 숫자로 정하기 — 날마다 평가한 세 흐름을 섞은 계좌.
A = 지금 운영 조합(1일봉 새 82 + 빈칸 엔진 · 인버스 · a_mtm 날마다 평가) · B = F5 공매도 비중 낮음 위 20(달마다 · 비용 0.5%) ·
D = 사건 바구니 C 8칸(공시 다음 날 · 20일 · 비용 0.5%). 섞기: 날마다 그 몫으로 맞춘다고 봄(어림 · 다시 맞추는 비용 뺌).
판: A · B · D · A50+B50 · A50+D50 · B50+D50 · A34+B33+D33 · A70+D30.
python research/z050.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a_mtm  # noqa: E402
import perf as P  # noqa: E402
import z001 as Z  # noqa: E402
from z046 import build, simulate  # noqa: E402
from z047 import run  # noqa: E402

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")


def main():
    z = np.load(SP / "dd_now.npz")
    D0 = [str(d) for d in z["days"]]
    A = pd.Series(a_mtm.account(D0, json.load(open(SP / "x008_d1.json")), z["mix"] - z["d1"]), index=D0)
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, _ = Z.universe(C)
    B = run(C, inside, -X["공매도20"], 20, 0.005)
    Cc = C[C.index >= "20161001"]
    Fc = {k: v.reindex(Cc.index) for k, v in F.items()}
    ev = build(Cc, Fc, evs, inside.reindex(Cc.index), ("자사주취득", "무상증자"))
    ev = ev[((ev["갈래"] == "자사주취득") & (ev["반응"] < -0.02)) | (ev["갈래"] == "무상증자")]
    Dd, _ = simulate(Cc, ev, 8, 20, 1, 0.005)
    idx = sorted(set(A.index) & set(B.index) & set(Dd.index))
    A, B, Dd = A.reindex(idx).fillna(0), B.reindex(idx).fillna(0), Dd.reindex(idx).fillna(0)
    print(f"날마다 수익 상관(2017 ~): A·B {A[A.index >= '20170201'].corr(B[B.index >= '20170201']):+.2f} · A·D {A.corr(Dd):+.2f} · B·D {B.corr(Dd):+.2f}")
    mixes = {"A 운영 조합(1일봉 + 엔진)": A, "B 공매도 낮음 위 20": B, "D 바구니 C 8칸": Dd, "A50 + B50": .5 * A + .5 * B, "A50 + D50": .5 * A + .5 * Dd,
             "B50 + D50": .5 * B + .5 * Dd, "A34 + B33 + D33": .34 * A + .33 * B + .33 * Dd, "A70 + D30": .7 * A + .3 * Dd}
    H = (("앞 2017 ~ 21", "20170201", "20220101"), ("뒤 2022 ~ 26", "20220101", "20991231"), ("시험 2023 ~", "20230101", "20991231"))
    for lab, r in mixes.items():
        print(f"== {lab} ==")
        for h, lo, hi in H:
            s = P.account_stats(r, lo, hi)
            x = r[(r.index >= lo) & (r.index < hi)]
            print(f"  {h}: {P.fmt(s)} · 나쁜 하루 {x.min() * 100:.1f}%", flush=True)


if __name__ == "__main__":
    main()
