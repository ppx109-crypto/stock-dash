"""미래 참조 자르기 시험(2026-10-03 사용자 "항상 미래 참조는 원천 차단해줘").
방법: 같은 계산을 '온 자료'와 '어느 날(자른 날) 뒤 자료를 처음부터 안 읽은 자료(I_CUT)'로 두 번 돌림.
      자른 날 앞날까지의 판단 · 날마다 손익이 한 칸이라도 다르면 = 그날 계산에 뒷날 자료가 섞였다는 뜻 → 불합격.
      (자른 날 당일은 자료 끝이라 들고 있던 것을 억지로 팔아 비용이 달라질 수 있어 빼고 봄.)
대상: 최종 판(i013: 1일봉 장부 + 빈칸 엔진 급락 되돌림 · 하락 추세 달러 · 돌리기 + 코스닥 과열 인버스) · 분위기 점수(mood.build) · 오늘의 신호 계산기.
쓰는 법: python research/lookahead.py  (자른 날 여러 개를 돌려 모두 합격이어야 채택)"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

RES = Path(__file__).resolve().parent
CUTS = ("20181015", "20200320", "20220615", "20240805", "20260701")
FINAL = dict(I_DIP="1", I_DOLLAR="2", I_GATE="idle20", I_L="20", I_TOP="2", I_CANDS="133690,138230,132030,148070", I_W="1", I_QINV="free")


def run_i013(extra, cut=""):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "dump.npz"
        env = {**os.environ, **FINAL, **extra, "I_DUMP": str(out), "I_CUT": cut}
        subprocess.run([sys.executable, str(RES / "i013.py")], env=env, check=True, capture_output=True)
        z = np.load(out)
        return {k: z[k] for k in z.files}


def compare(full, cut_res, cut):
    days = list(full["days"])
    k = int(np.searchsorted(full["days"], cut, side="right")) - 1          # 자른 날 위치
    bad = []
    for key in ("d1", "used", "rot", "dip", "qinv", "mix"):
        a, b = full[key][:k], cut_res[key][:k]                              # 자른 날 앞날까지
        if len(b) < k or not np.allclose(a, b, atol=1e-12, equal_nan=True):
            diff = np.flatnonzero(~np.isclose(a, b[:len(a)], atol=1e-12, equal_nan=True)) if len(b) >= k else [0]
            bad.append(f"{key}(처음 다른 날 {days[diff[0]] if len(diff) else '?'})")
    return bad


def check_final(extra=None, label="최종 판"):
    extra = extra or {}
    full = run_i013(extra)
    ok = True
    for cut in CUTS:
        bad = compare(full, run_i013(extra, cut), cut)
        print(f"  [{label}] 자른 날 {cut}: {'합격' if not bad else '불합격 — ' + ', '.join(bad)}", flush=True)
        ok &= not bad
    return ok


def check_mood():
    sys.path.insert(0, str(RES))
    import itools as I
    import mood
    full, _ = mood.build(I.DAYS)
    ok = True
    for cut in CUTS[:3]:
        k = int(np.searchsorted(np.array(I.DAYS), cut, side="right"))
        part, _ = mood.build(I.DAYS[:k])
        same = np.allclose(full[:k - 1], part[:k - 1], equal_nan=True)
        print(f"  [분위기 점수] 자른 날 {cut}: {'합격' if same else '불합격'}", flush=True)
        ok &= same
    return ok


if __name__ == "__main__":
    print("== 미래 참조 자르기 시험 ==", flush=True)
    a = check_final()
    b = check_final({"I_MOOD": "70"}, "최종 판 + 분위기(후보)")
    c = check_mood()
    print("모두 합격" if a and b and c else "불합격 있음 — 고쳐야 함", flush=True)
