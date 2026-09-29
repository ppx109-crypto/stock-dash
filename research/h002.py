"""1시간봉 2회차 — 일봉 재료(전 거래일까지) × 1시간봉 '때' 조합의 사건 연구(사용자 요청: 1시간봉 + DART + 수급 + 일봉 재료 조합).
1회차: 1시간봉 정배열 혼자는 힘이 없고 힘은 일봉 추세에서 옴 → 일봉 재료로 '무엇을'을 고르고, 1시간봉으로 '언제'를 고름.
판: 신호 봉이 닫힌 뒤 다음 봉 시가에 사서 k봉 뒤 종가에 팜(비용 0.30%). 앞 반 2023-10~2025-03 · 뒤 반 2025-04~."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H

data = H.load()
codes = [c for c in data if not c.startswith("K")]
ranks, trend = H.daily_tables("20220101")
uni = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=100)
CTX = H.daily_context(codes, ranks, trend)
DAYS = {c: sorted(v) for c, v in CTX.items()}
ATT = {c: H.attach(data[c], CTX[c], DAYS[c]) for c in codes if c in CTX}
print(f"일봉 재료 붙은 종목 {len(ATT)}", flush=True)
K = (7, 14, 35, 70)

def ctxmask(c, b, f):
    a = ATT.get(c)
    return np.zeros(len(b["c"]), bool) if a is None else np.array([bool(x) and f(x) for x in a])
first_bar = lambda b: np.r_[True, np.array([b["t"][i][:8] != b["t"][i - 1][:8] for i in range(1, len(b["t"]))])]
def hour_is(b, hh): return np.array([t[8:] == hh for t in b["t"]])

C = {
    "일봉 정배열": lambda x: x["정배열"],
    "일봉 정배열 + 가르침 수급": lambda x: x["정배열"] and x["가르침"],
    "정배열 문(간격 19~53 · 폭≥50) + 가르침": lambda x: x["정배열"] and 19 <= x["간격"] < 53 and (x["시장폭"] or 0) >= 50 and x["가르침"],
    "추세 문 + 가르침": lambda x: x["추세문"] and x["가르침"],
    "A그룹 꼴(추세 문 또는 정배열 문) + 가르침": lambda x: (x["추세문"] or (x["정배열"] and 19 <= x["간격"] < 53 and (x["시장폭"] or 0) >= 50)) and x["가르침"],
    "A그룹 꼴 + 3일 연속": lambda x: (x["추세문"] or (x["정배열"] and 19 <= x["간격"] < 53 and (x["시장폭"] or 0) >= 50)) and x["가르침"] and x["3일연속"],
    "A그룹 꼴 + 자사주 공시 20일": lambda x: (x["추세문"] or (x["정배열"] and 19 <= x["간격"] < 53 and (x["시장폭"] or 0) >= 50)) and x["가르침"] and x["자사주20"],
}
print("== 1시간봉 2회차 ==  (k봉 뒤 평균 %(이긴 몫)) — 같은 재료 안에서 '언제 사나'를 견줌", flush=True)
H.show("기준: 아무 봉", H.study(data, lambda c, b: np.ones(len(b["c"]), bool), uni, K, edge=False), K)
for name, f in C.items():
    print(f"-- {name}", flush=True)
    base = lambda c, b, f=f: ctxmask(c, b, f)
    H.show("재료가 켜진 날 아무 봉", H.study(data, base, uni, K, edge=False), K)
    # 재료 날의 첫 봉을 사려면 신호 봉 = 전날 마지막 봉(그 봉이 닫힌 뒤 = 전날 장 끝, 재료는 이미 전날 종가로 앎)
    # → 다음 봉 시가 = 오늘 09시 시가. 전날 마지막 봉이 신호가 되므로 오늘 재료(=전날 종가 값)만 씀, 미래 참조 없음.
    def open_buy(c, b, f=f):
        m = base(c, b); fb = first_bar(b)
        on = m & fb
        sig = np.zeros(len(m), bool); sig[np.flatnonzero(on)[np.flatnonzero(on) > 0] - 1] = True
        return sig
    H.show("재료 날 아침 09시 시가에 삼", H.study(data, open_buy, uni, K, edge=False), K)
    H.show("재료 날 10시 시가에 삼(09시 봉 뒤)", H.study(data, lambda c, b, f=f: base(c, b) & hour_is(b, "09"), uni, K, edge=False), K)
    H.show("재료 날 12시 시가에 삼", H.study(data, lambda c, b, f=f: base(c, b) & hour_is(b, "11"), uni, K, edge=False), K)
    H.show("재료 날 09시 봉이 음봉이면 10시에 삼", H.study(
        data, lambda c, b, f=f: base(c, b) & hour_is(b, "09") & (b["c"] < b["o"]), uni, K, edge=False), K)
    H.show("재료 날 1시간봉 A 정배열 됨", H.study(
        data, lambda c, b, f=f: base(c, b) & (H.states(c, b, "A")["정배열"] == 1), uni, K), K)
    H.show("재료 날 1시간봉 20봉선 되올라섬", H.study(
        data, lambda c, b, f=f: base(c, b) & (H.states(c, b, "A")["이격20"] > 0) & (np.r_[np.nan, H.states(c, b, "A")["이격20"][:-1]] <= 0), uni, K), K)
    H.show("재료 날 1시간봉 60봉선까지 눌림(이격60 ≤ 0)", H.study(
        data, lambda c, b, f=f: base(c, b) & (H.states(c, b, "A")["이격60"] <= 0), uni, K), K)
print("끝", flush=True)
