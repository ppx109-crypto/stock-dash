"""1시간봉 119회차(G7 막힌/바뀐 매매) — 117회차 '닮음 0.6 넘으면 안 삼'이 기준(94회차)에 견줘 어떤 매매를 막고 무엇을 새로 샀나.
씨앗 0 매매 목록끼리 (종목 · 산 날)로 견주고, 계좌 몫(칸 × 손익 ÷ 10칸)을 더함. Q_SRC=yahoo · kis · Q_ALIGN=1이면 날짜 맞춘 닮음."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/h116.py", encoding="utf-8").read().split("\nVOL, RUN = {}, {}")[0])
import kinpatch as KP

align = os.environ.get("Q_ALIGN") == "1"
rk = RK(SG)


def book(res):
    out = {}
    for side in ("앞", "뒤"):
        for t in (res.get(side) or {}).get("목록", []):
            key = (side, t["code"], t["산 때"][:8])
            out[key] = round(out.get(key, 0) + t["칸"] * t["손익"] / 10, 2)
    return out


run = lambda: SIM(data, lambda c, b: SG[c], EXF, size, rank=rk, stale_of=stale90, seeds=1)
base = book(run())
KP.set_edge(0.6, align=align)
got = book(run())
print(f"== 1시간봉 119회차: 닮음 0.6{'(날짜 맞춤)' if align else ''} 막힌/바뀐 매매 ({src} · 씨앗 0) ==", flush=True)
for side in ("앞", "뒤"):
    gone = {k: v for k, v in base.items() if k[0] == side and k not in got}
    new = {k: v for k, v in got.items() if k[0] == side and k not in base}
    same = [k for k in base if k[0] == side and k in got]
    print(f"  {side}: 같은 매매 {len(same)} · 같은 매매의 몫 차이 {sum(got[k] - base[k] for k in same):+.1f} | "
          f"막힘 {len(gone)}건 몫 {sum(gone.values()):+.1f} | 새로 삼 {len(new)}건 몫 {sum(new.values()):+.1f}", flush=True)
    for tag, d in (("막힘", gone), ("새로", new)):
        top = sorted(d.items(), key=lambda kv: -abs(kv[1]))[:6]
        print(f"    {tag} 큰 것: " + " · ".join(f"{k[1]} {k[2]} {v:+.1f}" for k, v in top), flush=True)
        yrs = {}
        for k, v in d.items():
            yrs[k[2][:4]] = round(yrs.get(k[2][:4], 0) + v, 1)
        print(f"    {tag} 해마다: {yrs}", flush=True)
print("끝", flush=True)
