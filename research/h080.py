"""1시간봉 80회차 — 낙폭 뜯어보기(사용자 "낙폭 시작 신호 · 되돌림인지 진입부터 하락인지").
최고 규칙 · 씨앗 16 · 두 반. 계좌 곡선에서 −10% 넘은 낙폭마다 꼭대기 날 → 바닥 날 사이의 계좌 변화를 매매(조각)별로 나눔:
  되돌림 = 꼭대기 전에 사서 꼭대기 날 이익 중이던 매매(이익을 돌려준 몫 · 산 값 아래로 더 빠진 몫을 따로)
  이미 손해 = 꼭대기 전에 샀고 꼭대기 날 이미 손해 중
  새 진입 = 꼭대기 뒤에 산 매매
계좌 값은 hlab._mark와 같음(1 + 실현 + 평가, 칸 무게 고정). 날 끝 값은 그날 마지막 봉 종가.
그리고 낙폭 첫 5거래일의 모습(계좌 몫 · 손절 수 · 시장 폭 · 코스피 5일)과, 같은 모습이 '큰 낙폭 없이 끝난' 때도 흔했는지(헛경보)."""
import sys, json, bisect
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
KOSPI = sorted(json.load(open("market-data/index_KOSPI.json", encoding="utf-8"))["rows"], key=lambda r: r["date"])
KD = [r["date"] for r in KOSPI]; KC = np.array([r["종가"] for r in KOSPI], float)
def k5(day):
    j = bisect.bisect_right(KD, day) - 1
    return (KC[j] / KC[j - 5] - 1) * 100 if j >= 5 else np.nan
DAYEND = {}
for c, b in data.items():
    d = {}
    for k, t in enumerate(b["t"]): d[t[:8]] = k
    DAYEND[c] = (sorted(d), d)
def close_on(c, day):
    days, d = DAYEND[c]; j = bisect.bisect_right(days, day) - 1
    return data[c]["c"][d[days[j]]] if j >= 0 else None
def breadth(day):
    vals = [x["시장폭"] for c in list(data)[:60] for x in [ATT[c][DAYEND[c][1][day]]] if day in DAYEND[c][1] and x and x["시장폭"] is not None] if True else []
    return np.median(vals) if vals else np.nan
def val(piece, day):
    c, i, k, kan, gain = piece
    bday, sday = data[c]["t"][i][:8], data[c]["t"][k][:8] if k is not None else "99999999"
    if day < bday: return 0.0
    if day >= sday: return gain / 100 * kan / 10
    return (close_on(c, day) / data[c]["o"][i] - 1) * kan / 10
def episodes(curve):
    days = sorted(curve); v = np.array([curve[d] for d in days]); out = []; pi = ti = 0; inside = False
    for i in range(1, len(v)):
        if v[i] >= v[pi]:
            if inside: out.append((v[ti] / v[pi] - 1, days[pi], days[ti], days[i]))
            inside = False; pi = ti = i
        else:
            inside = True
            if v[i] < v[ti]: ti = i
    if inside: out.append((v[ti] / v[pi] - 1, days[pi], days[ti], None))
    return out
print("== 1시간봉 80회차 (낙폭 뜯어보기) ==", flush=True)
for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
    agg = {"되돌림(이익 돌려줌)": [], "되돌림(산 값 아래로 더)": [], "이미 손해": [], "새 진입": []}
    early = []; allstarts = []
    for seed in range(16):
        r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
        curve = r["곡선"]; days = sorted(curve)
        pieces = []
        for t in r["목록"]:
            c = t["code"]; i = data[c]["t"].index(t["산 때"])
            k = None if str(t["판 때"]).startswith("끝") else data[c]["t"].index(t["판 때"])
            pieces.append((c, i, k, t["칸"], t["손익"], t["비킴"]))
        eps = episodes(curve)
        # 헛경보 셈: 꼭대기에서 −5%를 처음 넘은 날마다, 그 낙폭이 −10%까지 갔나
        for dd, pk, tr, rec in eps:
            if dd <= -0.05: allstarts.append(dd <= -0.10)
        for dd, pk, tr, rec in eps:
            if dd > -0.10: continue
            base = curve[pk]; parts = {k_: 0.0 for k_ in agg}
            for c, i, k, kan, gain, bump in pieces:
                p5 = (c, i, k, kan, gain)
                bday = data[c]["t"][i][:8]; sday = data[c]["t"][k][:8] if k is not None else "99999999"
                if sday <= pk or bday > tr: continue
                v0, v1 = val(p5, pk), val(p5, tr); ch = v1 - v0
                if bday > pk: parts["새 진입"] += ch
                elif v0 > 0:
                    give = max(ch, -v0); parts["되돌림(이익 돌려줌)"] += give; parts["되돌림(산 값 아래로 더)"] += ch - give
                else: parts["이미 손해"] += ch
            tot = curve[tr] - base
            for k_ in agg: agg[k_].append(parts[k_] / base * 100)
            # 첫 5거래일
            j = days.index(pk); d5 = days[min(j + 5, len(days) - 1)]
            stops = sum(1 for c, i, k, kan, gain, bump in pieces if k is not None and pk < data[c]["t"][k][:8] <= d5 and gain <= -4.5)
            early.append((round(dd * 100, 1), pk, tr, round((curve[d5] / base - 1) * 100, 1), stops, round(k5(d5), 1), round(tot / base * 100 - sum(parts.values()) / base * 100, 2)))
    print(f"\n  [{s}] −10% 넘은 낙폭 {len(early)}번(씨앗 16 합) · 낙폭 속 몫(꼭대기 계좌 대비 %p, 가운데 / 평균):", flush=True)
    for k_, v in agg.items():
        v = np.array(v)
        print(f"    {k_:18s} 가운데 {np.median(v):+6.1f} · 평균 {v.mean():+6.1f}", flush=True)
    print(f"  [{s}] 낙폭마다(깊이 · 꼭대기 · 바닥 · 첫 5일 계좌 · 첫 5일 손절 수 · 코스피 5일 · 셈 맞춤 차이) — 씨앗 0 ~ 2만:", flush=True)
    for e in early[:12]: print(f"    {e}", flush=True)
    e = np.array([x[3] for x in early]); st = np.array([x[4] for x in early]); kk = np.array([x[5] for x in early])
    print(f"  [{s}] 첫 5일: 계좌 가운데 {np.median(e):+.1f}% · 손절 가운데 {np.median(st):.0f}건 · 코스피 5일 가운데 {np.nanmedian(kk):+.1f}%", flush=True)
    print(f"  [{s}] 헛경보: 꼭대기에서 −5% 넘은 낙폭 {len(allstarts)}번 중 −10%까지 간 것 {sum(allstarts)}번({np.mean(allstarts) * 100:.0f}%)", flush=True)
print("끝", flush=True)
