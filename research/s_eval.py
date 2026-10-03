"""손절 줄 줄이기 연구(docs/RL-STOP.md) 실행기 — 설계(I_SX) 하나를 넣으면 한 줄로.

1) 1일봉 연구 엔진(i044 · 조용함 문턱은 그때까지 자료로만 = DNA_past) + 설계 → 장부
2) 장부 손익에서 실제 비용 0.2%p 더 뺌 · 엔진 비용 0.4%
3) 계좌 전체(i013 · 지금 모의투자와 같은 규칙 · 15:15 문턱 · 인버스 D11b · 급락 되돌림은 남은 몫) → 날마다 평가 · 되돌림 뺀 골
**2026은 잠금**(고르기 · 시험에 안 씀 · 마지막 회차에만 S_OPEN2026=1로 엶).
쓰는 법: python research/s_eval.py "ST3_10_10_4" [더 · 설계 …]   (빈 문자열 "" = 바탕)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

RES = os.path.dirname(os.path.abspath(__file__))
SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
ACC = dict(I_DIP="1", I_DOLLAR="2", I_GATE="weakidle20", I_L="20", I_TOP="2", I_CANDS="133690,138230,132030,148070", I_W="1",
           I_QINV="free", I_QPRI="inv", I_QTH="0.095", I_DIP_TH="-0.045", I_QEXIT="0.25", I_QSIGN="60", I_QEXIT_SIDE="take",
           I_QEXIT_LO="0.015", I_QEXIT_HI="0.025", I_COST="0.004")
OPEN = os.environ.get("S_OPEN2026") == "1"
SHOW_C1 = os.environ.get("S_SHOW_C1") == "1"     # 고르는 회차엔 뒤(2021 ~ 25)를 안 보임 · 시험 회차에만 1


def one(sx):
    tag = re.sub(r"[^A-Za-z0-9_]+", "-", sx) or "base"
    led = f"s_led_{tag}.json"
    env = {**os.environ, "I_VAR": "DNA_past", "I_SX": sx, "I_DUMP_LEDGER": SP + led}
    r1 = subprocess.run([sys.executable, os.path.join(RES, "i044.py")], env=env, capture_output=True, text=True, timeout=3600)
    line = next((x for x in r1.stdout.splitlines() if x.startswith("[")), "")
    m_front = re.search(r"앞 2017 ~ 2020 연 ([+-][\d.]+) 골 ([-\d.]+) 매매 (\d+)(?: 손절 (\d+) 무리 (\d+) 연속 (\d+))?", line)
    m_back = re.search(r"뒤 2021 ~ 연 [+-][\d.]+ 골 [-\d.]+ 매매 \d+(?: 손절 (\d+) 무리 (\d+) 연속 (\d+))?", line)
    if not m_front:
        return f"{sx or '바탕':28s} | 실패 {r1.stderr[-300:]}"
    L = json.load(open(SP + led))
    json.dump([[c, b, s, round(p - 0.2, 4), k] for c, b, s, p, k in L], open(SP + "c_" + led, "w"))
    env2 = {**os.environ, **ACC, "I_LEDGER": "c_" + led}
    r2 = subprocess.run([sys.executable, os.path.join(RES, "i013.py")], env=env2, capture_output=True, text=True, timeout=3600)
    acc = {}
    for x in r2.stdout.splitlines():
        m = re.match(r"\s+(B|C1 21~25|C2 2026)\s+날마다 평가 연\s+([+-][\d.]+) 골\s+([-\d.]+) · 되돌림 뺀 골\s+([-\d.]+)", x)
        if m:
            acc[m.group(1)] = (float(m.group(2)), float(m.group(3)), float(m.group(4)))
    b, c1 = acc.get("B", (0, 0, 0)), acc.get("C1 21~25", (0, 0, 0))
    f = m_front.groups()
    bk = m_back.groups() if m_back else ("?", "?", "?")
    s = (f"{sx or '바탕':28s} | 앞 1일봉 연 {f[0]} 골 {f[1]} 매매 {f[2]} 손절 {f[3]} 무리 {f[4]} 연속 {f[5]}"
         f" | 계좌 B 연 {b[0]:+.1f} 골 {b[1]:.1f} 되돌림뺀 {b[2]:.1f}")
    if SHOW_C1:
        s += (f" | 뒤(21~25) 손절 {bk[0]} 무리 {bk[1]} 연속 {bk[2]}"
              f" | C1 연 {c1[0]:+.1f} 골 {c1[1]:.1f} 되돌림뺀 {c1[2]:.1f}")
    if OPEN and "C2 2026" in acc:
        c2 = acc["C2 2026"]
        s += f" | 2026 연 {c2[0]:+.1f} 골 {c2[1]:.1f} 되돌림뺀 {c2[2]:.1f}"
    return s


if __name__ == "__main__":
    designs = sys.argv[1:] or [""]
    with ThreadPoolExecutor(int(os.environ.get("S_PAR", "3"))) as ex:
        for line in ex.map(one, designs):
            print(line, flush=True)
