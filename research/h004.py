"""1시간봉 4회차 — 파는 법 겨루기(사는 때는 3회차에서 가장 나은 '1시간봉 A 정배열 된 봉 다음, 없으면 12시 시가').
사용자 목표 ② 최대 이익 근처에서 팔기 ③ 최소 손실에서 손절 — 1시간봉으로 일봉보다 빨리 알아챌 수 있나.
- 기준: 일봉 규칙 파는 법(3회차와 같음)
- 장중 손절: 추세 −5% · 정배열 −10%를 봉 저가로(닿으면 그 값, 시가가 이미 아래면 시가)
- 정배열: 1시간봉 A 배열이 2 이하로 무너지면(짧은 선들이 꺾임, 7봉 넘게 든 뒤) 팜 / 1시간봉 종가가 60봉 EMA 아래로 두 봉 연속이면 팜
- 추세: +5% 반익 뒤 나머지를 +13% 대신 1시간봉 20봉 EMA 아래로 닫히면 팜(꼭대기 따라가기)
바뀐 매매 점검: 기준과 견주어 어느 쪽 매매가 벌고 잃었는지 · 반기별."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])   # 3회차 준비(자료 · 재료 · 사는 때 · 칸 · 순서 · 기준 파는 법)

def st(c, b): return H.states(c, b, "A")
def ema_line(c, b, span):
    import rna
    key = (c, "ema", span)
    if key not in H._ST:
        H._ST[key] = rna.ema(b["c"], span)
    return H._ST[key]

def make_stop():
    def f(p):
        kind = p.get("kind")
        return p["price"] * (0.95 if kind == "추세" else 0.90)
    return f

def with_kind(exit_rule):
    """pos에 갈래(추세 · 정배열)를 적어 두고 파는 법을 부름(장중 손절 값에 씀)."""
    def go(c, b, p, k):
        if "kind" not in p:
            p["kind"] = door(ATT[c][p["i"]]) or "정배열"
        return exit_rule(c, b, p, k)
    return go

def exit_hourly_break(c, b, p, k):
    r = exit_daily(c, b, p, k)
    if r: return r
    kind = door(ATT[c][p["i"]]) or "정배열"
    if kind == "정배열" and k - p["i"] >= 7 and st(c, b)["배열"][k] <= 2:
        return "all"
    return 0

def exit_below60(c, b, p, k):
    r = exit_daily(c, b, p, k)
    if r: return r
    kind = door(ATT[c][p["i"]]) or "정배열"
    e60 = ema_line(c, b, 60)
    if kind == "정배열" and k - p["i"] >= 2 and b["c"][k] < e60[k] and b["c"][k - 1] < e60[k - 1]:
        return "all"
    return 0

def exit_trail20(c, b, p, k):
    kind = door(ATT[c][p["i"]]) or "정배열"
    if kind != "추세":
        return exit_daily(c, b, p, k)
    now = (b["c"][k] / p["price"] - 1) * 100
    if now <= -5 or k - p["i"] >= 60: return "all"
    before = b["c"][p["i"]:k].max() if k > p["i"] else -1
    if now >= 5 and (before / p["price"] - 1) * 100 < 5 and p["칸"] == p["처음칸"]:
        return max(1, p["처음칸"] // 2)
    if p["칸"] < p["처음칸"] and b["c"][k] < ema_line(c, b, 20)[k]:
        return "all"
    return 0

E = e_align_or_noon
rows = [("기준: 일봉 규칙 파는 법", exit_daily, None),
        ("장중 손절(봉 저가)", with_kind(exit_daily), make_stop()),
        ("정배열: 1시간봉 배열 무너지면", exit_hourly_break, None),
        ("정배열: 60봉선 아래 두 봉", exit_below60, None),
        ("추세: 반익 뒤 20봉선 따라가기", exit_trail20, None)]
print("== 1시간봉 4회차 (파는 법 · 사는 때 = 정배열 된 봉 다음, 없으면 12시) ==", flush=True)
base = None
for tag, ex, stop in rows:
    res = H.simulate(data, E, ex, size, rank=rank, stop_of=stop)
    print(f"  {tag:26s} " + H.line(res), flush=True)
    print(f"      반기(씨앗 0): 앞 {res['앞']['반기'] if res['앞'] else '-'} · 뒤 {res['뒤']['반기'] if res['뒤'] else '-'}", flush=True)
    if base is None:
        base = res
    else:
        for side in ("앞", "뒤"):
            if not res[side] or not base[side]: continue
            a = {(t["code"], t["산 때"]): t for t in base[side]["목록"] if not t["나눠"]}
            z = {(t["code"], t["산 때"]): t for t in res[side]["목록"] if not t["나눠"]}
            both = [k for k in a if k in z and a[k]["판 때"] != z[k]["판 때"]]
            d = [z[k]["손익"] - a[k]["손익"] for k in both]
            if d:
                print(f"      바뀐 매매 {side}: {len(d)}건 · 새 방법이 나은 몫 {np.mean(np.array(d) > 0) * 100:.0f}% · 한 건 차이 평균 {np.mean(d):+.2f}%p", flush=True)
print("끝", flush=True)
