"""겹침 비중 3회(F11) — 15분봉 최종 후보(22회차 · q027 · 한투 1년 161종목 · 씨앗 16)에서 사는 신호 봉의 날이 1일봉 규칙(새 82)과 겹치면 칸 배수.
겹침 정의는 x011과 같음(보유 = 1일봉이 들고 있음 · 신호 = 전 거래일 장 끝 1일봉 사는 조건)."""
import bisect
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
import nrl

LED = json.load(open("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/x008_d1.json"))
HOLD = {}
for code, b0, s0, g, k in LED:
    HOLD.setdefault(code, []).append((b0, s0))
SIG = {(r["code"], r["date"]) for pool in (nrl.early, nrl.inside) for r in pool if nrl.BASE_HOLD(r)}
DAYS = sorted({r["date"] for r in nrl.inside})


def prev_day(d):
    k = bisect.bisect_left(DAYS, d)
    return DAYS[k - 1] if k else None


held = lambda c, d: any(b0 < d <= s0 for b0, s0 in HOLD.get(c, ()))
signal = lambda c, d: (c, prev_day(d)) in SIG
both = lambda c, d: held(c, d) or signal(c, d)
BASE_SIZE = size


def scaled(test, mult, cap=6):
    def f(c, b, k):
        n = BASE_SIZE(c, b, k)
        return int(max(1, min(cap, round(n * mult)))) if test(c, b["t"][k][:8]) else n
    return f


def run(tag, sz):
    res = M.simulate(data, lambda c, b: SGF[c], exit_rule, sz, rank=RKF, stale_of=stale90, seeds=16)
    print(f"  {tag:30s} " + H.line(res), flush=True)
    return res


print(f"== 겹침 비중 3회: 15분봉 ({len(data)}종목 · 한투 1년) ==", flush=True)
base = run("기준(15분봉 22회차)", BASE_SIZE)
for side, r in base.items():
    if not r:
        continue
    rows = r["목록"]
    for name, test in (("보유", held), ("신호", signal), ("보유 또는 신호", both)):
        on = [t for t in rows if test(t["code"], str(t["산 때"])[:8])]
        off = [t for t in rows if not test(t["code"], str(t["산 때"])[:8])]
        av = lambda xs: (sum(t["손익"] for t in xs) / len(xs)) if xs else float("nan")
        print(f"    {side} {name:10s} 겹침 {len(on):3d}건 평균 {av(on):+5.2f}% | 안 겹침 {len(off):3d}건 평균 {av(off):+5.2f}%", flush=True)
for name, test in (("보유 또는 신호", both), ("신호", signal)):
    for mult in (1.25, 1.5, 2.0, 0.5):
        run(f"{name} → ×{mult}", scaled(test, mult, 8 if mult == 2.0 else 6))
print("끝", flush=True)
