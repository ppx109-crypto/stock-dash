"""15분봉 39회차 — 운영 중인 1시간봉 규칙의 '주문 넣는 때'(15분봉을 현미경으로).
1시간봉 최고 규칙(같은 15분봉 자료를 1시간으로 묶음 · 씨앗 0)의 매매마다, 산 값 · 판 값을 그 시각 15분봉에서 다시 읽음:
- 사기: 정시(HH:00 시가 = 지금) vs HH:15 시가 vs HH:30 시가
- 팔기: 정시 vs HH:15 vs HH:30 — 특히 09:00(밤사이 틈 뒤 장 시작) 팔기는 따로
매매 하나당 손익 차이(%p, 비용 같음)의 평균 · 가운데 · 나은 몫을 두 반으로. 161종목."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
os.environ["Q_BARS"] = "1h"
exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
import statistics
import m15lab as M2

M15 = _load(None, os.environ.get("M15_HOME"))     # q_rule이 M.load를 1시간 묶음으로 바꿔 두므로 원래 읽기를 씀
IDX = {c: {t: i for i, t in enumerate(b["t"])} for c, b in M15.items()}


def px(c, stamp, plus):
    """1시간봉 시각(YYYYMMDDHH00)의 plus분 뒤 15분봉 시가. 없으면 None."""
    hh, mm = int(stamp[8:10]), plus
    key = f"{stamp[:8]}{hh:02d}{mm:02d}"
    i = IDX.get(c, {}).get(key)
    return M15[c]["o"][i] if i is not None else None


res = M.simulate(data, lambda c, b: SIGS[c], exit_rule, size, rank=RANK, stale_of=stale90, seeds=1)
print(f"== 15분봉 39회차: 1시간봉 규칙 주문 시각 ({len(data)}종목) ==", flush=True)
for side in ("앞", "뒤"):
    L = [t for t in res[side]["목록"] if not str(t["판 때"]).startswith("끝")]
    print(f"  {side} 매매 {len(L)}건")
    for what, key in (("사기", "산 때"), ("팔기", "판 때")):
        for plus in (15, 30):
            d, d9 = [], []
            for t in L:
                a, z = px(t["code"], t[key], 0), px(t["code"], t[key], plus)
                if not a or not z:
                    continue
                diff = (a / z - 1) * 100 if what == "사기" else (z / a - 1) * 100     # +면 미뤄서 이득
                d.append(diff)
                if t[key][8:10] == "09":
                    d9.append(diff)
            if d:
                line = f"    {what} {plus}분 미루면: 평균 {statistics.mean(d):+.3f}%p · 가운데 {statistics.median(d):+.3f} · 나은 몫 {sum(x > 0 for x in d) / len(d) * 100:.0f}% ({len(d)})"
                if d9:
                    line += f" | 09시만 평균 {statistics.mean(d9):+.3f} · 나은 몫 {sum(x > 0 for x in d9) / len(d9) * 100:.0f}% ({len(d9)})"
                print(line, flush=True)
print("끝", flush=True)
