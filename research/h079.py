"""1시간봉 79회차 — 사용자 "−15% 지키고 드문 경우만 크게 걸기" + "낙폭 최대 15, 그걸 빼면 몇?".
① 드문 경우만 크게: 신호 봉에서 1시간봉 A(또는 B) 정배열이 **막 된** 때(e_align, 한 해 약 6 ~ 8번)만 3 · 4칸. 나머지는 지금 크기. 씨앗 16 · 골 · 큰 매매 뺀 연.
② 낙폭 분해: 최고 규칙의 날마다 계좌 곡선(씨앗 16)에서 꼭대기 → 바닥 → 다시 꼭대기까지를 한 번의 낙폭으로 세어, 깊은 순서 1 · 2 · 3번째와 날짜 · 길이.
   씨앗 0은 날짜까지 보이고, 16 씨앗의 가운데 값도 봄."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
def episodes(curve):
    days = sorted(curve); v = np.array([curve[d] for d in days])
    out = []; peak_i = 0; trough_i = 0; inside = False
    for i in range(1, len(v)):
        if v[i] >= v[peak_i]:
            if inside:
                out.append((v[trough_i] / v[peak_i] - 1, days[peak_i], days[trough_i], days[i]))
                inside = False
            peak_i = i; trough_i = i
        else:
            inside = True
            if v[i] < v[trough_i]: trough_i = i
    if inside: out.append((v[trough_i] / v[peak_i] - 1, days[peak_i], days[trough_i], "아직"))
    return sorted(out)
print("== 1시간봉 79회차 (드문 경우만 크게 · 낙폭 분해) ==", flush=True)
print("  ② 낙폭 분해(최고 규칙)", flush=True)
for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
    tops = []
    for seed in range(16):
        r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
        ep = episodes(r["곡선"]); tops.append([round(e[0] * 100, 1) for e in ep[:5]] + [0.0] * (5 - len(ep[:5])))
        if seed == 0:
            print(f"    [{s}] 씨앗 0 · 계좌 곡선의 낙폭(꼭대기 대비 5% 넘은 것 {sum(e[0] <= -0.05 for e in ep)}번 · 10% 넘은 것 {sum(e[0] <= -0.10 for e in ep)}번)", flush=True)
            for n, e in enumerate(ep[:5], 1):
                print(f"      {n}번째 {e[0] * 100:6.1f}% · 꼭대기 {e[1]} → 바닥 {e[2]} → 회복 {e[3]}", flush=True)
    t = np.array(tops)
    print(f"    [{s}] 16 씨앗 가운데: 1번째 {np.median(t[:, 0]):.1f}% · 2번째 {np.median(t[:, 1]):.1f}% · 3번째 {np.median(t[:, 2]):.1f}% · 4번째 {np.median(t[:, 3]):.1f}% · 5번째 {np.median(t[:, 4]):.1f}%", flush=True)
    print(f"         1번째 범위 {t[:, 0].min():.1f} ~ {t[:, 0].max():.1f}% · 2번째 범위 {t[:, 1].min():.1f} ~ {t[:, 1].max():.1f}%", flush=True)

AL = {c: np.asarray(e_align(c, b), bool) for c, b in data.items()}
ALB = {}
for c, b in data.items():
    sb = H.states(c, b, "B")["정배열"] == 1
    ALB[c] = ctx_now(c, b) & sb & ~np.r_[False, sb[:-1]]
def rare(to, which="A"):
    M = AL if which == "A" else ALB
    def f(c, b, k):
        base = size(c, b, k)
        return max(base, to) if M[c][k] else base
    return f
def trim(sz):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, EX, sz, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
print("\n  ① 드문 경우만 크게(정배열이 막 된 봉 다음에 사는 매매)", flush=True)
for tag, sz in (("지금", size), ("A 막 정배열이면 3칸", rare(3)), ("A 막 정배열이면 4칸", rare(4)), ("B 막 정배열이면 3칸", rare(3, "B")), ("B 막 정배열이면 4칸", rare(4, "B"))):
    res = H.simulate(data, e_align_or_noon, EX, sz, rank=rank, stale_of=stale90, seeds=16)
    tr = trim(sz)
    print(f"  {tag:20s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
