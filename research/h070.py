"""1시간봉 70회차 — 정배열 문으로 산 매매를 +X%에 처음 닿으면 절반 먼저 팔기(나머지는 지금처럼 정배열이 깨질 때 · −10% · 본전 지키기).
까닭: 64회차에서 약한 장 이익이 거의 모두 '정배열 깨짐'으로 판 몇 건의 큰 매매 — 절반을 먼저 챙기면 큰 매매에 덜 기대고(큰3건 뺌 ↑) 돈이 빨리 돌까(회전 ↑)?
X = 8 · 10 · 13 · 15 · 20 · 30(고원). 판단은 봉 종가 → 다음 봉 시가. 바탕: 1시간봉 최고 규칙(자리 바꾸기 폭<90). 씨앗 16."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
BASE = make_exit()
def half_at(X):
    def f(c, b, p, k):
        r = BASE(c, b, p, k)
        if r: return r
        if (door(ATT[c][p["i"]]) or "정배열") == "정배열" and p["칸"] == p["처음칸"] and p["처음칸"] >= 2:
            if (b["c"][k] / p["price"] - 1) * 100 >= X: return p["처음칸"] // 2
        return 0
    return f
def trim(ex):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, ex, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
print("== 1시간봉 70회차 (정배열 매매 절반 먼저 팔기) ==", flush=True)
base0 = {}
for tag, ex in [("지금", BASE)] + [(f"정배열 +{X}%에 절반", half_at(X)) for X in (8, 10, 13, 15, 20, 30)]:
    res = H.simulate(data, e_align_or_noon, ex, size, rank=rank, stale_of=stale90, seeds=16)
    tr = trim(ex)
    msg = []
    for s in ("앞", "뒤"):
        L = res[s]["목록"]
        if tag == "지금": base0[s] = {(t["code"], t["산 때"]): t for t in L if not t["나눠"]}
        parts = [t for t in L if t["나눠"] and (door(ATT[t["code"]][data[t["code"]]["t"].index(t["산 때"])]) or "정배열") == "정배열"]
        keys = {(t["code"], t["산 때"]) for t in parts}
        rest = [t for t in L if (t["code"], t["산 때"]) in keys and not t["나눠"]]
        was = [base0[s][k]["손익"] for k in keys if k in base0.get(s, {})]
        msg.append(f"{s} 절반 판 매매 {len(keys)}건 · 먼저 판 절반 평균 {np.mean([t['손익'] for t in parts]) if parts else 0:+.1f}% · 나머지 평균 {np.mean([t['손익'] for t in rest]) if rest else 0:+.1f}% · (지금 규칙 같은 매매 {len(was)}건 평균 {np.mean(was) if was else 0:+.1f}%)")
    print(f"  {tag:18s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']} | " + " · ".join(msg), flush=True)
print("끝", flush=True)
