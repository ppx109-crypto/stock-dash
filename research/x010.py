"""견줌 — 15분봉 최종 후보(22회차 · q027 SGF)와 같은 자료(한투 15분봉 161종목을 1시간으로 묶음)의 1시간봉 최고 규칙(q_rule Q_BARS=1h)의
1년 매매 목록이 얼마나 같은가(사용자 2026-10-02 "15m 1년 백테스트 거래 목록이 1H 거래 목록과 100% 동일해?").
씨앗 1(같은 흔들기) · 두 반. 같은 매매 = 같은 종목 · 같은 산 날."""
import json
import os
import subprocess
import sys

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
if os.environ.get("X_CHILD"):
    sys.path.insert(0, "/home/user/stock-dash")
    sys.path.insert(0, "/home/user/stock-dash/research")
    if os.environ["X_CHILD"] == "15m":
        exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
        res = M.simulate(data, lambda c, b: SGF[c], exit_rule, size, rank=RKF, stale_of=stale90, seeds=1)
    else:
        os.environ["Q_BARS"] = "1h"
        exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
        res = M.simulate(data, lambda c, b: SIGS[c], exit_rule, size, rank=RANK, stale_of=stale90, seeds=1)
    out = {s: [{k: t.get(k) for k in ("code", "산 때", "판 때", "손익", "칸", "까닭", "kind", "종류")} for t in r["목록"]]
           for s, r in res.items() if r}
    json.dump(out, open(SP + f"x010_{os.environ['X_CHILD']}.json", "w"), ensure_ascii=False)
    sys.exit(0)

for k in ("15m", "1h"):
    subprocess.run([sys.executable, __file__], env=dict(os.environ, X_CHILD=k), check=True)
A = json.load(open(SP + "x010_15m.json"))
B = json.load(open(SP + "x010_1h.json"))
print("== 15분봉 최종 후보 vs 1시간봉 최고 규칙 · 같은 한투 자료 1년 · 씨앗 1 ==")
for side in A:
    a, b = A[side], B.get(side, [])
    ka = {(t["code"], str(t["산 때"])[:8]): t for t in a}
    kb = {(t["code"], str(t["산 때"])[:8]): t for t in b}
    both = set(ka) & set(kb)
    only_a, only_b = set(ka) - set(kb), set(kb) - set(ka)
    s = lambda rows: round(sum((t["손익"] or 0) * (t["칸"] or 0) / 10 for t in rows), 1)
    near = sum(1 for k in only_a if any(c == k[0] and abs(int(d) - int(k[1])) <= 3 for c, d in kb))
    print(f"[{side}] 15분봉 매매 {len(a)} · 1시간봉 매매 {len(b)}")
    print(f"   같은 종목 · 같은 날 산 것 {len(both)}  (15분봉의 {len(both) / max(len(a), 1) * 100:.0f}% · 1시간봉의 {len(both) / max(len(b), 1) * 100:.0f}%)")
    print(f"   15분봉에만 {len(only_a)}(그 가운데 1시간봉이 같은 종목을 3일 안에 산 것 {near}) · 1시간봉에만 {len(only_b)}")
    print(f"   손익 합(계좌 %): 같은 것 15분봉 {s([ka[k] for k in both])} / 1시간봉 {s([kb[k] for k in both])} · "
          f"15분봉에만 {s([ka[k] for k in only_a])} · 1시간봉에만 {s([kb[k] for k in only_b])} · 전체 15분봉 {s(a)} / 1시간봉 {s(b)}")
    same_t = sum(1 for k in both if str(ka[k]['산 때'])[8:10] == str(kb[k]['산 때'])[8:10])
    print(f"   같은 날 산 것 가운데 같은 시(時)에 산 것 {same_t}/{len(both)}")
