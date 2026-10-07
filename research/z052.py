"""N13 — 새로 찾은 두 흐름이 좁은 장(시장 폭 < 50)에서도 버티나(docs/RL-NARROW.md · 퀀트 보고서 F5 · 바구니 C).
흐름: F5 = 공매도 비중(20일 평균) 낮은 위 20(달마다 · 비용 0.5% · z047.run) · C = 사건 바구니 C 5칸(z046 · 공시 다음 날 · 20일 · 비용 0.5%)
     · 바탕 = 그날 시총 200위 똑같이(z047.run에 모든 종목 같은 점수 → 위 200).
국면은 **어제(t−1) 값**으로 그날 수익을 나눔(그날 아침에 알 수 있는 국면): 넓은 장 · 좁은 오름장 · 내림장(z008.regimes).
기간: 2017 ~ 19 · 2020 ~ 22 · 2023 ~ 26. 수치 = 그 국면 날들만 이어 붙인 연율 · 바탕과의 차(%p) · 날 수.
python research/z052.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402
from z008 import period, regimes  # noqa: E402
from z046 import build, simulate  # noqa: E402
from z047 import run  # noqa: E402


def ann(r):
    return (np.prod(1 + r.to_numpy()) ** (252 / len(r)) - 1) * 100 if len(r) else np.nan


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, size = Z.universe(C)
    reg, breadth = regimes(C, size)
    prev = reg.shift(1)
    S = {"F5 공매도 낮음 위 20": run(C, inside, -X["공매도20"], 20, 0.005),
         "바탕 200위 똑같이": run(C, inside, pd.DataFrame(1.0, index=C.index, columns=C.columns).where(C.notna()), 200, 0.005)}
    Cc = C[C.index >= "20161001"]
    Fc = {k: v.reindex(Cc.index) for k, v in F.items()}
    ev = build(Cc, Fc, evs, inside.reindex(Cc.index), ("자사주취득", "무상증자"))
    ev = ev[((ev["갈래"] == "자사주취득") & (ev["반응"] < -0.02)) | (ev["갈래"] == "무상증자")]
    S["바구니 C 5칸"], _ = simulate(Cc, ev, 5, 20, 1, 0.005)
    z = np.load(Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/dd_now.npz"))
    S["빈칸 엔진(운영 · 계좌 기여)"] = pd.Series(z["mix"] - z["d1"], index=[str(d) for d in z["days"]])   # 폭 < 50 날엔 대개 계좌 거의 전부를 씀
    idx = [d for d in C.index if d >= "20170201"]
    S = {k: v.reindex(idx).fillna(0.0) for k, v in S.items()}
    per = pd.Series([period(d) for d in idx], index=idx)
    pr = prev.reindex(idx)
    base = S["바탕 200위 똑같이"]
    for rg in ("넓은 장", "좁은 오름장", "내림장"):
        print(f"== 어제 국면 {rg} ==", flush=True)
        for lab in ("F5 공매도 낮음 위 20", "바구니 C 5칸", "빈칸 엔진(운영 · 계좌 기여)", "바탕 200위 똑같이"):
            r = S[lab]
            cells = []
            for p in ("2017~19", "2020~22", "2023~26"):
                m = (pr == rg) & (per == p)
                a, b = ann(r[m]), ann(base[m])
                cells.append(f"{p} {a:+6.1f}%({a - b:+5.1f}p · {int(m.sum())}일)")
            m = pr == rg
            hit = ((r[m] - base[m]) > 0).mean()
            print(f"  {lab:22s} " + " | ".join(cells) + f" | 바탕 이긴 날 {hit:.0%}", flush=True)


if __name__ == "__main__":
    main()
