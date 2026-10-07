"""감사 A4 — 바구니 C '사건'에 섞인 공시 종류(본 공시 · 정정 · 매매거래정지 안내 · 자회사 공시)별 성적(운영 · 연구 같은 정의 · 옛 시총 = 운영 그대로).
event-data 제목으로 갈래를 나눔 · 20거래일 겹침 거르기 뒤 남은 '그날 첫 사건'의 제목 · t0 = 접수일 · 반응 = t0 초과(200위 가운데값 뺌) ·
바구니 C 조건(자사주는 반응 < −2%) · t0+1 종가 → 20거래일 초과 − 바탕(아무 종목 · 날 같은 20일 초과 평균).
python research/z071.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import caps  # noqa: E402
import z001 as Z  # noqa: E402

caps.ADJ = False


def cat(t):
    return "정정" if "정정" in t else "권리락" if "권리락" in t else "매매거래정지" if "거래정지" in t else "자회사·종속" if ("자회사" in t or "종속" in t) else "본 공시"


def main():
    C, *_ = Z.load()
    inside, _ = Z.universe(C)
    days = list(C.index)
    r1 = C / C.shift(1) - 1
    react = r1.sub(r1.where(inside).median(axis=1), axis=0)
    f = C.shift(-21) / C.shift(-1) - 1
    ex = f.sub(f.where(inside).median(axis=1), axis=0)
    base = float(np.nanmean(ex.where(inside).to_numpy()))
    rows = []
    for c in C.columns:
        p = Path("event-data") / f"{c}.json"
        if not p.exists():
            continue
        evs = sorted((r["date"], r["kind"], r["title"]) for r in json.loads(p.read_text(encoding="utf-8"))["rows"]
                     if r.get("kind") in ("자사주취득", "무상증자") and r.get("date", "") >= "20170101")
        last = {}
        k_ = C.columns.get_loc(c)
        for d, kind, t in evs:
            j = int(np.searchsorted(days, d))
            if j + 22 >= len(days) or not inside.iat[j, k_]:
                continue
            if kind in last and j - last[kind] < 20:
                continue
            rx = react.iat[j, k_]
            if not np.isfinite(rx):
                continue
            last[kind] = j
            if kind == "자사주취득" and not rx < -0.02:
                continue
            rows.append((kind, cat(t), days[j], ex.iat[j, k_] - base))
    D = pd.DataFrame(rows, columns=["갈래", "종류", "날", "초과"]).dropna()
    D["기간"] = np.select([D["날"] < "20210101", D["날"] < "20230101"], ["2017 ~ 20", "2021 ~ 22"], "2023 ~ 26")
    print(f"바구니 C 사건(200위 · 옛 시총 · 운영 정의) {len(D)} · 바탕 20일 초과 {base * 100:+.2f}%", flush=True)
    for (k, c_), g in D.groupby(["갈래", "종류"]):
        cells = " | ".join(f"{p} {len(x)}건 {x['초과'].mean() * 100:+.2f}%p" for p, x in g.groupby("기간"))
        t = g["초과"].mean() / (g["초과"].std() / np.sqrt(len(g))) if len(g) > 2 else np.nan
        print(f"  {k} · {c_}: {len(g)}건 평균 {g['초과'].mean() * 100:+.2f}%p(중앙 {g['초과'].median() * 100:+.2f} · 나을 {(g['초과'] > 0).mean():.0%} · t {t:+.1f}) | {cells}", flush=True)


if __name__ == "__main__":
    main()
