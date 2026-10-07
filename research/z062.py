"""P13 — 바구니 C 효과가 '늦은(장 뒤) 공시'에서 오나(docs/RL-PRO.md · 2차 보고서 §6 · §18-2).
DART 접수 시각이 없으므로 접수번호 뒤 6자리(그날 DART 전체 접수 순서)를 시각 대신 씀: 갈래(자사주 · 무상)마다 가운데값으로 '이른 절반' · '늦은 절반'(미리 정함).
바구니 C 사건(쪼개기 고친 시총 200위 · z046.build · 자사주는 반응 < −2%)마다: t0 반응 · t0+1 반응(초과) · t0+1 종가 사기 → 20거래일 초과(그날 200위 가운데값 뺌).
늦은 공시라면 t0 반응은 '공시 전' 움직임이고 진짜 반응은 t0+1에 나와야 함 → 두 절반의 t0+1 반응 크기로 대리 변수가 맞는지 먼저 봄.
python research/z062.py
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
from z046 import build  # noqa: E402

caps.ADJ = True
KMAP = {"자사주취득": "자기주식취득", "무상증자": "무상증자"}


def serials():
    out = {}
    for p in Path("dart-events").glob("*.json"):
        b = json.loads(p.read_text(encoding="utf-8"))
        for k, dk in KMAP.items():
            for x in (b.get("rows") or {}).get(dk) or []:
                no = str(x.get("rcept_no", ""))
                if len(no) == 14:
                    key = (p.stem, k, no[:8])
                    out[key] = min(out.get(key, 10 ** 9), int(no[8:]))
    return out


def main():
    C, F, ops, evs, qs, name = Z.load()
    inside, _ = Z.universe(C)
    Cc = C[C.index >= "20161001"]
    Fc = {k: v.reindex(Cc.index) for k, v in F.items()}
    ev = build(Cc, Fc, evs, inside.reindex(Cc.index), ("자사주취득", "무상증자"))
    ev = ev[((ev["갈래"] == "자사주취득") & (ev["반응"] < -0.02)) | (ev["갈래"] == "무상증자")].copy()
    days = list(Cc.index)
    S = serials()
    # 접수일 = t0 이거나 그 앞 며칠(주말 접수) — t0 앞 4일 안에서 찾음
    def ser(r):
        for back in range(0, 5):
            d = (pd.Timestamp(r.날) - pd.Timedelta(days=back)).strftime("%Y%m%d")
            v = S.get((r.코드, r.갈래, d))
            if v is not None:
                return v
        return np.nan
    ev["순서"] = [ser(r) for r in ev.itertuples()]
    r1 = Cc / Cc.shift(1) - 1
    ins = inside.reindex(Cc.index)
    ex1 = r1.sub(r1.where(ins).median(axis=1), axis=0)
    f20 = Cc.shift(-21) / Cc.shift(-1) - 1
    ex20 = f20.sub(f20.where(ins).median(axis=1), axis=0)
    ev["반응t1"] = [ex1.iat[r.j + 1, Cc.columns.get_loc(r.코드)] if r.j + 1 < len(days) else np.nan for r in ev.itertuples()]
    ev["뒤20"] = [ex20.iat[r.j, Cc.columns.get_loc(r.코드)] for r in ev.itertuples()]
    base = float(np.nanmean(ex20.where(ins).to_numpy()))
    print(f"바구니 C 사건 {len(ev)} · 접수 순서 찾음 {int(ev['순서'].notna().sum())} · 바탕(아무 종목 20일 초과 평균) {base * 100:+.2f}%", flush=True)
    ev = ev.dropna(subset=["순서"])
    ev["늦음"] = ev.groupby("갈래")["순서"].transform(lambda s: s > s.median())
    ev["기간"] = np.select([ev["날"] < "20210101", ev["날"] < "20230101"], ["학습", "검증"], "시험")
    for k in ("자사주취득", "무상증자", None):
        sub = ev if k is None else ev[ev["갈래"] == k]
        print(f"== {k or '둘 다'} · 순서 가운데값 {sub['순서'].median():.0f} ==", flush=True)
        for late, lab in ((False, "이른 절반"), (True, "늦은 절반")):
            s = sub[sub["늦음"] == late]
            cells = []
            for p in ("학습", "검증", "시험"):
                x = s[s["기간"] == p]["뒤20"].dropna() - base
                cells.append(f"{p} {len(x)}건 {x.mean() * 100:+.2f}%p(나을 {(x > 0).mean():.0%})" if len(x) else f"{p} 0건")
            x = s["뒤20"].dropna() - base
            t = x.mean() / (x.std() / np.sqrt(len(x))) if len(x) > 2 else np.nan
            print(f"  {lab}: t0 반응 {s['반응'].mean() * 100:+.2f}% · t0+1 반응 {s['반응t1'].mean() * 100:+.2f}% | 뒤 20일 전체 {len(x)}건 {x.mean() * 100:+.2f}%p(t {t:+.1f}) | " + " · ".join(cells), flush=True)


if __name__ == "__main__":
    main()
