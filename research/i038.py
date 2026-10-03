"""최고의 조합 규칙(사용자 2026-10-03 "15m · 1h · 1일봉 · 인버스 … 지금까지 + 앞으로 연구로 오르든 옆걸음이든 내리든 최고의 자금 회전 · 수익 · 최소 낙폭").
판 장부(scratchpad · 매매마다 (종목, 산 날, 판 날, 손익%, 칸/10)):
  1일봉 x008_d1(2017 ~) · 1시간봉 x008_h1y3(야후 · 2023-10 ~) · 1년 세 갈래 x004_d1 · x004_h1k(한투 1시간봉) · x004_m15_final(15분봉 · 2025-09 ~ 2026-08).
돈 나누는 법:
  나눠 쓰기(고정 몫): 판마다 칸 × 몫.
  같이 쓰기(한 지갑 10칸): 산 날 순서로 빈칸이 있으면 받아들이고 없으면 그 매매는 못 함(같은 날은 앞 순위 판 먼저). 판 날이 산 날보다 '앞선 날'인 자리만 비움(같은 날 팔고 사기는 안 침 — 보수적).
  칸 몫(scale): 같이 쓰기에서 판마다 한 매매 칸을 몇 배로 쓸지(1 = 원래대로).
결과 장부를 i013(빈칸 엔진 · 코스닥 인버스 · 1일봉 쓴 몫 < 20%일 때 엔진)에 넣어 계좌 전체 연 · 골 · 돈 쓴 몫을 견줌. 미래 참조: 받아들일지는 그날까지의 빈칸만 봄."""
import json
import os
import sys

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
L = {k: json.load(open(SP + f)) for k, f in (("D", "x008_d1.json"), ("H", "x008_h1y3.json"), ("d", "x004_d1.json"), ("h", "x004_h1k.json"), ("m", "x004_m15_final.json"))}


def fixed(parts):
    """parts: {판: 몫} → 칸 × 몫 장부."""
    return [(c, b, s, p, k * w) for key, w in parts.items() for c, b, s, p, k in L[key]]


def pool(order, scale=None, cap=10.0, start="00000000"):
    """같이 쓰기: order 순위 · scale 칸 몫 · cap 칸. 받아들인 매매 장부와 못 한 매매 수."""
    scale = scale or {}
    ev = sorted(((b, order.index(key), key, c, b, s, p, k * scale.get(key, 1.0)) for key in order for c, b, s, p, k in L[key] if b >= start))
    open_, out, miss = [], [], {k: 0 for k in order}
    for _, _, key, c, b, s, p, k in ev:
        open_ = [(ss, kk) for ss, kk in open_ if ss >= b]          # 산 날보다 앞선 날 판 자리만 비움
        if sum(kk for _, kk in open_) + k <= cap + 1e-9:
            open_.append((s, k))
            out.append((c, b, s, p, k))
        else:
            miss[key] += 1
    return out, miss


def save(name, rows):
    json.dump(rows, open(SP + f"x038_{name}.json", "w"))
    return f"x038_{name}.json"


if __name__ == "__main__":
    plans = {}
    # 구간 A(2023-10 ~): 1일봉 + 1시간봉
    plans["A 1일봉만"] = fixed({"D": 1.0})
    plans["A 1시간봉만"] = fixed({"H": 1.0})
    plans["A 나눠 쓰기 반반"] = fixed({"D": 0.5, "H": 0.5})
    plans["A 나눠 쓰기 1일봉 70"] = fixed({"D": 0.7, "H": 0.3})
    plans["A 나눠 쓰기 1시간봉 70"] = fixed({"D": 0.3, "H": 0.7})
    for nm, order, sc in (("A 같이 쓰기 1일봉 먼저", ["D", "H"], None), ("A 같이 쓰기 1시간봉 먼저", ["H", "D"], None),
                          ("A 같이 쓰기 칸 0.7배", ["D", "H"], {"D": 0.7, "H": 0.7})):
        rows, miss = pool(order, sc, start="20231001")
        plans[nm] = rows
        print(f"  {nm}: 받아들인 {len(rows)}건 · 못 한 매매 {miss}", flush=True)
    # 구간 B(2025-09 ~ 2026-08 · 한투 1년 세 갈래)
    plans["B 1일봉만"] = fixed({"d": 1.0})
    plans["B 셋 나눠 쓰기"] = fixed({"d": 1 / 3, "h": 1 / 3, "m": 1 / 3})
    plans["B 1일봉 · 1시간봉 반반"] = fixed({"d": 0.5, "h": 0.5})
    for nm, order, sc in (("B 셋 같이 쓰기 1일봉 먼저", ["d", "h", "m"], None), ("B 셋 같이 쓰기 15분봉 먼저", ["m", "h", "d"], None),
                          ("B 셋 같이 쓰기 칸 0.6배", ["d", "h", "m"], {"d": 0.6, "h": 0.6, "m": 0.6}), ("B 1일봉 · 1시간봉 같이 쓰기", ["d", "h"], None)):
        rows, miss = pool(order, sc)
        plans[nm] = rows
        print(f"  {nm}: 받아들인 {len(rows)}건 · 못 한 매매 {miss}", flush=True)
    json.dump({nm: save(f"p{i}", rows) for i, (nm, rows) in enumerate(plans.items())}, open(SP + "x038_plans.json", "w"), ensure_ascii=False)
    print("장부", len(plans), "개 저장", flush=True)
