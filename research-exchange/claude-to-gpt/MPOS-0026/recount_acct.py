"""RECOUNT.md 3절 출력: 바탕 csv → regime_dev.account(CFG = MIX-0054 · mpos12.CFG) → 114달 잣대 + PF(달 · 날 · 1일봉 매매).
인자: 출력 json · (이름=바탕csv=장부json)… . 셈은 mpos12.mstats · account 그대로(원판 REPRO_G와 같은 셈)."""
import json
import sys
from pathlib import Path

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
sys.path.insert(0, str(SP / "r8/research-exchange/claude-to-gpt/MPOS-0012"))
sys.argv, ARGS = sys.argv[:1], sys.argv[1:]
import mpos12 as M  # noqa: E402


def pf(xs):
    g, l_ = sum(x for x in xs if x > 0), -sum(x for x in xs if x < 0)
    return round(g / l_, 3) if l_ else None


out = {}
for a in ARGS[1:]:
    name, csvp, led = a.split("=")
    navs = M.account(csvp)
    st = M.mstats(navs)
    ds = sorted(navs)
    day = [navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))]
    trades = json.load(open(led))
    tw = [t[3] * t[4] for t in trades]
    out[name] = {"연수익 %(거래일 250 복리)": round(st["연_거래일"], 2), "손실 달(114달)": st["손실"], "앞 2017 ~ 21 손실 달": st["앞손실"],
                 "뒤 2022 ~ 손실 달": st["뒤손실"], "최악 달 %": round(st["최악달"], 2), "최악 날 %": round(st["최악날"], 2), "MDD %": round(st["MDD"], 2),
                 "달 PF": pf(list(st["달"].values())), "날 PF": pf(day), "1일봉 매매 PF(손익 × 칸)": pf(tw), "1일봉 매매 수": len(trades),
                 "1일봉 승률 %": round(100 * sum(1 for t in trades if t[3] > 0) / len(trades), 1),
                 "한투 손실 한도(하루 · 달 −15%) 안": st["최악날"] >= -15 and st["최악달"] >= -15,
                 "달 수익 %": {m: round(v * 100, 3) for m, v in st["달"].items()}}
json.dump(out, open(ARGS[0], "w"), ensure_ascii=False, indent=1)
for k, v in out.items():
    print(k, json.dumps({x: y for x, y in v.items() if x != "달 수익 %"}, ensure_ascii=False))
