"""1시간봉 29회차(확인 줄) — 묵은 매매를 새 신호에 비키게(자리 바꾸기 · 회전 올리기).
가설: 칸이 꽉 찬 날 들어온 새 신호(재료가 막 켜진 종목)가, N봉 넘게 들고도 제자리인 매매보다 앞으로 더 오를 것.
새 매수가 칸이 모자라면 '묵음'(들고 N봉 이상 · 전 봉 종가 손익 < X%)을 그 봉 시가에 팔고(손익 나쁜 것부터) 새것을 삼.
판단은 모두 전 봉이 닫힌 뒤 값(hlab.simulate stale_of). 변형: 새 신호 모두가 밀어냄 / 센 새 신호(4칸)만 밀어냄.
점검: 비킨 매매 손익 · 그 자리에 산 매매 손익 · 비키지 않았으면 비킨 매매가 어떻게 끝났을지(견줌 목록과 대조) · 반기 · 문턱 고원."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

def stale(n, x):
    return lambda p: (p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x
weak_new = lambda c, b, k: size(c, b, k) < 4
print("== 1시간봉 29회차 (묵은 매매를 새 신호에 비키게) ==", flush=True)
base = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)
print(f"  {'지금':30s} " + H.line(base), flush=True)
keyb = {s: {(t["code"], t["산 때"]): t for t in base[s]["목록"] if not t["나눠"]} for s in ("앞", "뒤")}
for who in ("모든 새 신호", "센 새 신호만"):
    for n in (7, 14, 21, 35):
        for x in (0, 3):
            res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=stale(n, x),
                             yields=weak_new if who == "센 새 신호만" else None)
            chk = []
            for s in ("앞", "뒤"):
                L = res[s]["목록"]; moved = [t for t in L if t["비킴"]]
                was = [keyb[s][(t["code"], t["산 때"])]["손익"] for t in moved if (t["code"], t["산 때"]) in keyb[s]]
                chk.append(f"{s} 비킨 {len(moved)}건 평균 {np.mean([t['손익'] for t in moved]) if moved else 0:+.2f}%"
                           f"(안 비켰으면 {np.mean(was) if was else 0:+.2f}% · {len(was)}건 대조)")
            print(f"  {f'{who} · {n}봉 · <{x}%':30s} " + H.line(res), flush=True)
            print(f"      {' · '.join(chk)} · 반기 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
