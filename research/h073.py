"""1시간봉 73회차(탐색 줄 첫 단계) — 전날 마지막 봉에서 판단해 다음 날 09시 시가에 판 매매의 '밤사이 틈'(09시 시가 ÷ 전날 마지막 봉 종가 − 1).
틈이 평균적으로 손해면, 마감 전(한투 15시 봉 시가)에 파는 방법을 시험할 값어치가 있음. 파는 까닭별 · 두 반. 바탕: 1시간봉 최고 규칙 · 씨앗 16 모음."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
print("== 1시간봉 73회차 (다음 날 아침에 판 매매의 밤사이 틈) ==", flush=True)
for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
    seen = {}
    for seed in range(16):
        r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
        for t in r["목록"]:
            if str(t["판 때"]).startswith("끝") or t["판 때"][8:] != "09": continue
            c = t["code"]; k = data[c]["t"].index(t["판 때"]); i = data[c]["t"].index(t["산 때"])
            if k == 0 or data[c]["t"][k - 1][:8] == t["판 때"][:8]: continue
            gap = (data[c]["o"][k] / data[c]["c"][k - 1] - 1) * 100
            kind = door(ATT[c][i]) or "정배열"
            now = (data[c]["c"][k - 1] / data[c]["o"][i] - 1) * 100
            why = ("비킴" if t["비킴"] else "나눠 판 절반" if t["나눠"] else
                   ("익절" if now >= 12 else "손절" if now <= -4.5 else "기간") if kind == "추세" else
                   ("손절" if now <= -9.5 else "정배열 깨짐/본전"))
            seen[(c, t["산 때"], t["판 때"])] = (why, gap, t["칸"])
    by = {}
    for why, gap, kan in seen.values(): by.setdefault(why, []).append((gap, kan))
    allg = np.array([g for g, _ in sum(by.values(), [])])
    print(f"  [{s}] 아침에 판 매매 {len(seen)}건 · 틈 평균 {allg.mean():+.2f}% · 가운데 {np.median(allg):+.2f}% · 음수 몫 {np.mean(allg < 0) * 100:.0f}%", flush=True)
    for why, L in sorted(by.items(), key=lambda z: -len(z[1])):
        g = np.array([x for x, _ in L]); w = np.array([k for _, k in L])
        print(f"    {why:12s} {len(L):4d}건 · 틈 평균 {g.mean():+.2f}% · 가운데 {np.median(g):+.2f}% · 음수 몫 {np.mean(g < 0) * 100:.0f}% · 칸 무게 평균 {np.average(g, weights=w):+.2f}%", flush=True)
# 견줌: 모든 봉의 밤사이 틈(같은 종목들, 재료 켜진 날) — 파는 날이 특별히 나쁜가
for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
    g = []
    for c, b in data.items():
        for k in range(1, len(b["t"])):
            if b["t"][k][8:] == "09" and b["t"][k - 1][:8] != b["t"][k][:8] and lo <= b["t"][k] < hi and ok(ATT[c][k - 1]):
                g.append((b["o"][k] / b["c"][k - 1] - 1) * 100)
    g = np.array(g)
    print(f"  [{s}] 견줌: 재료 켜진 종목의 모든 밤사이 틈 {len(g)}번 · 평균 {g.mean():+.2f}% · 가운데 {np.median(g):+.2f}%", flush=True)
print("끝", flush=True)
