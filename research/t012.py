"""D1-F7C-0043 — 1일봉 개발 전 기간(2006 ~ 2016) 부진이 '대상 고르는 방법' 탓인지 '시기' 탓인지 가름(F7c).
사전등록: research-exchange/claude-to-gpt/D1-F7C-0043/PREREG.md
- F7b(research/f007b.py)와 같은 방법: investor-full 종목 · 그날 순위 = 전날까지 20일 평균 거래대금 · 하루 100위 · 수급 investor-full(전날까지).
- 이번에는 같은 방법을 2017 ~ 2020 · 2021 ~ 2026-09-16에도 돌려, 공식(시총 100위) 수치와 견줌.
- 판 2개: B 지금 1일봉(새 82 · BASE_HOLD/EXIT/SIZE) · S1 쉬운 판(D1-SIMPLE-0041 t011 그대로).
- 엔진: lab.wobble 씨앗 8 · 신호 날 종가 · realistic · cap 130 · 왕복 0.25% · rule.order.
python3 research/t012.py"""
import bisect
import glob
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import caps  # noqa: E402
import final_study as FS  # noqa: E402
import lab  # noqa: E402
import nrl  # noqa: E402
import t011  # noqa: E402

rule = nrl.rule
LO_D, HI_D = "20051001", "20260917"
SPANS = (("2006 ~ 2010", "20060101", "20110101"), ("2011 ~ 2016", "20110101", "20170101"),
         ("2017 ~ 2020", "20170101", "20210101"), ("2021 ~", "20210101", "20260917"))


def main():
    t0 = time.time()
    codes = sorted(Path(p).stem for p in glob.glob("investor-full/*.json"))
    codes = [c for c in codes if c in nrl.prices]
    rows = []
    for k in range(0, len(codes), 25):
        part = {c: nrl.prices[c] for c in codes[k:k + 25]}
        for r in lab.build(part, horizons=(0,)):
            if LO_D <= r["date"] < HI_D:
                r.pop("ahead", None)
                rows.append(r)
    TV = {}
    for c in codes:
        v = json.loads(Path(f"volume-data/{c}.json").read_text(encoding="utf-8"))["날"]
        ds = [x[0] for x in v]
        acc = np.concatenate([[0.0], np.cumsum([x[2] if len(x) > 2 and x[2] else 0.0 for x in v])])
        TV[c] = (ds, acc)

    def tv20(code, day):
        ds, acc = TV[code]
        k = bisect.bisect_left(ds, day)          # 전날까지
        return (acc[k] - acc[k - 20]) / 20 if k >= 20 else None

    by_day = {}
    for r in rows:
        v = tv20(r["code"], r["date"])
        if v:
            r["_tv"] = v
            by_day.setdefault(r["date"], []).append(r)
    for d, rs in by_day.items():
        rs.sort(key=lambda x: -x["_tv"])
        for place, x in enumerate(rs, 1):
            x[caps.RANK] = place
    nrl.shape.update(FS.shapes(nrl.lanes, [c for c in codes if c not in nrl.shape]))
    for d, v in FS.breadth_by_day(rows, nrl.shape).items():
        nrl.BR.setdefault(d, v)          # 2017 ~ 은 공식 시장 폭 그대로(규칙 정의) · 그 앞만 이 대상으로
    for c in codes:
        body = json.loads(Path(f"investor-full/{c}.json").read_text(encoding="utf-8"))
        cols = body["cols"]
        fr = [dict(zip(cols, r)) for r in body["rows"] if r[0] < "20170101"]
        old = nrl.FLOW.get(c)
        if old:
            days, acc, ok, closes = old
            tail = [{"date": d, **{col: acc[col][i + 1] - acc[col][i] for col in nrl.COLS}, "종가": closes[i]}
                    for i, d in enumerate(days)]
            fr = fr + [x for x in tail if x["date"] >= "20170101"]
        nrl.FLOW[c] = nrl.flow_entry(fr)
    pool = [r for r in rows if caps.inside(r, rule.TOP) and r["date"] >= "20060101"]
    ways = t011.build(nrl)
    out = {"task": "D1-F7C-0043", "round": 1, "codes": len(codes), "pool_rows": len(pool),
           "per_day": round(len(pool) / max(1, len({r['date'] for r in pool})), 1)}
    for tag in ("B", "S1"):
        w = ways[tag]
        out[tag] = {}
        for name, lo, hi in SPANS:
            sub = [r for r in pool if lo <= r["date"] < hi]
            g = lab.wobble(sub, nrl.prices, w["holds"], w["exits"], tries=8, slots=nrl.SLOTS, since=lo, apart=nrl.kin,
                           realistic=True, cap=130, detail=True, size=w["size"], rank=rule.order, cost=0.25)
            if not g:
                out[tag][name] = None
                continue
            s, a, b = nrl.luck(g, nrl.SLOTS, lo)
            out[tag][name] = {k: g.get(k) for k in ("매매", "연수익", "폭", "최대낙폭", "골 폭", "가동률", "승률", "해마다")}
            out[tag][name].update({"행운뺌": a, "큰2건뺌": b})
            print(tag, name, json.dumps(out[tag][name], ensure_ascii=False), file=sys.stderr, flush=True)
    out["초"] = round(time.time() - t0)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
