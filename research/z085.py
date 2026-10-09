"""ACC-VOL-0006 H5 — z084에 계좌 전체 흔들림 상한(Z_ACC_VOL · 하루 σ 상한, 0이면 끔)을 더한 판: 전날까지 20거래일 동안 지금 보유 전체(주식 · ETF)의 하루 수익률 σ로
E = min(1, Z_ACC_VOL ÷ σ). 보유 합 > E × 계좌면 15:20에 모든 보유를 같은 비율로 덜어냄 · 모든 매수(15분봉 · 바구니 · 엔진 · 1일봉)는 E × 계좌 − 보유 합까지.
(이하 z084 설명) z070(감사 A3)을 복사해 1일봉 몫에만 흔들림 상한(Z_D1_VOL · 하루 σ 상한, 0이면 끔)을 넣은 판. 그 밖은 z070과 같음.
감사 A3 — 현재 운영 조합을 '하나의 현금 · 주식 원장'으로 과거에 다시 돌림(운영 코드의 판단 함수를 그대로 부름 · 운영 코드는 고치지 않음).
- 1일봉 '새 82': 연구 매매 목록(z055_d1_raw = 운영 길과 107/107 같음 · 옛 시총 계산 = 지금 운영 caps 그대로)의 산 날 · 판 날 · 칸.
  크기 = 계좌 총액 × 50% × 칸 / 10(paper_trade.plan_orders) · 15:20(종가로 봄). 판 날 값은 장부 손익에 맞춤(a_mtm과 같음).
- 15분봉 22회차: x004_m15_final(2025-09-17 ~ 2026-08-31 · 한투 1년) · 크기 계좌 × 50% × 칸 / 10 · 산 날 종가로 어림(실제는 장중).
- 1시간봉: 운영 몫 0(PAPER_SHARE_1H 기본 0 · 작업 흐름 PAPER_TRADING off) → 넣지 않음.
- 사건 바구니 C: basket_live.step 그대로(돈 = 계좌 × 50% − 1일봉 평가액 · 5칸 · 20거래일 · others 제외) · 사건 = event-data · 반응 = 그날 200위(옛 시총) 가운데값 뺀 수익.
- 빈칸 엔진 · 코스닥 인버스: idle_live.step 그대로(idle_signal.decide · 15:10 값 = 그날 종가로 어림) · 시장 폭 = nrl.BR(옛 시총) · used = (1일봉 + 15분봉) ÷ 총액 ·
  reserve = 그날 1일봉이 살 돈(운영은 14:30 후보 × 4칸 · 여기선 그날 실제 산 것 — 어림).
- 하루 순서: 15분봉(장중) → 15:10 바구니 → 엔진 · 인버스 → 15:20 1일봉 팔기 → 사기. 1일봉 · 15분봉이 살 돈이 모자라면 make_room과 같게
  엔진 전부 → 바구니 오래된 것부터 팖(필요 × 1.36 > 현금 × 0.98 일 때만).
- 시장가 증거금: 살 수 있는 돈 = 현금 ÷ Z_MARGIN(기본 1.30 · 실제 장부 10-07 인버스 주문이 매수가능 수량에 맞춰 약 0.81배로 줄어 접수).
- 비용: 주식 perf2 BASE(해마다 거래세 · 수수료 · 슬리피지 · 충격 · 계좌 Z_ACC원) · ETF 편도 0.065%(수수료 0.015 + 슬리피지 0.05 · 매도세 없음).
- 현금 셋: ① 예비(그날 1일봉 몫으로 비켜 둔 돈 + 증거금 여유) ② 신호 없음 ③ 신호 있었는데 칸 · 돈 · 자리 문제로 못 쓴 돈(사려던 금액 − 산 금액).
Z_DROP=1d|15m|basket|engine|inverse — 그 전략을 빼고(돈은 현금으로) 다시 돌림. Z_FROM · Z_TO · Z_OUT(일별 NAV · 현금 CSV).
NRL_CACHE=/tmp/nrl-cache.pkl python research/z070.py
"""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
import basket_live  # noqa: E402
import idle_live  # noqa: E402
import idle_signal  # noqa: E402
import perf2 as P  # noqa: E402

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
DROP = set(filter(None, os.getenv("Z_DROP", "").split(",")))
FROM, TO = os.getenv("Z_FROM", "20170201"), os.getenv("Z_TO", "20260930")
MARGIN = float(os.getenv("Z_MARGIN", "1.30"))
ACC = float(os.getenv("Z_ACC", "1e8"))
SHARE = 0.5
ETF_SIDE = 0.00065
STOCK_SIDE = os.getenv("Z_STOCK_SIDE")
D1_VOL = float(os.getenv("Z_D1_VOL", "0"))   # 1일봉 몫 흔들림 상한(하루 σ). 후보 = 0.021822
LOOK = 20   # 검산용: 주식 편도 비용을 고정(예: 0.00125 = 왕복 0.25%)


def etf_closes(code):
    b = json.loads((ROOT / "etf-data" / f"{code}.json").read_text(encoding="utf-8"))
    return {str(d): float(c) for d, c in b["closes"] if c}


def main():
    import nrl
    days = sorted(d for d in nrl.BR if FROM <= d <= TO)
    stock = {c: dict(v["rows"]) for c, v in nrl.prices.items()}
    etf_codes = sorted(idle_live.CODES)
    etf = {c: etf_closes(c) for c in etf_codes}
    etf_days = {c: sorted(v) for c, v in etf.items()}
    etf_arr = {c: np.array([etf[c][x] for x in etf_days[c]], float) for c in etf_codes}
    import bisect
    led1 = [] if "1d" in DROP else json.load(open(SP / "z055_d1_raw.json"))
    led15 = [] if "15m" in DROP else json.load(open(SP / "x004_m15_final.json"))
    buys = {}
    sells = {}
    for tag, led in (("1d", led1), ("15m", led15)):
        for k, (c, b, e, p, s) in enumerate(led):
            buys.setdefault(b, []).append((tag, k, c, s))
            sells.setdefault(e, []).append((tag, k, c, p))
    # 바구니: 사건 · 반응(그날 200위 · 옛 시총)
    import z001 as Z
    import caps
    caps.ADJ = False
    C, F, ops, evs, qs, name = Z.load()
    inside, _ = Z.universe(C)
    inside = inside.where(inside, False)
    r1 = C / C.shift(1) - 1
    react = r1.sub(r1.where(inside).median(axis=1), axis=0)
    events = {c: [(d, k) for d, k in rows if k in basket_live.KINDS] for c, rows in evs.items()}
    cidx = {d: i for i, d in enumerate(C.index)}
    cal = list(C.index)
    tidx = {d: i for i, d in enumerate(days)}

    cash, nav_rows = ACC, []
    pos = {}                     # 열쇠 → {bot, code, val, px, cost_in(원), ...}
    eng_state, bas_state = {}, {}
    eng_held, bas_held = {}, {}  # 코드 → 원(평가액)으로 둠 · 수량 대신
    missed = {"1d": 0.0, "15m": 0.0, "basket": 0.0, "engine": 0.0, "inverse": 0.0}
    missed_n = {k: 0 for k in missed}
    costs = 0.0
    forced = 0.0
    prev = None
    vol_cuts = [0]
    acc_cuts = [0]
    acc_allowed = 1.0

    def price(code, d):
        if code in etf:
            return etf[code].get(d)
        return stock.get(code, {}).get(d)

    def total():
        return cash + sum(p["val"] for p in pos.values())

    def sell(key, d, frac=1.0, why=""):
        nonlocal cash, costs
        p = pos[key]
        amt = p["val"] * frac
        if p["code"] in etf:
            c = amt * ETF_SIDE
        else:
            c = amt * (float(STOCK_SIDE) if STOCK_SIDE else P.side_costs(p["code"], d, d, max(amt, 1.0), 1.0)[1])
        cash += amt - c
        costs += c
        if frac >= 0.999:
            pos.pop(key)
        else:
            p["val"] -= amt
        return amt

    def buy(key, bot, code, d, money, **kw):
        nonlocal cash, costs, acc_allowed
        px = price(code, d)
        if not px or money <= 0:
            return 0.0
        money = min(money, cash / MARGIN)
        if ACC_VOL > 0:
            money = min(money, max(0.0, acc_allowed * total() - sum(p["val"] for p in pos.values())))
        if money <= 0:
            return 0.0
        c = money * (ETF_SIDE if code in etf else (float(STOCK_SIDE) if STOCK_SIDE else P.side_costs(code, d, d, money, 1.0)[0]))
        cash -= money
        costs += c
        pos[key] = dict(bot=bot, code=code, val=money - c, px=px, day=d, **kw)
        return money

    def make_room(need, d):
        nonlocal forced
        if need * 1.36 <= cash * 0.98:
            return
        for k in [k for k, p in pos.items() if p["bot"] == "engine"]:
            forced += sell(k, d)
        for k in sorted([k for k, p in pos.items() if p["bot"] == "basket"], key=lambda k: pos[k]["day"]):
            if need * 1.36 <= cash * 0.98:
                break
            forced += sell(k, d)

    for d in days:
        # 1) 값 매기기(어제 → 오늘 종가)
        for k, p in pos.items():
            px = price(p["code"], d)
            if px and p["px"]:
                p["val"] *= px / p["px"]
                p["px"] = px
        tot0 = total()
        acc_allowed = 1.0
        if ACC_VOL > 0 and pos:
            held_v = sum(p["val"] for p in pos.values())
            rets, ok = [], held_v > 0
            for p in (pos.values() if ok else []):
                if p["code"] in etf:
                    ds = etf_days[p["code"]]; cs = [etf[p["code"]][x] for x in ds]
                else:
                    ln = nrl.lanes.get(p["code"]); ds, cs = (ln["날"], ln["closes"]) if ln else ([], [])
                i = bisect.bisect_left(ds, d) - 1                 # 전날까지(오늘 값 안 씀)
                if i - LOOK < 0:
                    ok = False
                    break
                rets.append((p["val"] / held_v, [cs[j] / cs[j - 1] - 1 for j in range(i - LOOK + 1, i + 1)]))
            if ok and rets:
                port = [sum(w * r[t] for w, r in rets) for t in range(LOOK)]
                m = sum(port) / LOOK
                sd = math.sqrt(sum((x - m) ** 2 for x in port) / (LOOK - 1))
                if sd > 0:
                    acc_allowed = min(1.0, ACC_VOL / sd)
        reserve_1d = sum(tot0 * SHARE * s / 10 for tag, k, c, s in buys.get(d, []) if tag == "1d")
        # 2) 15분봉(장중): 팔기 → 사기
        for tag, k, c, pnl in sells.get(d, []):
            if tag == "15m" and (tag, k) in pos:
                p = pos[(tag, k)]
                p["val"] = p["entry"] * (1 + pnl / 100) / (1 - 0.003)      # 장부 손익(왕복 0.30% 뺀 값) → 비용 전
                sell((tag, k), d)
        for tag, k, c, s in buys.get(d, []):
            if tag != "15m":
                continue
            want = total() * SHARE * s / 10
            make_room(want, d)
            got = buy((tag, k), "15m", c, d, min(want, cash * 0.98))
            if got:
                pos[(tag, k)]["entry"] = pos[(tag, k)]["val"]
            if got < want * 0.99:
                missed["15m"] += (want - got) / total()
                missed_n["15m"] += 1
        # 3) 15:10 바구니
        held_codes = {p["code"] for p in pos.values() if p["bot"] in ("1d", "15m", "engine")}
        if "basket" not in DROP and d in cidx and cidx[d] > 1:
            t0 = cal[cidx[d] - 1]                     # 전체 거래일 달력(시뮬 시작 앞 날도 있음)
            before = cal[cidx[d] - 2]
            ev_t0 = basket_live.todays_events(events, t0, before)
            ins = {c for c in C.columns if t0 in cidx and inside.iat[cidx[t0], C.columns.get_loc(c)]}
            rx = {c: float(react.iat[cidx[t0], C.columns.get_loc(c)]) for c, _ in ev_t0 if t0 in cidx and np.isfinite(react.iat[cidx[t0], C.columns.get_loc(c)])}
            d1v = sum(p["val"] for p in pos.values() if p["bot"] == "1d")
            capital = max(0.0, total() * SHARE - d1v)
            bheld = {p["code"]: 1 for p in pos.values() if p["bot"] == "basket"}
            nowp = {c: price(c, d) for c in set(bheld) | {c for c, _ in ev_t0}}
            orders, bas_state, why = basket_live.step(bas_state, d, t0, lambda x: cidx[d] - cidx.get(x, cidx[d]), ev_t0, rx, ins,
                                                      bheld, {c: v for c, v in nowp.items() if v}, capital,
                                                      max(0.0, cash - reserve_1d * 1.36), {}, held_codes)
            for c, side, q, _ in orders:
                if side == "sell":
                    for k in [k for k, p in pos.items() if p["bot"] == "basket" and p["code"] == c]:
                        sell(k, d)
            for c, side, q, _ in orders:
                if side == "buy":
                    want = q * price(c, d)
                    got = buy(("basket", c, d), "basket", c, d, want)
                    if got < want * 0.99:
                        missed["basket"] += (want - got) / total()
                        missed_n["basket"] += 1
            slot = capital / basket_live.SLOTS
            for w in why:
                if "5칸이 다 참" in w or "살 돈이 모자람" in w:
                    missed["basket"] += slot / total()
                    missed_n["basket"] += 1
        # 4) 15:10 엔진 · 인버스
        if not ({"engine", "inverse"} <= DROP):
            px_hist = {c: etf_arr[c][:bisect.bisect_right(etf_days[c], d)] for c in etf_codes}
            if all(len(v) > 60 for v in px_hist.values()) and all(etf[c].get(d) for c in etf_codes):
                live_codes = {p["code"] for p in pos.values() if p["bot"] == "engine"}
                eng_state["positions"] = {c: v for c, v in (eng_state or {}).get("positions", {}).items() if c in live_codes}
                tot = total()
                rule_v = sum(p["val"] for p in pos.values() if p["bot"] in ("1d", "15m"))
                used = rule_v / tot if tot > 0 else 1.0
                br = nrl.BR.get(d, 100.0)
                eheld = {}
                for p in pos.values():
                    if p["bot"] == "engine":
                        eheld[p["code"]] = eheld.get(p["code"], 0) + int(p["val"] / p["px"])
                nowp = {c: etf[c][d] for c in etf_codes}
                wk_end = tidx[d] + 1 >= len(days) or days[tidx[d] + 1][:4] + str(pd.Timestamp(days[tidx[d] + 1]).isocalendar()[1]) != d[:4] + str(pd.Timestamp(d).isocalendar()[1])
                bas_v = sum(p["val"] for p in pos.values() if p["bot"] == "basket")
                orig = idle_signal.decide
                if DROP & {"engine", "inverse"}:
                    def patched(*a, **k):
                        s = orig(*a, **k)
                        if "inverse" in DROP:
                            s = dict(s, 코스닥인버스=False)
                        if "engine" in DROP:
                            s = dict(s, 엔진=False, 급락=False, 하락추세=False, 돌리기={})
                        return s
                    idle_signal.decide = patched
                try:
                    orders, eng_state, why = idle_live.step(eng_state, d, px_hist, br, max(0.0, used), tot, max(0.0, cash - reserve_1d * 1.36),
                                                            eheld, nowp, wk_end, reserve_1d + bas_v)
                finally:
                    idle_signal.decide = orig
                for c, side, q, _ in orders:
                    if side == "sell":
                        for k in [k for k, p in pos.items() if p["bot"] == "engine" and p["code"] == c]:
                            sell(k, d)
                for c, side, q, r in orders:
                    if side == "buy":
                        got = buy(("engine", c, d), "engine", c, d, q * nowp[c], kind=("인버스" if c == idle_live.INV else "엔진"))
                        if got < q * nowp[c] * 0.99:
                            tag = "inverse" if c == idle_live.INV else "engine"
                            missed[tag] += (q * nowp[c] - got) / total()
                            missed_n[tag] += 1
                if any("비운 돈이 없음" in w for w in why):
                    missed_n["inverse"] += 1
                # 장부와 운영 상태 맞춤(엔진 장부에서 사라진 것은 상태에서도 뺌)
                live_codes = {p["code"] for p in pos.values() if p["bot"] == "engine"}
                eng_state["positions"] = {c: v for c, v in eng_state.get("positions", {}).items() if c in live_codes}
        # 4.5) 15:20 계좌 전체 흔들림 상한(전날까지 σ로 정한 E)
        if ACC_VOL > 0:
            held_v = sum(p["val"] for p in pos.values())
            if held_v > acc_allowed * total() + 1e-9:
                f = 1 - acc_allowed * total() / held_v
                for k in list(pos):
                    ent = pos[k].get("entry")
                    sell(k, d, frac=f)
                    if k in pos and ent:
                        pos[k]["entry"] = ent * (1 - f)
                acc_cuts[0] += 1
        # 5) 15:20 1일봉: 팔기 → 사기
        for tag, k, c, pnl in sells.get(d, []):
            if tag == "1d" and (tag, k) in pos:
                p = pos[(tag, k)]
                p["val"] = p["entry"] * (1 + pnl / 100) / (1 - 0.0025)     # 장부 손익(왕복 0.25% 뺀 값) → 비용 전
                sell((tag, k), d)
        allowed = 1.0
        if D1_VOL > 0:
            d1 = [(k, p) for k, p in pos.items() if p["bot"] == "1d"]
            tot_v = sum(p["val"] for _, p in d1)
            if tot_v > 0:
                rets, ok = [], True
                for _, p in d1:
                    ln = nrl.lanes.get(p["code"])
                    i = bisect.bisect_right(ln["날"], d) - 1 if ln else -1
                    if i - LOOK < 0:
                        ok = False
                        break
                    cs = ln["closes"]
                    rets.append((p["val"] / tot_v, [cs[j] / cs[j - 1] - 1 for j in range(i - LOOK + 1, i + 1)]))
                if ok:
                    port = [sum(w * r[t] for w, r in rets) for t in range(LOOK)]
                    m = sum(port) / LOOK
                    sd = math.sqrt(sum((x - m) ** 2 for x in port) / (LOOK - 1))
                    if sd > 0:
                        allowed = min(1.0, D1_VOL / sd)
                budget = total() * SHARE
                if tot_v > allowed * budget + 1e-9:
                    f = 1 - allowed * budget / tot_v            # 1일봉 보유를 같은 비율로 덜어냄
                    for k, p in d1:
                        ent = p.get("entry")
                        sell(k, d, frac=f)
                        if k in pos and ent:
                            pos[k]["entry"] = ent * (1 - f)     # 남은 몫의 장부 시작값도 같은 비율로
                    vol_cuts[0] += 1
        for tag, k, c, s in buys.get(d, []):
            if tag != "1d":
                continue
            want = total() * SHARE * s / 10
            if D1_VOL > 0:
                held1 = sum(p["val"] for p in pos.values() if p["bot"] == "1d")
                want = max(0.0, min(want, allowed * total() * SHARE - held1))
                if want <= 0:
                    continue
            make_room(want, d)
            got = buy((tag, k), "1d", c, d, min(want, cash * 0.98))
            if got:
                pos[(tag, k)]["entry"] = pos[(tag, k)]["val"]
            if got < want * 0.99:
                missed["1d"] += (want - got) / total()
                missed_n["1d"] += 1
        tot = total()
        by = {b: sum(p["val"] for p in pos.values() if p["bot"] == b) for b in ("1d", "15m", "basket", "engine")}
        inv_v = sum(p["val"] for p in pos.values() if p["bot"] == "engine" and p.get("kind") == "인버스")
        nav_rows.append(dict(날=d, NAV=tot, 현금=cash, 일봉=by["1d"], 분봉15=by["15m"], 바구니=by["basket"], 엔진=by["engine"] - inv_v, 인버스=inv_v,
                             예비=min(cash, reserve_1d), 비용누계=costs, 강제매도누계=forced))
        prev = d
    N = pd.DataFrame(nav_rows).set_index("날")
    r = N["NAV"].pct_change().fillna(0.0)
    out = os.getenv("Z_OUT")
    if out:
        N.round(0).to_csv(out)
    print(f"== 통합 계좌 {FROM} ~ {TO} · 뺀 것 {sorted(DROP) or '없음'} · 증거금 {MARGIN} · 계좌 {ACC / 1e8:.0f}억 · 1일봉 흔들림 상한 {D1_VOL or '없음'}(덜어낸 날 {vol_cuts[0]}) · 계좌 흔들림 상한 {ACC_VOL or '없음'}(덜어낸 날 {acc_cuts[0]}) ==", flush=True)
    for h, lo, hi in (("학습 2017 ~ 20", "20170201", "20210101"), ("검증 2021 ~ 22", "20210101", "20230101"), ("다시 본 기간 2023 ~ 26", "20230101", "20991231"), ("전체", "20000101", "20991231")):
        s = P.daily_stats(r, lo, hi)
        if s:
            print(f"  {h:20s} {P.fmt_d(s)}", flush=True)
    s = P.daily_stats(r, "20000101", "20991231")
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    under = (dd < 0).astype(int)
    runs, cur = [], 0
    for u in under:
        cur = cur + 1 if u else 0
        runs.append(cur)
    print(f"  해마다: {P.years_line(s)}", flush=True)
    print(f"  손실 상태 가장 긴 기간 {max(runs)}거래일 · MDD 날 {dd.idxmin()}", flush=True)
    w = N[["현금", "일봉", "분봉15", "바구니", "엔진", "인버스", "예비"]].div(N["NAV"], axis=0)
    print("  평균 몫: " + " · ".join(f"{k} {v * 100:.1f}%" for k, v in w.mean().items()), flush=True)
    yrs = len(N) / 245
    cy = N["비용누계"].diff().fillna(N["비용누계"].iloc[0]) / N["NAV"].shift(1).fillna(ACC)
    fy = N["강제매도누계"].diff().fillna(N["강제매도누계"].iloc[0]) / N["NAV"].shift(1).fillna(ACC)
    print(f"  비용 연 {cy.sum() / yrs * 100:.2f}%(그날 계좌 대비 합 ÷ 년) · 강제 매도 연 {fy.sum() / yrs * 100:.0f}%(계좌 대비 회전) · "
          "못 쓴 돈(신호 있었는데 · 그때 계좌 대비 합 ÷ 년) " + " · ".join(f"{k} {missed_n[k]}번 {missed[k] / yrs * 100:.0f}%" for k in missed), flush=True)


if __name__ == "__main__":
    main()
