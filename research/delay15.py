"""15분봉 봇이 늦게 돌면 얼마나 달라지나(사용자 2026-10-06 "15m봇을 30분늦게 진입한걸로 백테스트진행해줘 · 월마다 상세분석").

운영 규칙 = 15분봉 22회차(q027 바탕 · research/px15.py의 '바탕'과 같음). 백테스트는 봉이 닫히면 판단 → 다음 봉 시가에 체결.
늦음 D칸(15분 × D): 판단은 그대로 그 봉에서 하고, 체결만 D칸 뒤 봉 시가로 미룸.
- 사기 늦춤: 신호를 D칸 뒤로 밀어 넣음(그 칸이 닫힌 뒤 → 다음 봉 시가 = 원래보다 15분 × D 늦게 삼).
- 팔기 늦춤: 파는 판단이 난 봉을 적어 두고 D칸 뒤에 내보냄(그 사이 판단을 다시 하지 않음).
판단은 모두 그 시각까지의 값만 씀(늦출 뿐 앞당기지 않음 → 미래 참조 없음 · hlab 체결 감사 그대로 통과).
월별 손익 = 날마다 계좌 값(실현 + 평가, 처음 자금 = 100) 곡선의 그 달 변화(%p) · 씨앗 SEEDS개 가운데 값.
9월(최종 시험지)은 잠가 둔 그대로 — 2025-09-17 ~ 2026-08-31만.
python research/delay15.py
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
os.chdir("/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])

SEEDS = int(os.environ.get("DELAY_SEEDS", "8"))


def shift(sig, d):
    if d <= 0:
        return sig
    out = {}
    for c, s in sig.items():
        z = np.zeros_like(s)
        z[d:] = s[:-d]
        out[c] = z
    return out


def late_exit(d):
    if d <= 0:
        return exit_rule

    def ex(c, b, p, k):
        if "_늦음" in p:
            at, n = p["_늦음"]
            if k >= at + d:
                del p["_늦음"]
                return n
            return 0
        n = exit_rule(c, b, p, k)
        if n and not (isinstance(n, tuple) and n and n[0] == "add"):
            p["_늦음"] = (k, n)
            return 0 if d else n
        return n
    return ex


def months(curve):
    """날마다 계좌 값 → {YYYYMM: 그 달 변화 %p}(앞 달 끝 대비, 첫 달은 1.0 대비)."""
    out, prev, last_m = {}, 1.0, None
    for day in sorted(curve):
        m = day[:6]
        if last_m and m != last_m:
            prev = out_end
        out[m] = (curve[day] - prev) * 100
        out_end, last_m = curve[day], m
    return out


def run(tag, d_in, d_out):
    sg = shift(SGF, d_in)
    rk = rank_plus(tiers(sg)) if d_in else RKF
    ex = late_exit(d_out)
    sigs = {c: np.asarray(sg[c], bool) for c in data if not c.startswith("K")}
    per_month = defaultdict(list)
    summary = {}
    for name, (lo, hi) in M.PERIODS:
        runs = [H._one_run(data, sigs, ex, size, lo, hi, 10, s, None, rk, H.COST, stale_of=stale90) for s in range(SEEDS)]
        runs = [r for r in runs if r]
        summary[name] = {k: float(np.median([r[k] for r in runs])) for k in ("매매", "연", "골", "승률")}
        for r in runs:
            for m, v in months(r["곡선"]).items():
                per_month[m].append(v)
    mm = {m: float(np.median(v)) for m, v in sorted(per_month.items())}
    print(f"{tag:22s} " + " | ".join(f"{n} 매매 {s['매매']:.0f} 연 {s['연']:.1f} 골 {s['골']:.1f} 승률 {s['승률']:.0f}" for n, s in summary.items()), flush=True)
    return summary, mm


CASES = (("지금 백테스트", 0, 0), ("15분 늦게 사기", 1, 0), ("30분 늦게 사기", 2, 0), ("30분 늦게 사고팔기", 2, 2))
res = {tag: run(tag, a, b) for tag, a, b in CASES}
ms = sorted(set().union(*(r[1] for r in res.values())))
print("\n월 · " + " · ".join(t for t, *_ in CASES) + " (계좌 %p · 씨앗 가운데)")
for m in ms:
    print(f"{m[:4]}-{m[4:]} " + " ".join(f"{res[t][1].get(m, float('nan')):8.1f}" for t, *_ in CASES))
print("합   " + " ".join(f"{sum(res[t][1].values()):8.1f}" for t, *_ in CASES))
import json
json.dump({t: {"요약": res[t][0], "월": res[t][1]} for t, *_ in CASES}, open("/tmp/claude-0/delay15.json", "w"), ensure_ascii=False)
