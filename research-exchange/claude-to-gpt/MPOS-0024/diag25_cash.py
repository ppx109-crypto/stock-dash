"""H-USD 3단계 준비(GPT #454 USD-B): 최종 계좌(MIX-0054 BASE = REPRO_G)의 매일 '남는 현금' 경로 — 달러 ETF 손익은 안 봄.
regime_dev.account 원문에 기록 한 줄만 끼워(inspect 원문 · 줄 하나 추가) 같은 셈을 돌리고, 날별 NAV가 원본 account와 한 칸도 다르지 않은지 assert.
남는 현금(slack) = 계좌 현금 + 1일봉 몫 안 놀던 현금(vb × base 현금 몫) — account 안 '빚 없음 점검'과 같은 식(regime_dev.py:271).
보고: slack ÷ NAV 분포(전체 · 앞 ≤ 2021-12 · 뒤) · 10/20/30% 아래인 날 몫 · 'NAV의 x%를 달 첫날 넣고 그대로 두면' slack이 그 몫보다 작아져
억지로 팔아야 했을 날 수(손익 없이 현금 수준만 · 달러 값 변화 안 넣음 → 근사)."""
import hashlib
import inspect
import json
import sys
import textwrap
from pathlib import Path

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")   # 계산 폴더(MPOS-0012 묶음 · MPOS-0021 base_BASE.csv)
sys.path.insert(0, str(SP / "r8/research-exchange/claude-to-gpt/MPOS-0012"))
import mpos12 as M  # noqa: E402

Dv = M.Dv
BASE_CSV = SP / "mpos21/base_BASE.csv"
Dv.BASE_CSV, Dv.DATA, Dv.FEAT = BASE_CSV, None, None
ref = Dv.account(dict(M.CFG))[0]
src = textwrap.dedent(inspect.getsource(Dv.account))
anchor = "        navs[d] = vb + ve + cash\n"
assert src.count(anchor) == 1
src = src.replace(anchor, anchor + "        REC.append((d, vb + ve + cash, vb, ve, cash, base[d][1], code))\n").replace("def account(", "def account_rec(")
REC = []
g = dict(Dv.__dict__)
g["REC"] = REC
exec(compile(src, "regime_dev.account+기록", "exec"), g)
Dv.DATA, Dv.FEAT = None, None
navs = g["account_rec"](dict(M.CFG))[0]
assert navs == ref, "기록판 NAV가 원본과 다름"
rows = [{"날": d, "NAV": A, "1일봉": vb, "덧붙임": ve, "현금": c, "1일봉 현금 몫": bc, "덧붙임 종목": code, "slack": c + vb * bc} for d, A, vb, ve, c, bc, code in REC]


def q(xs, p):
    xs = sorted(xs)
    return xs[int(p * (len(xs) - 1))]


def summ(rs):
    f = [r["slack"] / r["NAV"] for r in rs]
    return {"날 수": len(rs), "분위 5 · 25 · 50 · 75 · 95%": [round(q(f, p) * 100, 1) for p in (.05, .25, .5, .75, .95)],
            "slack < 10% 날 몫 %": round(sum(x < .1 for x in f) / len(f) * 100, 1), "< 20%": round(sum(x < .2 for x in f) / len(f) * 100, 1),
            "< 30%": round(sum(x < .3 for x in f) / len(f) * 100, 1), "최소 %": round(min(f) * 100, 2)}


out = {"원본 NAV와 같음": True, "base csv sha256": hashlib.sha256(BASE_CSV.read_bytes()).hexdigest(),
       "전체": summ(rows), "앞(≤ 2021-12)": summ([r for r in rows if r["날"] <= "20211231"]), "뒤": summ([r for r in rows if r["날"] > "20211231"])}
# 덧붙임 종목별 slack(레버리지 들고 있을 때 현금이 줄어드는지)
by = {}
for r in rows:
    by.setdefault(r["덧붙임 종목"] or "없음", []).append(r)
out["덧붙임 종목별"] = {k: summ(v) for k, v in by.items()}
# NAV의 x%를 달 첫날 넣고 그대로 둘 때(근사: 달러 값 변화 · 비용 안 넣음) slack이 모자란 날 수
for x in (.1, .2, .3):
    short, firsts, held_ok = 0, 0, 0
    month, want = None, 0.0
    for r in rows:
        if r["날"][:6] != month:
            month = r["날"][:6]
            firsts += 1
            want = x * r["NAV"]
            held_ok += r["slack"] >= want
        if r["slack"] < want - 1e-12:
            short += 1
    out[f"NAV {int(x * 100)}% 고정 근사"] = {"달 첫날 slack ≥ 목표인 달": f"{held_ok}/{firsts}", "slack < 목표인 날": short, "전체 날": len(rows)}
json.dump(out, open(Path(__file__).with_suffix(".json"), "w"), ensure_ascii=False, indent=1)
json.dump(rows, open(Path(__file__).parent / "cash_path_base.json", "w"), ensure_ascii=False)
print(json.dumps(out, ensure_ascii=False, indent=1))
