"""1시간봉 27회차(탐색 줄) — 쉬는 돈에만 짧은 판 굴리기(양보 칸).
긴 판(지금 규칙)은 가동 62~67%: 돈의 3분의 1이 늘 놂. 23회차(두 계좌 따로)는 자금을 떼어 줘서 긴 판 몫이 줄었음.
이번엔 **한 계좌**에서 긴 판이 먼저, 짧은 판은 빈 칸에만 들어가고 긴 판 신호가 오면 그 봉 시가에 짧은 판(손익 나쁜 것부터)을 팔아 자리를 비킴(hlab.simulate yields).
짧은 판 재료(긴 판이 안 사는 것만): ① A그룹 꼴(문)인데 가르침 없음 ② 가르침 + 일봉 정배열인데 간격 · 시장 폭이 문 밖 ③ 둘 다.
짧은 판 파는 법: B식(반 +8% 지정가 · 반 1시간봉 20봉선 따라가기 · 최대 70봉 · −5% 손절) 또는 긴 판 파는 법.
점검: 짧은 판 매매만의 손익 · 양보로 판 매매 수 · 긴 판 매매 손익이 그대로인지 · 반기."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import rna
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

_E20 = {}
def e20(c, b):
    if c not in _E20: _E20[c] = rna.ema(b["c"], 20)
    return _E20[c]
LONG = {}
def long_sig(c, b):
    if c not in LONG: LONG[c] = e_align_or_noon(c, b)
    return LONG[c]
def over_ctx(kind):
    def f(x):
        if not x: return False
        if ok(x): return False
        a = door(x) is not None and not x["가르침"]
        bb = bool(x["가르침"] and x["정배열"] and door(x) is None)
        return {"문·수급없음": a, "가르침·문밖정배열": bb, "둘다": a or bb}[kind]
    return f
SHORT = {}
def short_sig(kind):
    f = over_ctx(kind)
    def e(c, b):
        key = (kind, c)
        if key not in SHORT:
            a = ATT[c]
            okc = np.array([f(x) for x in a]) & IN[c]
            s = H.states(c, b, "A")["정배열"] == 1
            edge = s & ~np.r_[False, s[:-1]]
            days = [t[:8] for t in b["t"]]; seen = set(); m = np.zeros(len(a), bool)
            for k in range(len(m)):
                if days[k] in seen: continue
                if okc[k] and (edge[k] or b["t"][k][8:] == "11"):
                    m[k] = True; seen.add(days[k])
            SHORT[key] = m
        return SHORT[key]
    return e
def combo(kind):
    se = short_sig(kind)
    return lambda c, b: long_sig(c, b) | se(c, b)
is_short = lambda c, b, k: not long_sig(c, b)[k]
def sz(n):
    return lambda c, b, k: n if is_short(c, b, k) else size(c, b, k)
def exit_mix(short_exit):
    def f(c, b, p, k):
        if not p.get("양보"): return exit_daily(c, b, p, k)
        if short_exit == "긴 판식": return exit_daily(c, b, p, k)
        if p["칸"] < p["처음칸"]:
            return "all" if (b["c"][k] < e20(c, b)[k] or k - p["i"] >= 70) else 0
        return "all" if k - p["i"] >= 35 else 0
    return f
def take_of(short_exit):
    if short_exit == "긴 판식": return None
    return lambda p: (p["price"] * 1.08, p["처음칸"] // 2) if p.get("양보") and p["칸"] == p["처음칸"] else (None, 0)
def stop_of(short_exit):
    if short_exit == "긴 판식": return None
    return lambda p: p["price"] * 0.95 if p.get("양보") else None

def split(res):
    out = []
    for side in ("앞", "뒤"):
        r = res[side]
        if not r: out.append(f"{side} -"); continue
        L = r["목록"]; sh = [t for t in L if t["양보"]]; lo = [t for t in L if not t["양보"]]
        f = lambda T: f"{len(T)}건 평균 {np.mean([t['손익'] for t in T]):+.2f}% 몫 {sum(t['손익'] * t['칸'] for t in T) / 10 / (1.5 if side == '앞' else 1.5):+.1f}" if T else "0건"
        cut = sum(1 for t in sh if t["봉"] < 35 and t["판 때"][:1] != "끝")
        out.append(f"{side}: 긴 판 {f(lo)} · 짧은 판 {f(sh)}(35봉 안에 판 것 {cut})")
    return " | ".join(out)

print("== 1시간봉 27회차 (쉬는 돈에만 짧은 판 · 양보 칸) ==", flush=True)
base = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)
print(f"  {'견줌: 긴 판만':34s} " + H.line(base), flush=True)
print(f"      {split(base)}", flush=True)
for kind in ("문·수급없음", "가르침·문밖정배열", "둘다"):
    for n in (2, 4):
        for ex in ("B식", "긴 판식"):
            res = H.simulate(data, combo(kind), exit_mix(ex), sz(n), rank=lambda c, b, k: ((1,) if is_short(c, b, k) else (0,)) + rank(c, b, k),
                             take_of=take_of(ex), stop_of=stop_of(ex), yields=is_short)
            print(f"  {f'{kind} · {n}칸 · {ex}':34s} " + H.line(res), flush=True)
            print(f"      {split(res)}", flush=True)
            print(f"      반기(씨앗 0): 앞 {res['앞']['반기']} · 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
