"""15분봇 규칙(15분봉 22회차 = 운영 m15_live)을 1시간봉으로 옮겨 긴 자료에 돌림(사용자 2026-10-04 "야후 자료 3년에 대입하여 15분봇 가동 · ①로 진행").
※ 진짜 15분봇이 아님 — 15분마다 보던 것을 1시간마다 봄. 3년 동안 어땠을지 짐작하는 참고값.
옮기는 법(q_rule의 Q_BARS=1h 스위치 그대로): 봉 수 숫자 × 1/4(추세 문 240 → 60봉 · 자리 바꾸기 28 → 7봉) · 정오 사기 11:45 봉 → 11시 봉 ·
'10:45 봉이 닫히면 11:00 시가'(22회차) → '10시 봉이 닫히면 11:00 시가' · EMA 묶음 A(5 · 20 · 60 · 120 · 180봉) · +2% 거르기 · 장중 시장 −1% 쉼 · 크기 · 순서 · 팔기 그대로.
미래 참조: 신호는 봉이 닫힌 뒤 다음 봉 시가 · 일봉 재료는 전 거래일 · 종목 모음은 전 거래일 시총 100위 · 장중 시장 흐름은 그 봉에 100위 안 종목만.
M15Y_SRC=kis(한투 15분봉을 1시간으로 · 2025-09 ~ 2026-08 · 진짜 15분봇과 맞대 보기) | yahoo(야후 60분봉 · 2023-10 ~ 2026-08).
출력: 씨앗 16 가운데(H.line) · 씨앗 1 장부 → scratchpad m15y_{SRC}.json · 해마다 칸 반영 합."""
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
os.chdir("/home/user/stock-dash")
SRC = os.environ.get("M15Y_SRC", "kis")
os.environ["Q_BARS"] = "1h"
import numpy as np
import hlab as H
import m15lab as M

if SRC == "yahoo":
    def _yahoo(codes=None, home=None):
        got = H.load(codes)                 # 야후 60분봉(15시 봉 없음 · 시험지 2026-09-30 뒤 잠금)
        out = {}
        for c, b in got.items():
            keep = [i for i, t in enumerate(b["t"]) if "2023010100" <= t < "2026090100"]
            if len(keep) < 500:
                continue
            out[c] = {"t": [b["t"][i] + "00" for i in keep], **{k: b[k][keep] for k in ("o", "h", "l", "c", "v")}}
        return out
    M.load = _yahoo
    M.PERIODS = (("2023-10 ~ 2025-08", ("202310010000", "202509170000")), ("2025-09 ~ 2026-08", ("202509170000", "202609010000")))
    _setup = M.setup

    def _setup3(codes=None, home=None, top=100):
        data = M.load(codes, home)
        names = [c for c in data if not c.startswith("K")]
        ranks, trend = H.cached_tables("20220101")
        ctx = H.daily_context(names, ranks, trend)
        att = {c: H.attach(data[c], ctx[c], sorted(ctx[c])) for c in names if c in ctx}
        uni = H.Universe({d: v for d, v in ranks.items() if d >= "20230101"}, top=top)     # 3년이라 2023년부터
        data = {c: data[c] for c in att}
        inside = {c: np.array([uni.ok(c, t) for t in data[c]["t"]]) for c in data}
        return {"data": data, "ATT": att, "IN": inside, "ranks": ranks, "trend": trend, "CTX": ctx}
    M.setup = _setup3
else:
    M.PERIODS = (("2025-09 ~ 2026-03", ("202509170000", "202604010000")), ("2026-04 ~ 2026-08", ("202604010000", "202609010000")))

exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
# 22회차 '10:45 봉 뒤 11:00 시가' → 1시간봉 '10시 봉 뒤 11:00 시가'(entry3이 HH == "1045"를 봄)
HH = {c: np.where(HH[c] == "1000", "1045", HH[c]) for c in HH}
FIN = entry3(al_mkt=-0.01)
SGF = {c: np.asarray(FIN(c, b), bool) for c, b in data.items()}
RKF = rank_plus(tiers(SGF))
res16 = M.simulate(data, lambda c, b: SGF[c], exit_rule, size, rank=RKF, stale_of=stale90, seeds=16, cost=H.COST)
print(f"== 15분봇 규칙을 1시간봉으로 · {SRC} · {len(data)}종목 ==", flush=True)
print("  씨앗 16 가운데: " + H.line(res16), flush=True)
res1 = M.simulate(data, lambda c, b: SGF[c], exit_rule, size, rank=RKF, stale_of=stale90, seeds=1, cost=H.COST)
T = [(t["code"], t["산 때"][:8], t["판 때"].lstrip("끝")[:8], t["손익"], t["칸"]) for s in res1 if res1[s] for t in res1[s]["목록"]]
json.dump(T, open(f"/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/m15y_{SRC}.json", "w"))
by = {}
for c, b, e, p, k in T:
    by.setdefault(e[:4], []).append(p * k / 10)
w = sorted((p * k / 10 for c, b, e, p, k in T), reverse=True)
print(f"  씨앗 1 장부: 매매 {len(T)} · 칸 반영 합 {sum(w):+.1f}%p · 큰 두 건 뺌 {sum(w[2:]):+.1f} · 해마다(판 해): "
      + " · ".join(f"{y} {sum(v):+.1f}%p({len(v)}건)" for y, v in sorted(by.items())), flush=True)
