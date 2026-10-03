"""손절 줄 연구 설계의 미래 참조 시험 — 1일봉 장부를 자른 · 더럽힌 세계에서 다시 만들어 그날까지 판 매매가 같은지.

쓰는 법: python research/s_cut.py ST2_4_20_4 [자른 날 …]   (I_SX 설계 · 날은 YYYYMMDD · 빼면 기본 넷)
cut   : 그날 뒤 종가 · 후보를 처음부터 없앰 → 그날 앞에 판 매매(판 날 < 그날)가 같아야 함
poison: 그날 뒤 종가를 엉터리로(길이 그대로 · 자리로 미리 보기를 잡음) → 그날까지 판 매매(판 날 ≤ 그날)와
        그날까지 산 매매(종목 · 산 날)가 같아야 함(산 것까지 봐야 '며칠 뒤 종가를 보고 사기'가 걸림 · 검사 눈 PK5로 확인)
※ 엔진은 한 판의 매매가 60건 아래면 결과를 안 냄 → 뒤쪽 판(2021-01 ~)이 짧게 잘리는 2021 상반기는 자른 날로 안 씀
"""
import json
import os
import subprocess
import sys
import tempfile

RES = os.path.dirname(os.path.abspath(__file__))


def ledger(sx, cut="", mode="cut"):
    f = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    env = {**os.environ, "I_VAR": "DNA_past", "I_SX": sx, "I_DUMP_LEDGER": f, "PYTHONHASHSEED": "0"}
    if cut:
        env.update(I_CUTDAY=cut, I_CUTMODE=mode)
    r = subprocess.run([sys.executable, os.path.join(RES, "i044.py")], env=env, capture_output=True, text=True, timeout=3600)
    if r.returncode:
        raise SystemExit(r.stderr[-500:])
    return [tuple(x) for x in json.load(open(f))]


if __name__ == "__main__":
    sx = sys.argv[1]
    cuts = sys.argv[2:] or ["20190315", "20220315", "20230915", "20250310"]
    full = ledger(sx)
    bad = 0
    for cut in cuts:
        for mode in ("cut", "poison"):
            got = ledger(sx, cut, mode)
            keep = (lambda t: t[2] < cut) if mode == "cut" else (lambda t: t[2] <= cut)
            a, b = sorted(t for t in full if keep(t)), sorted(t for t in got if keep(t))
            diff = len(set(a) ^ set(b))
            if mode == "poison":
                buys = lambda L: {(t[0], t[1]) for t in L if t[1] <= cut}
                diff += len(buys(full) ^ buys(got))
            bad += diff > 0
            print(f"{sx} {mode:6s} {cut}: 견준 매매 {len(a)} · 다른 매매 {diff} → {'통과' if diff == 0 else '어긋남'}", flush=True)
    print("종합:", "모두 통과" if bad == 0 else f"{bad}곳 어긋남")
