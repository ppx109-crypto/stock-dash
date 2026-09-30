"""1시간봉 87회차(탐색 줄) — 자료 점검 빈틈 ④ 계속: **자리 바꾸기로 비킬 매매 고르기**를 한투 자료로(stale_key, 작을수록 먼저 비킴).
지금: 전 봉 종가 기준 손익이 나쁜 것부터. 견줌: 최근 프로그램 · 외국인+투신 매수가 몰린 것부터(85회차: 몰린 것은 덜 오름) ·
수급이 식은 것(5일 외국인+투신이 약한 것)부터 · 오래 든 것부터 · 손익 나쁨과 프로그램 몰림을 섞은 순서.
비킬 매매의 자료는 그 매매가 지금 있는 봉의 날 전 거래일까지(64회차 재료 feats와 같음) — 미래 참조 없음. 씨앗 16."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
src = open("research/h064.py", encoding="utf-8").read()
exec(src.split("# ---------- 1. 매매 모으기")[0].replace("== 1시간봉 64회차 (약한 장 진 매매 샅샅이 분해) ==", "== 1시간봉 87회차 (비킬 매매를 자료로 고르기) =="))
exec(src.split("# ---------- 2. 자료 읽기 ----------")[1].split("ROWS = []")[0].replace("CODES = sorted({c for c, _ in trades})", "CODES = sorted(data)"))
EX = make_exit()
CACHE = {}
def fday(c, k):
    day = data[c]["t"][k][:8]
    if (c, day) not in CACHE: CACHE[(c, day)] = feats(c, k)
    return CACHE[(c, day)]
def val(c, k, nm):
    v = fday(c, k).get(nm, np.nan); return 0.0 if v is None or v != v else float(v)
def gain(q): return data[q["code"]]["c"][q["now"]] / q["price"] - 1
KEYS = {"지금: 손익 나쁜 것부터": None,
        "프로그램 몰린 것부터": lambda q: -val(q["code"], q["now"], "프로그램 5일/거래량"),
        "외국인+투신 몰린 것부터": lambda q: -(val(q["code"], q["now"], "외국인 5일/거래량") + val(q["code"], q["now"], "투신 5일/거래량")),
        "수급 식은 것부터": lambda q: (val(q["code"], q["now"], "외국인 5일/거래량") + val(q["code"], q["now"], "투신 5일/거래량")),
        "오래 든 것부터": lambda q: -(q["now"] - q["i"]),
        "섞음: 손익 순위 + 프로그램 몰림 순위": "mix"}
def trim(sk):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90, None, sk)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
def mix(q):   # 손익(나쁠수록 작음)과 프로그램 몰림(몰릴수록 작음)을 절반씩
    return gain(q) - 0.05 * val(q["code"], q["now"], "프로그램 5일/거래량")
for tag, sk in KEYS.items():
    if sk == "mix": sk = mix
    res = H.simulate(data, e_align_or_noon, EX, size, rank=rank, stale_of=stale90, seeds=16, stale_key=sk)
    tr = trim(sk)
    print(f"  {tag:30s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
