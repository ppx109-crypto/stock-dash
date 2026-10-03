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
SHOW_C1 = os.environ.get("S_SHOW_C1") == "1"     # (35회차까지) 고르는 회차엔 뒤(2021 ~ 25)를 안 보임
SPLIT2 = os.environ.get("S_SPLIT", "2") == "2"   # 36회차부터: 고르기 2017 ~ 2022 · 시험 2023 ~ 2025(S_SHOW_TEST=1) · 2026 잠금
SHOW_TEST = os.environ.get("S_SHOW_TEST") == "1"


_D = None


def oned(L):
    """1일봉만 떼어 낸 계좌(날마다 평가 · 실제 비용 장부): 앞(2017 ~ 20) [뒤(2021 ~ 25)] 연 · 되돌림 뺀 골(13 ~ 20회차에 주 잣대로 더함)."""
    global _D
    import numpy as np
    sys.path.insert(0, RES)
    import a_mtm
    import itools as I
    if _D is None:
        _D = list(I.DAYS)
    z = np.zeros(len(_D))
    rc, rm = a_mtm.account(_D, L, z, mode="cost"), a_mtm.account(_D, L, z, mode="mark")
    out = []
    for lo, hi in (("20170101", "20210101"),) + ((("20210101", "20260101"),) if SHOW_C1 else ()):
        m = np.array([lo <= d < hi for d in _D])
        q, qm = np.cumprod(1 + rc[m]), np.cumprod(1 + rm[m])
        out.append(((qm[-1] ** (250 / m.sum()) - 1) * 100, (q / np.maximum.accumulate(q) - 1).min() * 100))
    return out


def win_stats(L, base, lo, hi):
    """그 기간 1일봉만 · 계좌(base = 1일봉 밖 몫) 날마다 평가: 연 · 되돌림 뺀 골 + 손절 무리(10거래일 안 −4% 손실 3번 넘게)."""
    import numpy as np
    import a_mtm
    z = np.zeros(len(_D))
    m = np.array([lo <= d < hi for d in _D])
    out = []
    for b in (z, base):
        rc, rm = a_mtm.account(_D, L, b, mode="cost"), a_mtm.account(_D, L, b, mode="mark")
        q, qm = np.cumprod(1 + rc[m]), np.cumprod(1 + rm[m])
        out.append(((qm[-1] ** (250 / m.sum()) - 1) * 100, (q / np.maximum.accumulate(q) - 1).min() * 100))
    # 36회차: 여러 하락을 다 보는 잣대 — 1일봉만 되돌림 뺀 곡선의 '하락 평균 깊이'(꼭대기 아래에 있는 날들의 깊이 제곱 평균의 제곱근)
    rc1 = a_mtm.account(_D, L, z, mode="cost")
    q1 = np.cumprod(1 + rc1[m]); dd1 = q1 / np.maximum.accumulate(q1) - 1
    ulcer = float(np.sqrt(np.mean(dd1 ** 2)) * 100)
    import bisect
    st = sorted((bisect.bisect_left(_D, s), p * k / 10) for c, b_, s, p, k in L if lo <= s < hi and p <= -4)
    pos = [x for x, _ in st]
    cl, j, cl_loss = 0, 0, 0.0
    while j < len(pos):
        k = j
        while k + 1 < len(pos) and pos[k + 1] - pos[j] < 10:
            k += 1
        if k - j + 1 >= 3:
            cl += 1; cl_loss += sum(v for _, v in st[j:k + 1]); j = k + 1
        else:
            j += 1
    return out, (cl, cl_loss, ulcer), len(pos)


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
    Lc = [[c, b, s, round(p - 0.2, 4), k] for c, b, s, p, k in L]
    json.dump(Lc, open(SP + "c_" + led, "w"))
    od = oned(Lc)          # _D도 여기서 채움
    env2 = {**os.environ, **ACC, "I_LEDGER": "c_" + led, "I_DUMP": SP + "d_" + led.replace(".json", ".npz"), "I_MTM": "0" if SPLIT2 else "1"}
    r2 = subprocess.run([sys.executable, os.path.join(RES, "i013.py")], env=env2, capture_output=True, text=True, timeout=3600)
    acc = {}
    for x in r2.stdout.splitlines():
        m = re.match(r"\s+(B|C1 21~25|C2 2026)\s+날마다 평가 연\s+([+-][\d.]+) 골\s+([-\d.]+) · 되돌림 뺀 골\s+([-\d.]+)", x)
        if m:
            acc[m.group(1)] = (float(m.group(2)), float(m.group(3)), float(m.group(4)))
    if SPLIT2:
        import numpy as np
        zd = np.load(SP + "d_" + led.replace(".json", ".npz"))
        base = zd["mix"] - zd["d1"]
        (o1, a1), c1_, n1 = win_stats(Lc, base, "20170101", "20230101")
        s = (f"{sx or '바탕':28s} | 고르기 17~22: 1일봉만 연 {o1[0]:+.1f} 되돌림뺀 {o1[1]:.1f} 하락평균 {c1_[2]:.2f} · 손절 {n1} 무리 {c1_[0]} 무리손실 {c1_[1]:.1f}"
             f" · 계좌 연 {a1[0]:+.1f} 되돌림뺀 {a1[1]:.1f}")
        if SHOW_TEST:
            (o2, a2), c2_, n2 = win_stats(Lc, base, "20230101", "20260101")
            s += f" | 시험 23~25: 1일봉만 연 {o2[0]:+.1f} 되돌림뺀 {o2[1]:.1f} 하락평균 {c2_[2]:.2f} · 손절 {n2} 무리 {c2_[0]} 무리손실 {c2_[1]:.1f} · 계좌 연 {a2[0]:+.1f} 되돌림뺀 {a2[1]:.1f}"
        if OPEN:
            (o3, a3), c3_, n3 = win_stats(Lc, base, "20260101", "20991231")
            s += f" | 2026: 1일봉만 연 {o3[0]:+.1f} 되돌림뺀 {o3[1]:.1f} 하락평균 {c3_[2]:.2f} · 무리 {c3_[0]} 무리손실 {c3_[1]:.1f} · 계좌 연 {a3[0]:+.1f} 되돌림뺀 {a3[1]:.1f}"
        return s
    b, c1 = acc.get("B", (0, 0, 0)), acc.get("C1 21~25", (0, 0, 0))
    f = m_front.groups()
    bk = m_back.groups() if m_back else ("?", "?", "?")
    s = (f"{sx or '바탕':28s} | 앞 1일봉 연 {f[0]} 골 {f[1]} 매매 {f[2]} 손절 {f[3]} 무리 {f[4]} 연속 {f[5]}"
         f" | 1일봉만 앞 연 {od[0][0]:+.1f} 되돌림뺀 {od[0][1]:.1f}"
         f" | 계좌 B 연 {b[0]:+.1f} 골 {b[1]:.1f} 되돌림뺀 {b[2]:.1f}")
    if SHOW_C1:
        s += (f" | 뒤(21~25) 손절 {bk[0]} 무리 {bk[1]} 연속 {bk[2]} · 1일봉만 연 {od[1][0]:+.1f} 되돌림뺀 {od[1][1]:.1f}"
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
