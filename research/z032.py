"""B10 · B9① — 봇 강화(docs/RL-BOTS.md · 오푸스 검토 ③ · ④).
B10: 1일봉 '가르침'(전날까지 n일 외국인 + · 투신 + · 개인 −)을 n = 3 · 5 · 7 가운데 둘 이상 맞으면 → 봉우리(5일)에 덜 기대게. 두 반 모두 같거나 나을 때만.
B9①: 지금 장부(씨앗 0 매매)를 공매도 금지 기간(2020-03-16 ~ 2021-05-02 · 2023-11-06 ~ 2025-03-30) 산 매매 · 그 밖으로 나눠 매매당 손익 · 이길 확률 · 해마다 몫.
python research/z032.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402
import rule  # noqa: E402

BAN = (("20200316", "20210502"), ("20231106", "20250330"))


def vote(r):
    return sum(bool(nrl.teacher(r, n)) for n in (3, 5, 7)) >= 2


def main():
    print("== B10: 가르침 다수결 · B9①: 공매도 금지 기간 나눠 보기 ==", flush=True)
    base = T.once("지금(새 82)", holds=nrl.BASE_HOLD)
    got = T.once("가르침 3 · 5 · 7일 가운데 둘 이상", holds=lambda r: (rule.holds(r) or nrl.aligned(r)) and vote(r) and not nrl.target_cut(r))
    T.diff_check(base, got)
    inban = lambda d: any(a <= d <= b for a, b in BAN)
    for side in ("앞", "뒤"):
        led = base[side]["매매목록"]
        for lab, sel in (("금지 기간에 산 매매", lambda t: inban(t["산 날"])), ("허용 기간에 산 매매", lambda t: not inban(t["산 날"]))):
            ts = [t for t in led if sel(t)]
            if not ts:
                continue
            acc = sum(t["손익"] * t["자리"] for t in ts) / nrl.SLOTS
            win = sum(t["손익"] > 0 for t in ts) / len(ts)
            avg = sum(t["손익"] for t in ts) / len(ts)
            print(f"  {side} {lab}: {len(ts)}건 · 매매당 {avg:+.2f}% · 이길 확률 {win:.0%} · 계좌 몫 합 {acc:+.1f}%", flush=True)


if __name__ == "__main__":
    main()
