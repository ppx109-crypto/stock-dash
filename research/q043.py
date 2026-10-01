"""15분봉 42회차(줄 4) — 운영 중인 1시간봉 규칙의 사기를 시장가(정시 시가) 대신 지정가(신호 봉 종가)로 넣으면.
매매마다 지정가 = 신호 봉(산 봉 바로 앞 1시간봉) 종가. 산 시각부터 N분(15 · 30 · 60) 안 15분봉 저가가 지정가 이하면 체결(시가가 이미 아래면 시가).
체결 비율 · 체결된 매매의 값 이득(%p) · 놓친 매매의 원래 손익 · 합친 계좌 몫(놓친 매매는 0으로). 두 반 · 씨앗 0."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
os.environ["Q_BARS"] = "1h"
exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
import m15lab as M2

M15 = _load(None, os.environ.get("M15_HOME"))     # q_rule이 M.load를 1시간 묶음으로 바꿔 두므로 원래 읽기를 씀
IDX = {c: {t: i for i, t in enumerate(b["t"])} for c, b in M15.items()}
res = M.simulate(data, lambda c, b: SIGS[c], exit_rule, size, rank=RANK, stale_of=stale90, seeds=1)
print(f"== 15분봉 42회차: 1시간봉 규칙 사기를 지정가로 ({len(data)}종목) ==", flush=True)
for side in ("앞", "뒤"):
    rows = [t for t in res[side]["목록"] if not str(t["판 때"]).startswith("끝") and t["code"] in IDX]
    for mins in (15, 30, 60):
        fill, gain, miss, total = 0, [], [], 0.0
        for t in rows:
            c, b = t["code"], data[t["code"]]
            k = b["t"].index(t["산 때"])
            if k == 0:
                continue
            lim = b["c"][k - 1]
            i0 = IDX[c].get(t["산 때"])
            if i0 is None:
                continue
            b15 = M15[c]
            got = None
            for j in range(i0, min(len(b15["t"]), i0 + mins // 15)):
                if b15["t"][j][:8] != t["산 때"][:8]:
                    break
                if b15["l"][j] <= lim:
                    got = min(b15["o"][j], lim)
                    break
            mkt = b15["o"][i0]
            if got is None:
                miss.append(t["손익"] * t["칸"] / 10)
            else:
                fill += 1
                g = (mkt / got - 1) * 100
                gain.append(g)
                total += (t["손익"] + g) * t["칸"] / 10
        n = fill + len(miss)
        base = sum(t["손익"] * t["칸"] / 10 for t in rows)
        print(f"  {side} {mins}분 안: 체결 {fill}/{n} ({fill / max(1, n) * 100:.0f}%) · 체결 값 이득 평균 {statistics.mean(gain) if gain else 0:+.2f}%p · "
              f"놓친 매매 계좌 몫 합 {sum(miss):+.1f} · 지정가 계좌 몫 합 {total:+.1f} vs 시장가 {base:+.1f}", flush=True)
print("끝", flush=True)
