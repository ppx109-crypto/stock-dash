"""코스닥 갈래(K) 도우미 — 코스닥 종목만 따로 1일봉 규칙 엔진(nrl · lab.wobble)을 돌리게 판을 바꿔 끼움.
코스닥 = 야후 표시(hourly-data/suffix.json) KQ · 조사 대상 500종목 안 101종목(지금 큰 코스닥 — 지금 살아 있는 종목만이라 좋게 나오는 쪽 치우침).
그날 순위 = 코스닥 안 시총 순위(caps · 주식수는 그날까지 접수된 것) · 시장 폭 = 코스닥 안 50일선 > 200일선 몫(그날 100위 안).
수급 = investor-data(2017 ~ · 전날까지) · '조용함' 문턱: 기본은 지금(코스피 섞인 표) 것 · calm='kq'면 코스닥 줄로 다시 잼."""
import json
import os
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import caps
import final_group
import final_study as FS
import lab
import nrl

rule = nrl.rule
SUF = json.load(open("/home/user/stock-dash/hourly-data/suffix.json"))
KQ = sorted(c for c, v in SUF.items() if v == "KQ" and c in nrl.prices)
BR_KOSPI = dict(nrl.BR)


def build(since="20161001"):
    rows = []
    for k in range(0, len(KQ), 25):
        part = {c: nrl.prices[c] for c in KQ[k:k + 25]}
        rows += [r for r in lab.build(part, horizons=(0,)) if r["date"] >= since]
    for r in rows:
        r.pop(caps.RANK, None)
    caps.tag(rows, rule.TOP)
    new = FS.shapes(nrl.lanes, [c for c in KQ if c not in nrl.shape])
    nrl.shape.update(new)
    for c in KQ:
        if c not in nrl.FLOW:
            fr = final_group.flow_rows(c)
            if fr:
                nrl.FLOW[c] = nrl.flow_entry(fr)
    return rows


def use_breadth(rows, which="kq"):
    """aligned()가 보는 시장 폭을 바꿈: kq = 코스닥 안 · kospi = 지금(시총 100위 섞인 표)."""
    nrl.BR.clear()
    nrl.BR.update(FS.breadth_by_day(rows, nrl.shape) if which == "kq" else BR_KOSPI)


def calm_kq(rows):
    vals = sorted(r["변동성"] for r in rows if r.get("변동성") is not None and caps.inside(r, rule.TOP))
    return vals[int(len(vals) * rule.CALM)]


def run(tag, pool, holds=None, size=None, exit_at=None, rank=None, seeds=8):
    holds = holds or nrl.BASE_HOLD
    out = [f"  {tag:34s}"]
    got = {}
    for side, lo, hi in (("앞", "20170101", rule.MID), ("뒤", rule.MID, "20991231")):
        sub = [r for r in pool if lo <= r["date"] < hi]
        g = lab.wobble(sub, nrl.prices, holds, exit_at or nrl.BASE_EXIT, tries=seeds, slots=nrl.SLOTS, since=lo, apart=nrl.kin,
                       realistic=True, cap=130, detail=True, size=size or nrl.BASE_SIZE, rank=rank or rule.order)
        got[side] = g
        out.append(f"{side} " + nrl.line(g, nrl.SLOTS, lo))
    print(" | ".join(out), flush=True)
    return got
