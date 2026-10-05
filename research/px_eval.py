"""1일봉 이익확보 · 고점추격 연구(docs/RL-PX.md) 실행기 — 설계(I_PX)마다 1일봉 장부(조용함 문턱 그때까지 · DNA_past)를 다시 만들어
1일봉만 계좌를 날마다 평가(실제 비용 −0.2%p): 해마다 수익 · 되돌림 셈 골(꼭대기 대비) · 되돌림 뺀 골 · 큰 이익 매매(꼭대기 +20% 넘음)의 평균 되돌림.
쓰는 법: python research/px_eval.py "" LDU "TR15_20" …   ("" = 바탕) · PX_SHOW_TEST=1(시험 2023 ~ 25) · PX_OPEN2026=1(마지막에만)."""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import numpy as np

RES = os.path.dirname(os.path.abspath(__file__))
SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
PER = [("고르기 17~22", "20170101", "20230101")] + ([("시험 23~25", "20230101", "20260101")] if os.environ.get("PX_SHOW_TEST") == "1" else []) \
    + ([("2026", "20260101", "20991231")] if os.environ.get("PX_OPEN2026") == "1" else [])


def ledger(px):
    tag = re.sub(r"[^A-Za-z0-9_]+", "-", px) or "base"
    f = SP + f"px_led_{tag}.json"
    env = {**os.environ, "I_VAR": "DNA_past", "I_SX": "", "I_PX": px, "I_DUMP_LEDGER": f}
    r = subprocess.run([sys.executable, os.path.join(RES, "i044.py")], env=env, capture_output=True, text=True, timeout=3600)
    if r.returncode:
        raise RuntimeError(r.stderr[-400:])
    return [(c, b, e, p - 0.2, k) for c, b, e, p, k in json.load(open(f))]


def stats(L):
    import a_mtm
    import itools as I
    import nrl
    D = list(I.DAYS); z = np.zeros(len(D))
    rm, rc = a_mtm.account(D, L, z, mode="mark"), a_mtm.account(D, L, z, mode="cost")
    out = []
    for name, lo, hi in PER:
        m = np.array([lo <= d < hi for d in D])
        q, qc = np.cumprod(1 + rm[m]), np.cumprod(1 + rc[m])
        ann = (q[-1] ** (250 / m.sum()) - 1) * 100
        ddm = (q / np.maximum.accumulate(q) - 1).min() * 100
        ddc = (qc / np.maximum.accumulate(qc) - 1).min() * 100
        gb = []
        for c, b, e, p, k in L:
            if lo <= e < hi:
                rows = dict(nrl.prices.get(c, {}).get("rows") or [])
                ds = sorted(d for d in rows if b <= d <= e)
                if ds and rows.get(b):
                    pk = (max(rows[d] for d in ds) / rows[b] - 1) * 100
                    if pk >= 20:
                        gb.append(pk - p)
        out.append(f"{name}: 연 {ann:+6.1f} · 되돌림 셈 골 {ddm:6.1f} · 되돌림 뺀 골 {ddc:6.1f} · 큰 이익 {len(gb)}건 평균 되돌림 {np.mean(gb) if gb else 0:5.1f}%p")
    return " | ".join(out)


def one(px):
    try:
        return f"{px or '바탕':12s} | " + stats(ledger(px))
    except Exception as e:
        return f"{px or '바탕':12s} | 실패 {e}"


if __name__ == "__main__":
    with ThreadPoolExecutor(int(os.environ.get("PX_PAR", "3"))) as ex:
        for line in ex.map(one, sys.argv[1:] or [""]):
            print(line, flush=True)
