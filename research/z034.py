"""오푸스 2차 검토 ① — 손실 한도를 '날마다 평가'로 다시(사용자 한도: 하루 · 한 달 −15% · 계좌 전체).
지금까지 한도 참고값(가장 나쁜 하루 −4.7% · 달 −9.6%)은 i013 덤프(1일봉 손익을 판 날에만 적음)로 셈 → 들고 있는 동안 평가 손실이 빠짐.
여기선 a_mtm.account(산 날 몫만큼 사서 값대로 오르내림 · 판 날 장부 손익에 맞춤)로 날마다 평가한 계좌를 씀.
판: (가) 판 날 셈(지금까지) (나) 날마다 평가 — 1일봉 + 빈칸 엔진 · 인버스(운영 조합) (다) (나) + 사건 바구니 C(1일봉 몫의 쉬는 돈 · 바구니 먼저)
기간: 앞 2017 ~ 21 · 뒤 2022 ~ 26 · 2026만. 나쁜 하루 · 나쁜 달 · 골 · 연(복리).
python research/z034.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a_mtm  # noqa: E402

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")


def stats(r, lo, hi):
    x = r[(r.index >= lo) & (r.index < hi)]
    e = (1 + x).cumprod()
    mon = (1 + x).groupby(pd.to_datetime(x.index).to_period("M")).prod() - 1
    return (f"연 {(e.iloc[-1] ** (245 / len(x)) - 1) * 100:+6.1f}% · 골 {(e / e.cummax() - 1).min() * 100:6.1f}% · "
            f"나쁜 하루 {x.min() * 100:5.1f}%({x.idxmin()}) · 나쁜 달 {mon.min() * 100:6.1f}%({mon.idxmin()}) · −15% 넘은 달 {int((mon < -0.15).sum())}")


def main():
    z = np.load(SP / "dd_now.npz")
    D = [str(d) for d in z["days"]]
    led = json.load(open(SP / "x008_d1.json"))
    mtm = pd.Series(a_mtm.account(D, led, z["mix"] - z["d1"]), index=D)
    sold = pd.Series(z["mix"], index=D)
    out = {"(가) 판 날 셈(지금까지 한도 참고)": sold, "(나) 날마다 평가 · 운영 조합": mtm}
    bk = SP / "z021_full.csv"
    if bk.exists():                                  # P4b 자르기 시험 때 남긴 바구니 날마다 수익(문턱 −2% · 5칸 · 20일)
        b = pd.read_csv(bk, index_col=0, dtype={0: str})
        b.index = b.index.astype(str)
        r, inv = b["r"].reindex(D).fillna(0.0), b["inv"].reindex(D).fillna(0.0)
        used = pd.Series(z["used"], index=D)
        pf = (1 - used).clip(0, 1).shift(1).fillna(1.0)
        eng = pd.Series(z["mix"] - z["d1"], index=D)
        out["(다) (나) + 사건 바구니 C"] = mtm - eng + eng * (1 - inv.shift(1).fillna(0.0)) + pf * r
    for lab, s in out.items():
        print(f"[{lab}]")
        for h, lo, hi in (("앞 2017~21", "20170101", "20220101"), ("뒤 2022~26", "20220101", "20991231"), ("2026", "20260101", "20991231")):
            print(f"   {h}: {stats(s, lo, hi)}", flush=True)


if __name__ == "__main__":
    main()
