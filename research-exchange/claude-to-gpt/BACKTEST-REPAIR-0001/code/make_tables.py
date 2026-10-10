"""results.json → 비교표(tables.md) · 판정(verdicts.json). PREREG §6 판정 규칙을 그대로 코드로.
python3 make_tables.py <results.json> <출력 폴더>"""
import json
import sys
from pathlib import Path

R = json.load(open(sys.argv[1], encoding="utf-8"))["runs"]
OUT = Path(sys.argv[2])
P = ("Train 2017-02~2020-12", "Validation 2021~2022", "다시 본 2023-01~2026-09", "전체")
COLS = ("기간", "종목", "거래", "CAGR", "CAGR 비용 전", "MDD", "Sharpe", "Sortino", "PF", "승률", "평균 손익%", "95% CI", "보유일",
        "최악 하루", "최악 달력월", "기준 넘음(하루/달)", "비용 합(시작 대비%)", "자금활용%")


def row(label, rep):
    if not rep:
        return f"| {label} | " + " | ".join(["검증하지 못함"] + [""] * (len(COLS) - 1)) + " |"
    v = [f"{rep['from']}~{rep['to']}", rep["codes"], rep["trades"], rep["CAGR"], rep["CAGR_gross"], rep["MDD_daily"], rep["Sharpe"],
         rep["Sortino"], rep["PF"], rep["win_rate"], rep["avg_ret_net_pct"], rep["ci95_avg_ret_net_pct"], rep["avg_hold_tdays"],
         rep["worst_day"], f"{rep['worst_month']}({rep['worst_month_at']})", f"{rep['day_breach_-15']}/{rep['month_breach_-15']}",
         rep["cost_total_pct_of_start"], rep["utilization_avg_pct"]]
    return f"| {label} | " + " | ".join("" if x is None else str(x) for x in v) + " |"


def table(title, runs, periods=P):
    lines = [f"### {title}", "", "| 판 · 기간 | " + " | ".join(COLS) + " |", "|" + "---|" * (len(COLS) + 1)]
    for label, key in runs:
        rr = R.get(key)
        if rr is None:
            lines.append(f"| {label} | 검증하지 못함(실행 없음) |" + " |" * (len(COLS) - 1))
            continue
        for p in periods:
            lines.append(row(f"{label} · {p}", rr["report"].get(p)))
    return "\n".join(lines) + "\n"


def verdict(key, key2, short_data=False):
    rr, r2 = R.get(key), R.get(key2)
    if not rr or not rr["report"].get("전체"):
        return "증거 부족", "계산 불가"
    a, b = rr["report"]["전체"], (r2 or {}).get("report", {}).get("전체") or {}
    ci = a.get("ci95_avg_ret_net_pct")
    if short_data or (a.get("trades") or 0) < 30:
        return "증거 부족", f"자료 1년 이하 또는 거래 {a.get('trades')}건"
    if (a.get("CAGR") or 0) <= 0 or (ci and ci[1] < 0):
        return "폐기 후보", f"보수 · 기본 비용 CAGR {a.get('CAGR')}% · CI {ci}"
    ok = [ci and ci[0] > 0, a.get("day_breach_-15") == 0, a.get("month_breach_-15") == 0, (b.get("CAGR") or -1) > 0]
    if all(ok):
        return "유지", f"CAGR {a.get('CAGR')}% · CI {ci} · 기준 안 넘음 · 2배 비용 CAGR {b.get('CAGR')}%"
    miss = [n for n, k in zip(("CI 하한 > 0", "하루 기준", "달력월 기준", "2배 비용 CAGR > 0"), ok) if not k]
    return "보완 후보", f"CAGR {a.get('CAGR')}% > 0이나 못 지킴: {', '.join(miss)}"


S = []
S.append(table("1일봉 새82 — 수정 전(원장 ASIS) vs 수정 후(FIX = K1 수급 지연 + K2 달별 calm)", [
    ("ASIS · 종가 근사 · 비용 1배", "D1_ASIS_close_x1"), ("ASIS · 보수 · 비용 1배", "D1_ASIS_next_x1"),
    ("K1만 · 보수 · 1배", "D1_K1_next_x1"), ("K2만 · 보수 · 1배", "D1_K2_next_x1"),
    ("FIX · 종가 근사 · 1배", "D1_FIX_close_x1"), ("FIX · 보수 · 1배", "D1_FIX_next_x1"), ("FIX · 보수 · 2배", "D1_FIX_next_x2")]))
S.append(table("15분봉 22회차 — 수정 전(ASIS) vs 수정 후(K1 수급 지연 = FLOW-LAG2) · 바 시가 체결(정확재현)", [
    ("ASIS · 1배", "M15_ASIS_x1"), ("ASIS · 2배", "M15_ASIS_x2"), ("K1 · 1배", "M15_FLOW-LAG2_x1"), ("K1 · 2배", "M15_FLOW-LAG2_x2")],
    periods=("전체",)))
S.append(table("빈칸 엔진 + 코스닥 인버스(한 소매) — 수정 전(종가 근사 · used = 1일봉 ASIS) vs 수정 후(보수 · used = 1일봉 FIX 보수)", [
    ("소매 ASIS · 종가 근사 · 1배", "ETF_sleeve_ASIS_close_x1"), ("소매 FIX · 종가 근사 · 1배", "ETF_sleeve_FIX_close_x1"),
    ("소매 FIX · 보수 · 1배", "ETF_sleeve_FIX_next_x1"), ("소매 FIX · 보수 · 2배", "ETF_sleeve_FIX_next_x2"),
    ("엔진만 ASIS · 종가 · 1배", "ETF_engine_ASIS_close_x1"), ("엔진만 FIX · 보수 · 1배", "ETF_engine_FIX_next_x1"), ("엔진만 FIX · 보수 · 2배", "ETF_engine_FIX_next_x2"),
    ("인버스만 ASIS · 종가 · 1배", "ETF_inverse_ASIS_close_x1"), ("인버스만 FIX · 보수 · 1배", "ETF_inverse_FIX_next_x1"), ("인버스만 FIX · 보수 · 2배", "ETF_inverse_FIX_next_x2")]))
S.append(table("바구니 C — 수정 전(ASIS 제목 그대로 · 종가 근사 = 연구 P4b) vs 수정 후(K3 제목 정제 · 보수)", [
    ("ASIS · 종가 근사 · 1배", "BASKET_ASIS_close_x1"), ("K3만 · 종가 근사 · 1배", "BASKET_K3_close_x1"),
    ("ASIS · 보수 · 1배", "BASKET_ASIS_next_x1"), ("FIX · 보수 · 1배", "BASKET_FIX_next_x1"), ("FIX · 보수 · 2배", "BASKET_FIX_next_x2")]))
(OUT / "tables.md").write_text("\n".join(S), encoding="utf-8")

V = {
    "1일봉 새82": verdict("D1_FIX_next_x1", "D1_FIX_next_x2"),
    "15분봉": verdict("M15_FLOW-LAG2_x1", "M15_FLOW-LAG2_x2", short_data=True),
    "빈칸 엔진": verdict("ETF_engine_FIX_next_x1", "ETF_engine_FIX_next_x2"),
    "코스닥 인버스": verdict("ETF_inverse_FIX_next_x1", "ETF_inverse_FIX_next_x2"),
    "엔진 + 인버스 소매": verdict("ETF_sleeve_FIX_next_x1", "ETF_sleeve_FIX_next_x2"),
    "바구니 C": verdict("BASKET_FIX_next_x1", "BASKET_FIX_next_x2"),
}
(OUT / "verdicts.json").write_text(json.dumps(V, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in V.items():
    print(k, v)
