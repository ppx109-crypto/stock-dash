"""15분봉 26회차 — 1시간봉 · 일봉 연구에서 해 본 것을 최종 후보(22회차) 위에 옮김(사용자 2026-10-01 "1시간봉과 1일봉에서 연구했던 거 15m에 적용").
Q_PART=1(사는 쪽 · 공시): 희석 공시 20일 거르기(1시간봉 72회차) · 자사주 + 희석 함께(1시간봉 67회차) · 들고 있다 희석 공시가 나면 팔기(1시간봉 82회차)
Q_PART=2(파는 쪽): 추세 +13% 익절 대신 고점 따라가기(1시간봉 58회차) · 추세 절반 판 뒤 본전 지키기(일봉 49회차) ·
                   정배열 +10%에 절반 먼저(1시간봉 70회차) · 과열 꼭대기 팔기(일봉 78회차: 거래량 배수 3↑ · 오늘 +8%↑ · 이익 중)
                   · 장중 시장 −2% 아래면 정배열 매매 정리(일봉 69회차)
161종목 · 씨앗 16 · 비용 0.30%.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('part = os.environ')[0])
exec("def make_exit" + open("/home/user/stock-dash/research/q003.py", encoding="utf-8").read().split("def make_exit", 1)[1].split("def run(tag")[0])

FIN = entry3(al_mkt=-0.01)
SGF = {c: np.asarray(FIN(c, b), bool) for c, b in data.items()}
RKF = rank_plus(tiers(SGF))


def go(tag, sig=None, ex=None, cost=H.COST):
    sg = SGF if sig is None else {c: np.asarray(sig(c, b), bool) for c, b in data.items()}
    rk = RKF if sig is None else rank_plus(tiers(sg))
    res = M.simulate(data, lambda c, b: sg[c], ex or exit_rule, size, rank=rk, stale_of=stale90, seeds=16, cost=cost)
    print(f"  {tag:36s} " + H.line(res), flush=True)


def mat(c, b, k):
    return ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]


def with_cut(test):
    def f(c, b):
        m = SGF[c].copy()
        for k in np.flatnonzero(m):
            x = mat(c, b, k)
            if x and test(x):
                m[k] = False
        return m
    return f


def first(extra, base=None):
    base = base or exit_rule

    def f(c, b, p, k):
        r = extra(c, b, p, k)
        return r if r else base(c, b, p, k)
    return f


kind_of = lambda c, p: door(ATT[c][p["i"]]) or "정배열"
gain = lambda b, p, k: (b["c"][k] / p["price"] - 1) * 100
RVf = {c: np.nan_to_num(RV[c], nan=0.0) for c in data}

part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 26회차({part}): 1시간봉 · 일봉 연구 옮기기 ({len(data)}종목) ==", flush=True)
go("최종 후보 그대로")
if part == "1":
    go("희석 공시 20일 거르기", with_cut(lambda x: x["희석20"]))
    go("자사주 + 희석 공시 거르기", with_cut(lambda x: x["희석20"] or x["자사주20"]))
    go("들고 있다 희석 공시 나면 팔기", ex=first(lambda c, b, p, k: "all" if (mat(c, b, k) or {}).get("희석20")
                                            and not (ATT[c][p["i"]] or {}).get("희석20") else 0))
else:
    for back in (3, 5):
        def trail(c, b, p, k, back=back):
            if kind_of(c, p) != "추세":
                return 0
            top = (p["peak"] / p["price"] - 1) * 100
            return "all" if top >= 13 and gain(b, p, k) <= top - back else 0
        go(f"추세 +13% 뒤 고점 −{back}%p 따라가기", ex=first(trail, make_exit(take=999)))
    go("추세 절반 판 뒤 본전 지키기", ex=first(lambda c, b, p, k: "all" if kind_of(c, p) == "추세" and p["칸"] < p["처음칸"]
                                          and gain(b, p, k) <= 0 else 0))
    go("정배열 +10%에 절반 먼저", ex=first(lambda c, b, p, k: max(1, p["처음칸"] // 2) if kind_of(c, p) == "정배열"
                                     and p["칸"] == p["처음칸"] and gain(b, p, k) >= 10 else 0))
    go("과열 꼭대기 팔기", ex=first(lambda c, b, p, k: "all" if RVf[c][k] >= 3 and nan0(DR[c])[k] >= 0.08 and gain(b, p, k) > 0 else 0))
    go("장중 시장 −2% 아래면 정배열 정리", ex=first(lambda c, b, p, k: "all" if kind_of(c, p) == "정배열" and nan0(MKT[c])[k] < -0.02 else 0))
print("끝", flush=True)
