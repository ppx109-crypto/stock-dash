"""1시간봉 63회차(첫 훑기) — 약한 장(앞)에서 진 매매 101건의 '사기 전에 알 수 있는' 공통점. 바탕: 1시간봉 최고 규칙 · 씨앗 0.
사는 봉의 일봉 재료(전 거래일 것)로 이긴 매매 · 진 매매를 나눠 봄. 뒤 반도 같이 보아 두 반에서 같은 방향인 것만 믿음."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
print("== 1시간봉 63회차 (진 매매의 공통점 첫 훑기) ==", flush=True)
x0 = next(x for c in ATT for x in ATT[c] if x)
keys = [k for k, v in x0.items() if isinstance(v, (int, float, bool)) and not isinstance(v, str)]
print("  재료:", keys, flush=True)
for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
    r = H._one_run(data, sigs, make_exit(), size, lo, hi, 10, 0, None, rank, H.COST, None, None, stale90)
    rows = []
    for t in r["목록"]:
        c = t["code"]; i = data[c]["t"].index(t["산 때"]); x = ATT[c][i]
        if not x: continue
        rows.append((t["손익"], door(x) or "정배열", x))
    print(f"  {s} 매매 {len(rows)}", flush=True)
    for kind in ("추세", "정배열"):
        R = [r_ for r_ in rows if r_[1] == kind]
        if not R: continue
        print(f"    {kind} 문: {len(R)}건 · 이긴 몫 {np.mean([p > 0 for p, _, _ in R]) * 100:.0f}% · 평균 {np.mean([p for p, _, _ in R]):+.2f}%", flush=True)
    for k in keys:
        v = np.array([float(x[k]) if x[k] is not None else np.nan for _, _, x in rows]); p = np.array([q for q, _, _ in rows])
        ok_ = ~np.isnan(v)
        if ok_.sum() < 20 or len(set(v[ok_])) < 2: continue
        med = np.median(v[ok_])
        lo_, hi_ = ok_ & (v <= med), ok_ & (v > med)
        if lo_.sum() < 10 or hi_.sum() < 10: continue
        print(f"    {k:8s} 가운데 {med:10.2f} · 아래 {lo_.sum():3d}건 이긴 {np.mean(p[lo_] > 0) * 100:3.0f}% 평균 {p[lo_].mean():+6.2f}% | 위 {hi_.sum():3d}건 이긴 {np.mean(p[hi_] > 0) * 100:3.0f}% 평균 {p[hi_].mean():+6.2f}%", flush=True)
print("끝", flush=True)
