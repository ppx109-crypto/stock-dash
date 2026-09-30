"""1시간봉 78회차 — 사용자 질문 "일봉 진입 조건 + 1시간봉 조건이 일치하면 강한 상승 신호인가? 둘이 일치하면 강한 배팅".
① 매매 나눠 보기(씨앗 16 모음): 사는 봉 바로 앞(신호 봉)의 1시간봉 상태 — A(5 · 20 · 60 · 120 · 180봉) 정배열 · B(5 · 10 · 20 · 60 · 120 · 240봉) 정배열 · 배열 점수 ·
   그리고 사는 까닭(정배열 된 봉 다음 vs 12시)으로 나눠 이긴 몫 · 평균 손익 · 큰 손해 몫.
② 강한 배팅: 두 조건이 맞으면(일봉 재료 + 신호 봉 1시간봉 정배열) 칸을 키움(2 → 3 · 4칸, 한 종목 최대 40% 지킴). 씨앗 16 · 큰 매매 뺀 연 · 골.
1시간봉 상태는 닫힌 봉(신호 봉)까지의 EMA만 씀 — 미래 참조 없음."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
def st(c, key): return H.states(c, data[c], key)
print("== 1시간봉 78회차 (일봉 + 1시간봉 일치 = 강한 신호?) ==", flush=True)
AL = {c: np.asarray(e_align(c, b), bool) for c, b in data.items()}
for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
    seen = {}
    for seed in range(16):
        r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
        agg = {}
        for t in r["목록"]:
            g = agg.setdefault((t["code"], t["산 때"]), [0, 0.0]); g[0] += t["칸"]; g[1] += t["손익"] * t["칸"]
        for k, (kan, w) in agg.items(): seen.setdefault(k, []).append(w / kan)
    rows = []
    for (c, t0), v in seen.items():
        i = data[c]["t"].index(t0); k = i - 1
        rows.append({"p": float(np.mean(v)), "A": st(c, "A")["정배열"][k] == 1, "B": st(c, "B")["정배열"][k] == 1,
                     "배열A": st(c, "A")["배열"][k], "cross": bool(AL[c][k]), "추세": door(ATT[c][i]) == "추세", "칸": size(c, data[c], k)})
    def show(tag, L):
        if not L: print(f"    {tag:34s} 0건", flush=True); return
        p = np.array([x["p"] for x in L])
        print(f"    {tag:34s} {len(L):4d}건 · 이긴 {np.mean(p > 0) * 100:3.0f}% · 평균 {p.mean():+6.2f}% · 가운데 {np.median(p):+6.2f}% · −5% 이하 {np.mean(p <= -5) * 100:3.0f}% · +20% 이상 {np.mean(p >= 20) * 100:3.0f}%", flush=True)
    print(f"  [{s}] 모은 매매 {len(rows)}", flush=True)
    show("전체", rows)
    show("사는 까닭: 1시간봉 정배열 된 봉 다음", [x for x in rows if x["cross"]])
    show("사는 까닭: 12시(정배열 없이)", [x for x in rows if not x["cross"]])
    show("신호 봉 1시간봉 A 정배열(일치)", [x for x in rows if x["A"]])
    show("신호 봉 1시간봉 A 정배열 아님", [x for x in rows if not x["A"]])
    show("신호 봉 1시간봉 B 정배열(일치)", [x for x in rows if x["B"]])
    show("신호 봉 1시간봉 B 정배열 아님", [x for x in rows if not x["B"]])
    for a in range(5): show(f"1시간봉 A 배열 점수 {a}", [x for x in rows if x["배열A"] == a])
    show("일봉 추세 문 + 1시간봉 A 정배열", [x for x in rows if x["추세"] and x["A"]])
    show("일봉 정배열 문 + 1시간봉 A 정배열", [x for x in rows if not x["추세"] and x["A"]])

def trim(ex, sz):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, ex, sz, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
def bet(key, to, need_full=True):
    def f(c, b, k):
        base = size(c, b, k)
        s_ = st(c, key)
        hit = (s_["정배열"][k] == 1) if need_full else (s_["배열"][k] >= 3)
        return max(base, to) if hit else base
    return f
print("\n  ② 두 조건이 맞으면 칸을 키움(지금: 추세 문 · 3일 연속 4칸, 나머지 2칸)", flush=True)
for tag, sz in (("지금", size), ("A 정배열이면 3칸", bet("A", 3)), ("A 정배열이면 4칸", bet("A", 4)),
                ("B 정배열이면 3칸", bet("B", 3)), ("B 정배열이면 4칸", bet("B", 4)), ("A 배열 3 이상이면 3칸", bet("A", 3, False))):
    res = H.simulate(data, e_align_or_noon, EX, sz, rank=rank, stale_of=stale90, seeds=16)
    tr = trim(EX, sz)
    print(f"  {tag:22s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
