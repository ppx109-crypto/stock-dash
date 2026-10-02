"""겹침 추가 배팅(사용자 2026-10-02: "1H 신호보다 1일봉의 신뢰도가 더 높은데 겹침이 있다는 건 1h봉 종목의 신뢰도 향상 → 추가 배팅").
1시간봉 최고 규칙(123회차 기준 = 94 + 101 거르기 · 씨앗 16)에서, 사는 신호 봉의 날 d에 1일봉 규칙(새 82)과 겹치면 칸을 늘림.
겹침(그 봉 때 이미 알 수 있는 것만):
  보유 = 1일봉 규칙이 그 종목을 들고 있음(산 날 < d ≤ 판 날 · 1일봉 매매 목록 씨앗 0 = scratchpad/x008_d1.json)
  신호 = 전 거래일 장 끝 1일봉 사는 조건(nrl.BASE_HOLD)이 맞았음(칸이 없어 못 산 것 포함)
Q_SRC=yahoo(3년 · 기본) · kis(한투 1년). Q_PART=1: 겹침별 매매 성적(기준 판) + 칸 늘리기 판."""
import bisect
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import hlab as H
import kis1h

src = os.environ.get("Q_SRC", "yahoo")
PER = kis1h.use() if src == "kis" else None
exec(open("/home/user/stock-dash/research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
SG = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
rk = rk_of(tiers(20, 5, 3))
BASE_SIZE = size

# ── 1일봉 규칙: 보유 구간 · 사는 조건 날
import nrl
LED = json.load(open("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/x008_d1.json"))
HOLD = {}
for code, b, s, g, k in LED:
    HOLD.setdefault(code, []).append((b, s))
SIG = {(r["code"], r["date"]) for pool in (nrl.early, nrl.inside) for r in pool if nrl.BASE_HOLD(r)}
DAYS = sorted({r["date"] for r in nrl.inside} | {r["date"] for r in nrl.early})


def prev_day(d):
    k = bisect.bisect_left(DAYS, d)
    return DAYS[k - 1] if k else None


def held(code, d):
    return any(b < d <= s for b, s in HOLD.get(code, ()))


def signal(code, d):
    p = prev_day(d)
    return p is not None and (code, p) in SIG


KINDS = {"보유": held, "신호": signal, "보유 또는 신호": lambda c, d: held(c, d) or signal(c, d)}


def sized(kind, plus=None, mult=None, cap=6):
    test = KINDS[kind]

    def f(c, b, k):
        n = BASE_SIZE(c, b, k)
        if not test(c, b["t"][k][:8]):
            return n
        return int(min(cap, n + plus if plus is not None else round(n * mult)))
    return f


def go(tag, sz, seeds=16):
    kw = {"periods": PER} if PER else {}
    res = H.simulate(data, lambda c, b: SG[c], EX, sz, rank=rk, stale_of=stale90, seeds=seeds, **kw)
    print(f"  {tag:34s} " + H.line(res), flush=True)
    return res


print(f"== 겹침 추가 배팅 ({'한투 1년' if src == 'kis' else '야후 3년'} · {len(data)}종목) · 1일봉 신호 날 {len(SIG)} ==", flush=True)
base = go("기준(1시간봉 123회차 기준)", BASE_SIZE)
print("  [기준 판 매매를 겹침으로 나눔 — 씨앗 0 목록 · 손익은 매매 %]", flush=True)
for side, r in base.items():
    if not r:
        continue
    rows = r["목록"]
    for kind, test in KINDS.items():
        on = [t for t in rows if test(t["code"], str(t["산 때"])[:8])]
        off = [t for t in rows if not test(t["code"], str(t["산 때"])[:8])]
        av = lambda xs: (sum(t["손익"] for t in xs) / len(xs)) if xs else float("nan")
        win = lambda xs: (sum(t["손익"] > 0 for t in xs) / len(xs) * 100) if xs else float("nan")
        print(f"    {side} {kind:10s} 겹침 {len(on):3d}건 평균 {av(on):+5.2f}% 이김 {win(on):4.1f} | 안 겹침 {len(off):3d}건 평균 {av(off):+5.2f}% 이김 {win(off):4.1f}", flush=True)
for kind in KINDS:
    go(f"{kind} → +1칸(최대 6)", sized(kind, plus=1))
    go(f"{kind} → +2칸(최대 6)", sized(kind, plus=2))
    go(f"{kind} → ×1.5(최대 6)", sized(kind, mult=1.5))
print("끝", flush=True)
