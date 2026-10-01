"""일봉 새 85회차 — 사용자 질문(2026-10-01): "②정배열로 산 매도는 기간이 지나면 자동 매도는 없어? 없으면 테스트해서 적용시 좋아지는지".
지금 ②는 기간 제한 없음(최대 60일은 새 20회차에 뺌 — 60일 넘게 이어진 매매가 없어서). 더 짧은 기간 청산을 더해 봄:
- 기간 청산 N거래일(10 · 20 · 30 · 40 · 60): N일째 종가에 남은 것을 모두 팖.
- 느린 것만 청산: N일째에 이익이 +3% 미만인 매매만 팖(10 · 20 · 30).
씨앗 8 · 두 반 · 행운뺌 · 큰2건뺌 · 막힌/바뀐 매매 직접 봄. 기준 = 새 82회차 규칙.
"""
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import lab
import rule


def broken_n(days, gain=None):
    def go(lane, start, price, step, peak, row=None):
        if nrl.broken(lane, start, price, step, peak, row):
            return True
        if step >= days:
            now = (lane["closes"][start + step] / price - 1) * 100
            return gain is None or now < gain
        return False
    return go


def exits(days, gain=None):
    return lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": broken_n(days, gain)})


print("== 일봉 새 85회차: ②정배열 매매에 기간 청산 더하기 ==", flush=True)
base = T.once("기준(새 82회차, 기간 제한 없음)")
for side in ("앞", "뒤"):
    g = base.get(side)
    if not g:
        continue
    held = [t.get("보유") for t in g["매매목록"] if t.get("행") is not None and not rule.holds(t["행"]) and t.get("보유") is not None]
    if held:
        q = statistics.quantiles(held, n=10)
        print(f"      {side} ②정배열 매매 보유일: {len(held)}건 · 가운데 {statistics.median(held)}일 · 90% {q[-1]:.0f}일 · 가장 긴 {max(held)}일", flush=True)
for n in (10, 20, 30, 40, 60):
    got = T.once(f"②기간 청산 {n}거래일", exit_at=exits(n))
    T.diff_check(base, got)
for n in (10, 20, 30):
    got = T.once(f"②{n}일째 +3% 못 가면 청산", exit_at=exits(n, 3))
    T.diff_check(base, got)
print("끝", flush=True)
