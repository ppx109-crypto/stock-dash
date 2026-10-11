"""MIX-0054 운영 계산(사용자 2026-10-11 "최종으로 모의투자 운영 계산해줘") — 주문 · 설정 바꾸기 없음(계산만).
- 최종 판: 15분봉 뺌 · 1일봉 0.5 · 바구니 0.3 · 빈칸 엔진 · 인버스 켬 · 계좌 흔들림 상한 m1 + 덧붙임(n24 · persist 3 · r10m5 · above_only ·
  상승 → 122630 레버리지 0.4 · 횡보 → 114800 인버스 0.4 · 하락 → 덧붙임 없음).
- 국면 판정은 연구 코드(regime_dev.features · states)를 그대로 부름. 재료는 069500 종가뿐(24일선 · 10일 수익) → 최신 날까지 셀 수 있음.
- 같은지 확인: 2017-02-01 ~ 2026-09-15 국면이 결과 셈(MIX-0054 최종 칸 account의 nst)과 하루도 다르지 않아야 함.
- 내는 것: 최근 국면 · 다음 거래일 목표 · 바꿈이 일어난 날 수 · 1억 원 예시 금액(공개 저장소라 실제 계좌 금액은 쓰지 않음)."""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("REG_BOX", "MIX-0054")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402

FINAL_BASE, FINAL_OV = (0.5, 0.3), "L0.4_S0.4"
CFG = dict(D.R0, **M.OVERLAYS[FINAL_OV])
CODE = {"상승": "122630(KODEX 레버리지)", "횡보": "114800(KODEX 인버스)", "하락": "없음"}


def live_states():
    px = {str(d): float(c) for d, c in json.load(open(ROOT / "etf-data/069500.json"))["closes"] if c}
    feat = D.features({"069500": px}, {}, {})
    return D.states(feat, CFG), feat


def research_states():
    D.BASE_CSV = M.BASES / f"{M.name(FINAL_BASE)}.csv"
    D.DATA, D.FEAT = None, None
    navs, nst = D.account(CFG)
    return nst, D.stats(navs, nst)


def main():
    st, feat = live_states()
    nst, r = research_states()
    days = sorted(st)
    prev = {days[i]: days[i - 1] for i in range(1, len(days))}
    mism = [d for d in nst if nst[d] != st.get(prev.get(d))]              # nst[d] = 전날 장 끝 판정
    last = days[-1]
    recent = [{"날": d, "종가": feat[d]["close"], "24일선": round(D.ma_of(feat[d], 24), 1), "10일 수익 %": round(feat[d]["r10"] * 100, 2),
               "그날 판정(버팀 전)": D.raw_state(feat[d], CFG), "국면(버팀 뒤)": st[d]} for d in days[-15:]]
    switches = [d for d in days if d >= "20170201" and prev.get(d) and st[d] != st[prev[d]]]
    by_year = {}
    for d in switches:
        by_year[d[:4]] = by_year.get(d[:4], 0) + 1
    acc = 100_000_000
    tgt = {"상승": 0.4, "횡보": 0.4, "하락": 0.0}[st[last]]
    out = {"same_as_research": {"days_compared": len(nst), "mismatch": len(mism), "first_mismatch": mism[:3],
                                "research_annual_pct": r["annual_pct"], "research_worst_month_pct": r["worst_month_pct"]},
           "last_data_day": last, "state_at_last_close": st[last], "next_day_target": {"ETF": CODE[st[last]], "share_of_account": tgt,
           "amount_per_100m_won": int(acc * tgt), "cap": "그날 계좌의 놀던 현금까지(빚 없음) · 모자라면 ETF부터 덜기"},
           "recent": recent, "switches_total": len(switches), "switches_per_year": by_year,
           "state_days_2017_on": {k: sum(1 for d in days if d >= "20170201" and st[d] == k) for k in ("상승", "횡보", "하락")}}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
