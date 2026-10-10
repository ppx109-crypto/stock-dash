"""D1-F7C-0043 — 1일봉 개발 전 기간(2006 ~ 2016) 부진이 '대상 고르는 방법' 탓인지 '시기' 탓인지 가름(F7c).
사전등록: research-exchange/claude-to-gpt/D1-F7C-0043/PREREG.md
- F7b(research/f007b.py)와 같은 방법: investor-full 종목 · 그날 순위 = 전날까지 20일 평균 거래대금 · 하루 100위 · 수급 investor-full(전날까지).
- 이번에는 같은 방법을 2017 ~ 2020 · 2021 ~ 2026-09-16에도 돌려, 공식(시총 100위) 수치와 견줌.
- 판 2개: B 지금 1일봉(새 82 · BASE_HOLD/EXIT/SIZE) · S1 쉬운 판(D1-SIMPLE-0041 t011 그대로).
- 엔진: lab.wobble 씨앗 8 · 신호 날 종가 · realistic · cap 130 · 왕복 0.25% · rule.order.
- round 2(GPT #194 6095763346):
  1. 셈 전에 자료 · 코드 잠금(lock.json)을 다시 세어 다르면 멈춤(캐시 · 표 · investor-full · volume-data · investor-data · opinion-data · 코드).
  2. 기간마다 일봉을 그 기간 끝 날까지로 잘라 엔진에 주고, 끝 날에는 새로 사지 않으며, 열린 매매는 끝 날 종가에 팖(정산판).
     F7b와 같은 정산 없는 셈(legacy)은 재현 확인용으로 따로 둠.
  3. 기준 P도 같은 정산을 한 공식(시총 100위) B 2017 ~ 2020으로 같은 실행에서 셈 → 경계 = 0.5 × P_정산.
python3 research/t012.py"""
import bisect
import glob
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

import os

ROOT = Path("/home/user/stock-dash")                 # 자료(캐시 · 표 · 원자료 폴더)는 여기서 읽음
HERE = Path(__file__).resolve().parent.parent         # 코드는 이 파일이 든 작업 트리에서 import
BOX = HERE / "research-exchange/claude-to-gpt/D1-F7C-0043"
os.chdir(ROOT)


def _fh(pattern):
    h = hashlib.sha256()
    for f in sorted(glob.glob(str(ROOT / pattern))):
        h.update(Path(f).name.encode())
        h.update(hashlib.sha256(Path(f).read_bytes()).digest())
    return h.hexdigest()


def _file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


LOCK_FILES = ["/tmp/nrl-cache.pkl", "study/features.json"]
LOCK_DIRS = ["investor-full/*.json", "volume-data/*.json", "investor-data/*.json", "opinion-data/*.json"]
LOCK_CODE = ["research/t012.py", "research/t011.py", "nrl.py", "lab.py", "rule.py", "final_study.py", "final_group.py",
             "caps.py", "study.py"]


def current_lock():
    out = {f: _file(f if f.startswith("/") else ROOT / f) for f in LOCK_FILES}
    out.update({d: _fh(d) for d in LOCK_DIRS})
    out.update({c: _file(HERE / c) for c in LOCK_CODE if c != "research/t012.py"})
    return out


def lock_check():
    want = json.loads((BOX / "lock.json").read_text())
    got = current_lock()
    bad = [k for k in want if want[k] != got.get(k)]
    if bad:
        sys.exit(f"자료 · 코드 잠금 다름 {bad} — 셈하지 않음")


if __name__ == "__main__" and "--make-lock" not in sys.argv:
    lock_check()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "research"))
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
    out = {"task": "D1-F7C-0043", "round": 2, "codes": len(codes), "pool_rows": len(pool),
           "per_day": round(len(pool) / max(1, len({r['date'] for r in pool})), 1)}

    def one(sub, w, lo, settled):
        if not sub:
            return None
        if settled:
            hi = max(r["date"] for r in sub)
            p = {c: {**b, "rows": [x for x in b["rows"] if x[0] <= hi]} for c, b in nrl.prices.items()}
            p = {c: b for c, b in p.items() if b["rows"]}
            sub = [r for r in sub if r["code"] in p and r["i"] < len(p[r["code"]]["rows"])]
            holds = lambda r, h=w["holds"], hi=hi: r["date"] < hi and h(r)
            exits = t011_settle(w["exits"])
            kin = rule.apart(p)
        else:
            p, holds, exits, kin = nrl.prices, w["holds"], w["exits"], nrl.kin
        g = lab.wobble(sub, p, holds, exits, tries=8, slots=nrl.SLOTS, since=lo, apart=kin, realistic=True, cap=130,
                       detail=True, size=w["size"], rank=rule.order, cost=0.25)
        if not g:
            return None
        s_, a, b = nrl.luck(g, nrl.SLOTS, lo)
        res = {k: g.get(k) for k in ("매매", "연수익", "폭", "최대낙폭", "골 폭", "가동률", "승률", "해마다")}
        res.update({"행운뺌": a, "큰2건뺌": b})
        return res

    for tag in ("B", "S1"):
        out[tag] = {}
        for name, lo, hi in SPANS:
            out[tag][name] = one([r for r in pool if lo <= r["date"] < hi], ways[tag], lo, True)
            print(tag, name, json.dumps(out[tag][name], ensure_ascii=False), file=sys.stderr, flush=True)
    out["legacy_B"] = {}
    for name, lo, hi in SPANS[:3]:
        out["legacy_B"][name] = one([r for r in pool if lo <= r["date"] < hi], ways["B"], lo, False)
        print("legacy_B", name, json.dumps(out["legacy_B"][name], ensure_ascii=False), file=sys.stderr, flush=True)
    off = [r for r in nrl.early if r["date"] >= "20170101"]
    out["P_settled"] = one(off, ways["B"], rule.SINCE, True)
    x, pp = out["B"]["2017 ~ 2020"], out["P_settled"]
    if not x or not pp:
        out["label"] = "INCONCLUSIVE"
    else:
        bound = 0.5 * pp["연수익"]
        out["bound"] = round(bound, 4)
        out["label"] = "PERIOD_EFFECT" if x["연수익"] >= bound else "METHOD_EFFECT"
        out["crosses_width"] = abs(x["연수익"] - bound) <= max(x["폭"], 0.5 * pp["폭"])
    out["초"] = round(time.time() - t0)
    print(json.dumps(out, ensure_ascii=False))


def t011_settle(exit_at):
    """종목 줄의 마지막 칸(기간 끝 · 줄 끝)에서 그날 종가에 팖(연구용 가상 정산)."""
    def go(lane, start, price, step, peak, row=None):
        if start + step >= len(lane["closes"]) - 1:
            return True
        return exit_at(lane, start, price, step, peak, row)
    return go


if __name__ == "__main__":
    if "--make-lock" in sys.argv:
        (BOX / "lock.json").write_text(json.dumps(current_lock(), indent=1))
        sys.exit(0)
    sys.exit(main())
