"""N15 — 내림장(어제 폭 < 50 · 코스피 < 60일선) 날 빈칸 엔진 몫의 절반 · 전부를 바구니 C(5칸 · 8칸)로(docs/RL-NARROW.md).
계좌: 1일봉 '새 82'(쪼개기 고친 시총 · z055_d1_adj · BASE 비용) 날마다 평가 + 바깥 몫.
바깥 몫 = 엔진(dd_now.npz mix − d1) · 바꾼 판: 내림장 날만 엔진 × 0.5 + (1 − 1일봉 쓴 몫) × 0.5 × 바구니 C 날마다 수익(z054_adj.npz · BASE) 등.
잣대: 고르기 2017 ~ 22 · 시험 2023 ~ 26 · 하루 · 달 −15% · 날마다 수익 상관.
CAPS_ADJ=1 NRL_CACHE=.../nrl-cache-adj.pkl python research/z064.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import a_mtm  # noqa: E402
import caps  # noqa: E402
import perf2 as P  # noqa: E402
import z001 as Z  # noqa: E402
from z008 import regimes  # noqa: E402
from z058 import recost  # noqa: E402

caps.ADJ = True
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")


def main():
    import nrl
    z = np.load(SP / "dd_now.npz")
    D0 = [str(d) for d in z["days"]]
    eng, used = z["mix"] - z["d1"], z["used"]
    f5 = np.load(SP / "z054_adj.npz")
    idx = [str(d) for d in f5["days"]]
    D5 = pd.Series(f5["D 바구니 C 5칸"], index=idx).reindex(D0).fillna(0).to_numpy()
    D8 = pd.Series(f5["D 바구니 C 8칸"], index=idx).reindex(D0).fillna(0).to_numpy()
    C, *_ = Z.load()
    inside, size = Z.universe(C)
    reg, br = regimes(C, size)
    narrow = (reg.shift(1).reindex(D0) == "내림장").to_numpy()
    on = narrow & (np.abs(eng) > 0)
    led, _ = recost(json.load(open(SP / "z055_d1_adj.json")), 1.0)
    out = {}
    free = np.clip(1 - used, 0, 1)
    for lab, base in (("지금(엔진 그대로)", eng), ("내림장: 엔진 50 + 바구니 C 8칸 50", np.where(on, 0.5 * eng + 0.5 * free * D8, eng)),
                      ("내림장: 바구니 C 8칸 100", np.where(on, free * D8, eng)), ("내림장: 엔진 50 + 바구니 C 5칸 50", np.where(on, 0.5 * eng + 0.5 * free * D5, eng))):
        out[lab] = pd.Series(a_mtm.account(D0, led, base, nrl.prices), index=D0)
    print(f"내림장 · 엔진 켜진 날 {int(on.sum())}", flush=True)
    for lab, r in out.items():
        print(f"== {lab} ==", flush=True)
        for h, lo, hi in (("고르기 2017 ~ 22", "20170201", "20230101"), ("시험 2023 ~ 26", "20230101", "20991231"), ("전체", "20170201", "20991231")):
            print(f"  {h:14s} {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)
        m = pd.Series(on, index=D0)
        print(f"  내림장 · 엔진 날만 연율: 고르기 {r[m & (r.index < '20230101')].mean() * 245 * 100:+.1f}% · 시험 {r[m & (r.index >= '20230101')].mean() * 245 * 100:+.1f}%", flush=True)


if __name__ == "__main__":
    main()
