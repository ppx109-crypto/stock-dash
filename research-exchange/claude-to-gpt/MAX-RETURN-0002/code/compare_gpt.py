"""MAX-RETURN-0002 · GPT_RESULTS(PR #46 head 5308ae74)와 claude_results.json 1회 대조. python3 compare_gpt.py <claude_results.json>
값이 같으면 '일치', 값은 같지만 저장 형식만 다르면(예: 정수 0과 문자열 "0") '형식만 다름', 값이 다르면 '값 다름'."""
import json
import subprocess
import sys

G = json.loads(subprocess.check_output(["git", "-C", "/home/user/stock-dash", "show",
                                        "5308ae74:research-exchange/gpt-to-claude/MAX-RETURN-0002/GPT_RESULTS.json"]))["results"]
C = json.loads(open(sys.argv[1], encoding="utf-8").read())


def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b) <= 1e-9 * max(1, abs(a))
    return a == b


n_val, n_fmt, n_all = 0, 0, 0
for k, g in G.items():
    if k.endswith("_ex_top"):
        c = C[k]
        ia = c["independent_arith"]
        pairs = [("제외 종목", g["excluded"], c["excluded"]), ("CAGR 엔진", g["CAGR_pct"], c["CAGR_engine"]),
                 ("CAGR 따로 산술", g["CAGR_pct"], ia["CAGR"]), ("끝 NAV 따로 산술", g["end_nav_won"], ia["end_nav_won"])]
    else:
        cfg, m = k.split("_x")
        c = C[f"{cfg}_x{float(m)}"]
        e, ia = c["engine_report"], c["independent_arith"]
        pairs = [("포지션", g["positions"], e["positions"]), ("CAGR 엔진", g["CAGR"], e["CAGR"]), ("CAGR 따로 산술", g["CAGR"], ia["CAGR"]),
                 ("MDD 엔진", g["MDD_daily"], e["MDD_daily"]), ("MDD 따로 산술", g["MDD_daily"], ia["MDD_daily"]),
                 ("최악 하루(반올림 전)", g["worst_day_unrounded_pct"], ia["worst_day_unrounded_pct"]),
                 ("최악 날짜 엔진", g["worst_day_at"], e["worst_day_at"]), ("최악 날짜 따로 산술", g["worst_day_at"], ia["worst_day_at"]),
                 ("하루 −15% 넘음 엔진", g["day_breach_-15"], e["day_breach_-15"]), ("하루 −15% 넘음 따로 산술", g["day_breach_-15"], ia["day_breach_-15"]),
                 ("끝 NAV 엔진", g["end_nav_won"], e["end_nav_won"]), ("끝 NAV 따로 산술", g["end_nav_won"], ia["end_nav_won"]),
                 ("첫 NAV 날", g.get("first", "20250918"), ia["first_nav_day"])]
    vals = [n for n, a, b in pairs if not same(a, b) and str(a) != str(b)]
    fmts = [n for n, a, b in pairs if not same(a, b) and str(a) == str(b)]
    n_all += len(pairs)
    n_val += len(vals)
    n_fmt += len(fmts)
    print(k, f"{len(pairs)}항목", "값 다름 " + ",".join(vals) if vals else "일치", f"(형식만 다름: {','.join(fmts)})" if fmts else "")
print(f"전체 {n_all}항목 · 값 다름 {n_val} · 형식만 다름 {n_fmt}")
