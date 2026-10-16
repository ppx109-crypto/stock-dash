"""MPOS-0018 H1 자료 감사(수익률 안 봄 · GPT #443): opinion-data에서 '실제 투자의견 상향' 사건이 몇 건인지.
1) 의견 표기 모음 → 등급 사다리(매도 1 · 비중축소/시장하회 2 · 중립/보유 3 · 매수/비중확대 4 · 강력매수 5)로 묶음(표기 바꿈 '매수 ↔ BUY'는 같은 등급).
2) 상향 = 같은 줄의 prior_opinion 등급 < opinion 등급, 그리고 같은 증권사의 직전 관측 등급도 opinion보다 낮음(둘 다 확인 · 둘 중 하나만 맞으면 '불일치'로 셈).
3) 신규 커버리지(그 증권사의 첫 관측)는 상향과 분리 · 같은 종목 같은 날 여러 증권사 상향은 한 사건.
출력: 표기 목록 · 사다리에 안 들어간 표기 · 연도별 사건 수 · 불일치 수(성과 없음)."""
import collections
import json
from pathlib import Path

ROOT = Path("/home/user/stock-dash/opinion-data")
LADDER = {}
for k in ("SELL", "매도", "STRONG SELL", "강력매도"):
    LADDER[k] = 1
for k in ("UNDERPERFORM", "REDUCE", "UNDERWEIGHT", "비중축소", "시장수익률하회", "MARKETUNDERPERFORM", "TRADING SELL", "SELL(유지)"):
    LADDER[k] = 2
for k in ("HOLD", "NEUTRAL", "중립", "보유", "MARKETPERFORM", "MARKET PERFORM", "시장수익률", "INLINE", "TRADING BUY", "NOT RATED", "N/R", "NR", "단기매수"):
    LADDER[k] = 3
for k in ("BUY", "매수", "OUTPERFORM", "OVERWEIGHT", "비중확대", "시장수익률상회", "MARKETOUTPERFORM", "ACCUMULATE", "ADD", "매수(유지)", "BUY(유지)"):
    LADDER[k] = 4
for k in ("STRONG BUY", "STRONGBUY", "강력매수", "적극매수", "TOP PICK"):
    LADDER[k] = 5
NOT_RATING = {"NOT RATED", "N/R", "NR"}


def norm(x):
    return (x or "").strip().upper().replace("  ", " ")


labels = collections.Counter()
events, firsts, mismatch, unknown = [], 0, 0, collections.Counter()
MM, MMY = collections.Counter(), collections.Counter()
files = sorted(ROOT.glob("*.json"))
for f in files:
    d = json.load(open(f))
    last = {}
    for r in sorted(d.get("rows") or [], key=lambda x: x["date"]):
        o, po, m = norm(r.get("opinion")), norm(r.get("prior_opinion")), r.get("member")
        labels[o] += 1
        if o and o not in LADDER:
            unknown[o] += 1
        g, gp = LADDER.get(o), LADDER.get(po)
        prev = last.get(m)
        if prev is None:
            firsts += 1
        elif g is not None and o not in NOT_RATING:
            up_line = gp is not None and po not in NOT_RATING and gp < g
            up_prev = prev[0] is not None and prev[1] not in NOT_RATING and prev[0] < g
            if up_line and up_prev:
                events.append((d["code"], r["date"], m, po, o))
            elif up_line != up_prev:
                mismatch += 1
                MM["줄의 prior만 상향"] += up_line
                MM["증권사 직전 관측만 상향"] += up_prev
                if up_line:
                    MMY[r["date"][:4]] += 1
        if g is not None:
            last[m] = (g, o)
uniq = sorted({(c, dt) for c, dt, *_ in events})
by_year = collections.Counter(dt[:4] for _, dt in uniq)
out = {"파일 수": len(files), "표기 종류": len(labels), "많은 표기 20": labels.most_common(20), "사다리 밖 표기": unknown.most_common(30),
       "증권사 첫 관측(신규 커버리지 · 상향 아님)": firsts, "상향 줄(두 확인 모두)": len(events), "줄 확인 불일치": mismatch,
       "상향 사건(종목 · 날 묶음)": len(uniq), "연도별 사건": dict(sorted(by_year.items())), "사건 있는 종목 수": len({c for c, _ in uniq}),
       "예시 5": events[:5], "불일치 나눔": dict(MM), "prior만 상향 연도별": dict(sorted(MMY.items())),
       "주의": "TRADING BUY는 중립(3)으로 묶음 · 등급 체계는 증권사마다 다를 수 있음(확인 안 함) · 날짜는 발표일 단위 · 발표 시각 없음"}
json.dump(out, open(Path(__file__).with_suffix(".json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "많은 표기 20"}, ensure_ascii=False))
print("많은 표기", out["많은 표기 20"])
