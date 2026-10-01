"""15분봉 41회차(줄 3) — 운영 중인 1시간봉 규칙의 손절 · 익절을 15분봉 종가마다 보면(지금은 1시간봉 종가마다).
1시간봉 최고 규칙(같은 15분봉 자료를 1시간으로 묶음 · 씨앗 0)의 매매 줄마다, 산 뒤 ~ 원래 판 때 앞의 15분봉 종가에서
추세 문: −5% 이하 · +13% 이상 / 정배열 문: −10% 이하 · (+8% 닿은 뒤) +1% 이하 가 먼저 나오면 다음 15분봉 시가에 판 것으로 바꿈.
매매 줄 하나당 손익 차이(%p) · 바뀐 줄의 몫 · 두 반. Q_PART=stop(손절만) · take(익절 · 이익 지키기만) · both."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
os.environ["Q_BARS"] = "1h"
exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
import m15lab as M2

M15 = _load(None, os.environ.get("M15_HOME"))     # q_rule이 M.load를 1시간 묶음으로 바꿔 두므로 원래 읽기를 씀
IDX = {c: {t: i for i, t in enumerate(b["t"])} for c, b in M15.items()}
part = os.environ.get("Q_PART", "both")
res = M.simulate(data, lambda c, b: SIGS[c], exit_rule, size, rank=RANK, stale_of=stale90, seeds=1)
print(f"== 15분봉 41회차({part}): 1시간봉 규칙 손절 · 익절을 15분봉 종가로 ({len(data)}종목) ==", flush=True)
for side in ("앞", "뒤"):
    d, changed, w = [], 0, 0
    for t in res[side]["목록"]:
        c = t["code"]
        if str(t["판 때"]).startswith("끝") or c not in IDX:
            continue
        b15 = M15[c]
        i0, i1 = IDX[c].get(t["산 때"]), IDX[c].get(t["판 때"])
        if i0 is None or i1 is None:
            continue
        price = b15["o"][i0]
        kind = door(ATT[c][data[c]["t"].index(t["산 때"])]) or "정배열"
        base = (b15["o"][i1] / price - 1) * 100
        new, peak = base, price
        for j in range(i0, i1 - 1):
            cl = b15["c"][j]
            peak = max(peak, cl)
            g = (cl / price - 1) * 100
            pg = (peak / price - 1) * 100
            hit = False
            if kind == "추세":
                hit = (part in ("stop", "both") and g <= -5) or (part in ("take", "both") and g >= 13)
            else:
                hit = (part in ("stop", "both") and g <= -10) or (part in ("take", "both") and pg >= 8 and g <= 1)
            if hit:
                new = (b15["o"][j + 1] / price - 1) * 100
                break
        diff = (new - base) * t["칸"] / 10
        d.append(diff)
        changed += new != base
        w += 1
    if d:
        ch = [x for x in d if x != 0]
        print(f"  {side}: 매매 줄 {w} · 바뀐 줄 {changed} · 계좌 몫 합 {sum(d):+.1f}%p · 바뀐 줄 평균 {statistics.mean(ch) if ch else 0:+.2f} · 나아진 몫 {sum(x > 0 for x in ch) / max(1, len(ch)) * 100:.0f}%", flush=True)
print("끝", flush=True)
