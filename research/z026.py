"""B0 ③ — 1일봉 운영 봇(daily_live.py) = 연구 엔진(nrl · lab.run)인가: 날마다 다시 돌려 맞춰 보기.
- 운영 쪽: 날 d마다 그날까지 일봉만 남긴 자료로 daily_live와 같은 길(전날 시총 150위 · final_group.compute · 목표가 내림 빼기 ·
  3일 연속 · 거래량비(그날 거래량) · 크기 · 닮음 · decide · settle)을 그날 종가로 돌림(15:20 값 = 종가로 봄).
- 연구 쪽: lab.wobble 씨앗 0 매매목록(같은 기간에 빈 계좌로 시작).
- 견줌: 산 매매(종목 · 산 날) 같은 것 · 한쪽에만 있는 것 · 같은 매매의 판 날 · 손익 차이 · 두 쪽 계좌(칸 × 손익) 합.
Z_FROM · Z_TO(기본 20250102 ~ 20260930). python research/z026.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import caps  # noqa: E402
import daily_live as DL  # noqa: E402
import final_group  # noqa: E402
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402

FROM, TO = os.getenv("Z_FROM", "20250102"), os.getenv("Z_TO", "20260930")
KEEP = int(os.getenv("Z_KEEP", "600"))
OUT = Path(os.getenv("Z_OUT", "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/z026.json"))


def vol_on(code, day):
    body = DL._load(Path("volume-data") / f"{code}.json", {})
    names = body.get("칸") or []
    if "거래량" not in names:
        return None
    k = names.index("거래량")
    for row in body.get("날") or []:
        if str(row[0]) == day:
            return row[k]
    return None


def replay():
    prices = study.load_prices()
    days = sorted({d for v in prices.values() for d, _ in v["rows"] if FROM <= d <= TO})
    alld = sorted({d for v in prices.values() for d, _ in v["rows"]})
    calm = (DL._load(Path("study") / "a_group.json", {}) or {}).get("calm_edge")
    full = {c: {"name": v["name"], "rows": v["rows"]} for c, v in prices.items()}
    steps = lab.moves(full)
    pos = {c: {d: i for i, (d, _) in enumerate(v["rows"])} for c, v in full.items()}
    dates = {c: [d for d, _ in v["rows"]] for c, v in full.items()}
    state = {"positions": {}, "closed": []}
    for n, day in enumerate(days):
        last = alld[alld.index(day) - 1]
        yest = [{"code": c, "date": last, "price": dict(v["rows"]).get(last)} for c, v in prices.items()]
        yest = [r for r in yest if r["price"]]
        caps.tag(yest, DL.POOL)
        pool = {r["code"] for r in yest if (r.get(caps.RANK) or 999) <= DL.POOL} | set(state["positions"])
        live = {}
        for c in pool:
            k = pos[c].get(day)
            rows = prices[c]["rows"][max(0, k - KEEP + 1):k + 1] if k is not None else []   # 최근 KEEP일만(200일선 · 250일 고점에 넉넉 · 셈 빠르게)
            if rows and rows[-1][0] == day:
                live[c] = {"name": prices[c]["name"], "rows": rows}
        found = final_group.compute(live, calm=calm)
        if found.get("date") != day:
            continue
        cands = []
        for one in found.get("picks", []):
            code = one["code"]
            if DL.target_cut(code, day):
                continue
            cands.append({**one, "추세문": final_group.RULE_DOOR in (one.get("갈래") or []), "3일연속": DL.steady3(code, day),
                          "거래량비": DL.volume_ratio(code, day, vol_on(code, day))})
        held = state["positions"]
        aligned = {}
        for code in held:
            if code in live:
                form = final_group.lines_now([x for _, x in live[code]["rows"]])
                aligned[code] = bool(form and form.get("정배열"))
        idx = {c: pos[c][day] for c in live}
        kin_ok = DL.kin_checker(steps, idx, dates, {c: p.get("bought") for c, p in held.items()})
        close = {c: live[c]["rows"][-1][1] for c in live}
        rate = {c: (live[c]["rows"][-1][1] / live[c]["rows"][-2][1] - 1) * 100 if len(live[c]["rows"]) > 1 else 0 for c in live}
        sells, buys = DL.decide(state, cands, close, aligned, rate, kin_ok)
        DL.settle(state, day, sells, buys, close)
        if n % 5 == 0:
            print(f"  {day} 들고 있음 {len(state['positions'])} · 끝난 매매 {len(state['closed'])}", flush=True)
    OUT.write_text(json.dumps(state, ensure_ascii=False))
    return state


def research():
    g = lab.wobble(nrl.inside, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, tries=1, slots=nrl.SLOTS, since=FROM,
                   apart=nrl.kin, realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE, rank=rule.order)
    return [t for t in g["매매목록"] if t["산 날"] <= TO]


def main():
    st = json.loads(OUT.read_text()) if os.getenv("Z_REUSE") and OUT.exists() else replay()
    live = [t for t in st["closed"]]
    res = research()
    L = {(t["code"], t["산 날"]): t for t in live}
    R = {(t["code"], t["산 날"]): t for t in res}
    both = sorted(set(L) & set(R))
    print(f"\n== 1일봉 운영 = 연구? ({FROM} ~ {TO}) ==")
    print(f"  산 매매(종목 · 산 날): 운영 {len(L)} · 연구 {len(R)} · 같음 {len(both)} · 운영에만 {len(set(L) - set(R))} · 연구에만 {len(set(R) - set(L))}")
    sameexit = sum(1 for k in both if L[k]["판 날"] == R[k]["판 날"])
    print(f"  같은 매매 가운데 판 날 같음 {sameexit}/{len(both)}")
    f = lambda ts, kk, kp: sum(t[kp] * t[kk] for t in ts) / 10
    print(f"  계좌 몫 합(칸 × 손익 ÷ 10): 운영 {f(live, '칸', '손익'):+.1f}% · 연구 {f(res, '자리', '손익'):+.1f}%")
    for lab_, ks, src in (("운영에만", sorted(set(L) - set(R))[:12], L), ("연구에만", sorted(set(R) - set(L))[:12], R)):
        print(f"  {lab_}: " + " · ".join(f"{c} {d}" for c, d in ks))
    diff = [k for k in both if L[k]["판 날"] != R[k]["판 날"]][:10]
    print("  판 날 다른 것: " + " · ".join(f"{c} {d}(운영 {L[(c, d)]['판 날']} · 연구 {R[(c, d)]['판 날']})" for c, d in diff))


if __name__ == "__main__":
    main()
