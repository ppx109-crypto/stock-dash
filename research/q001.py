"""15분봉 0회차 — 1시간봉 최고 규칙(90 · 94회차)을 15분봉에 옮겨, 같은 자료(한투 15분봉)를 1시간으로 묶은 1시간봉 규칙과 견줌.
같은 종목 · 같은 기간(앞 2025-09-17 ~ 2026-03-31 · 뒤 2026-04-01 ~ 2026-09-29) · 씨앗 16.
15분봉: EMA 묶음 A(5 · 20 · 60 · 120 · 180 15분봉)와 A4(20 · 80 · 240 · 480 · 720 = 1시간봉 A와 같은 시간 길이) 둘 다.
실행: python3 research/q001.py   (각 판을 따로 띄워 돌림 — 같은 프로세스에서 섞이지 않게)
"""
import os
import subprocess
import sys

if os.environ.get("Q_CHILD"):
    sys.path.insert(0, "/home/user/stock-dash")
    exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
    res = M.simulate(data, lambda c, b: SIGS[c], exit_rule, size, rank=RANK, stale_of=stale90, seeds=16)
    per_hour = 1 if HOURLY else 4
    out = []
    for name, r in res.items():
        if not r:
            out.append(f"{name} -")
            continue
        w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
        years = max(len(r["곡선"]) / 245, 0.25)
        out.append(f"{name} 매매 {r['매매']} 연 {r['연']}(폭 {r['폭']}) 골 {r['골']} 회전 {r['회전']}배 승률 {r['승률']} "
                   f"보유 {round(r['보유봉'] / per_hour, 1)}시간 행운뺌 {r['행운뺌']} 큰3건뺌 {round(sum(w[3:]) / years, 1)} 가동 {r['가동']}")
    print(f"  {os.environ['Q_TAG']:34s} " + " | ".join(out), flush=True)
    sys.exit(0)

print("== 15분봉 0회차: 1시간봉 최고 규칙 옮김 vs 같은 자료의 1시간봉 ==", flush=True)
for tag, env in (("1시간봉(15분봉을 묶음) · 최고 규칙", {"Q_BARS": "1h"}),
                 ("15분봉 · EMA A(15분봉 5~180) · 봉 수 ×4", {"Q_BARS": "15m", "Q_SPAN": "A"}),
                 ("15분봉 · EMA A4(1시간봉과 같은 길이) · ×4", {"Q_BARS": "15m", "Q_SPAN": "A4"})):
    r = subprocess.run([sys.executable, __file__], env={**os.environ, **env, "Q_CHILD": "1", "Q_TAG": tag},
                       capture_output=True, text=True)
    print(r.stdout.strip() or ("  " + tag + " 실패 · " + r.stderr.strip()[-600:]), flush=True)
print("끝", flush=True)
