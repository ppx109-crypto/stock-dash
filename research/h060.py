"""1시간봉 60회차 — 산 종목을 실시간으로 지켜보며 익절 · 손절(사용자 "한국투자증권 API 연결 · 1H 진입 뒤 그 종목만 실시간으로 받아 손절 · 익절").
실시간 감시 = '그 시간 안에 값에 닿았나' → 1시간봉 고가 · 저가로 흉내(닿은 순간 그 값에 체결 · 시가가 이미 넘었으면 시가 · 한 봉에서 둘 다 닿으면 손절 먼저).
지금 방식은 봉 종가로 판단 → 다음 봉 시가. 바탕: 1시간봉 최고 규칙(자리 바꾸기 폭<90 · 추세 문 +5% 절반 · +13% 전량 · −5% · 정배열 −10% · 본전 지키기 +8 → +1).
비교: ① 지금(종가 판단) ② 익절만 실시간(+5% 절반 · +13% 지정가) ③ 손절만 실시간(−5 · −10% · 본전 +1% 선) ④ 둘 다 실시간 ⑤ 익절 실시간 + 손절은 종가.
점검: 씨앗 16 · 큰 매매 뺀 연수익 · 바뀐 매매 손익 · 반기."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
base_exit = make_exit()
def kind_of(p):
    return door(ATT[p["code"]][p["i"]]) or "정배열"
def take_rt(p):
    if kind_of(p) != "추세": return (None, 0)
    if p["칸"] == p["처음칸"]:
        return (p["price"] * 1.05, max(1, p["처음칸"] // 2))
    return (p["price"] * 1.13, "all")
def stop_rt(p):
    if kind_of(p) == "추세": return p["price"] * 0.95
    if (p["peak"] / p["price"] - 1) * 100 >= 8: return p["price"] * 1.01      # 본전 지키기 선(고점은 닫힌 봉 종가 기준)
    return p["price"] * 0.90
def trimmed2(ex, tk, st):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, ex, size, lo, hi, 10, seed, st, rank, H.COST, tk, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
CASES = [("① 지금(봉 종가 판단)", None, None), ("② 익절만 실시간", take_rt, None), ("③ 손절만 실시간", None, stop_rt),
         ("④ 익절 · 손절 모두 실시간", take_rt, stop_rt)]
print("== 1시간봉 60회차 (산 종목 실시간 익절 · 손절) ==", flush=True)
base = None
for tag, tk, st in CASES:
    res = H.simulate(data, e_align_or_noon, base_exit, size, rank=rank, stale_of=stale90, seeds=16, take_of=tk, stop_of=st)
    tr = trimmed2(base_exit, tk, st)
    print(f"  {tag:22s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연(가운데): 앞 {tr['앞']} · 뒤 {tr['뒤']} · 반기(씨앗 0) 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
    if base is None:
        base = res
    else:
        for s in ("앞", "뒤"):
            kb = {(t["code"], t["산 때"]): t for t in base[s]["목록"] if not t["나눠"]}
            kn = {(t["code"], t["산 때"]): t for t in res[s]["목록"] if not t["나눠"]}
            both = [k for k in kn if k in kb and kn[k]["판 때"] != kb[k]["판 때"]]
            d = [kn[k]["손익"] - kb[k]["손익"] for k in both]
            print(f"      {s} 바뀐 매매 {len(d)}건 · 차이 평균 {np.mean(d) if d else 0:+.2f}%p · 나은 몫 {np.mean([v > 0 for v in d]) * 100 if d else 0:.0f}%", flush=True)
print("끝", flush=True)
