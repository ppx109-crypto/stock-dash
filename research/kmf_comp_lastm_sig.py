"""COMP-0004 공개 신호 표 — 마지막 30분 모멘텀(14:45 진입 · 15:15 정리). P2 v1.3이 안 들고 있는 날 · 시간에만 비공개 결합 엔진이 씀.
신호 2개(문턱 없음 · 방향만):
  M1 첫 30분 = sign(그날 569분(09:29) 이하 마지막 1분봉 종가 − 앞 거래일 마지막 1분봉 종가)   (밤사이 갭 + 첫 30분)
  M2 낮 동안 = sign(884분(14:44) 이하 마지막 1분봉 종가 − 그날 첫 1분봉 시가)
  둘 다 885분(14:45) 시가 전에 다 나온 값. 0이면 신호 없음.
진입 분 = 885분부터 처음 있는 1분봉(시가) · 정리 분 915(15:15) · 목표 없음 · 손절 폭 = s × ATR(885분에 닫힌 15분봉 kmf_nb.E10의 ATR) · s ∈ {1.0, 1.5}.
평가 날 = 01-08 ~ 10-12(183일 · COMP-0001 ~ 0003과 같음). 앞 거래일 = kmf_nb.DAYS에서 바로 앞 날.
python3 research/kmf_comp_lastm_sig.py → research/kmf_comp_lastm_sig.json"""
import sys, json, bisect, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import kmf_nb as K, kmf_r0q as Q, kmf_hdd_pre as P
DAYS = [d for d in K.DAYS if "20260108" <= d <= "20261012"]
KEY15 = [(b[0], b[1]) for b in K.B15]

def last_at(d, m):
    x = K.BY[d]; ms = [mm for mm in x if mm <= m]
    return x[max(ms)][5] if ms else None

def atr885(d):
    i = bisect.bisect_right(KEY15, (d, 885)) - 1
    return K.E10[i][1] if i >= 0 and K.B15[i][0] == d else None

def table(s):
    out = {"M1": {}, "M2": {}}
    for d in DAYS:
        x = K.BY[d]; me = next((mm for mm in range(885, 915) if mm in x), None); a = atr885(d)
        prev = K.DAYS[K.DAYS.index(d) - 1]; pc = last_at(prev, 934); c569 = last_at(d, 569); c884 = last_at(d, 884); o = x[min(x)][2]
        for k, r in (("M1", None if (pc is None or c569 is None) else c569 - pc), ("M2", None if c884 is None else c884 - o)):
            ok = me is not None and a and r
            out[k][d] = [[me, 1 if r > 0 else -1, None, s * a, 915, 885]] if ok else []
    return out

def main():
    data_sha = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
    if not K.CUT: assert data_sha == P.DATA_EXPECT
    sig = {}
    for s in (1.0, 1.5):
        t = table(s)
        for k in t: sig[f"{k} s{s}"] = t[k]
    out = {"meta": {"days": DAYS, "data_sha256": data_sha, "KMF_CUT": K.CUT, "열": ["진입 분 me", "방향", "목표(null)", "손절 폭", "정리 분", "판단 분"],
                    "code_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ("kmf_comp_lastm_sig.py", "kmf_nb.py", "kmf_r0q.py", "kmf_hdd_pre.py")}},
           "holes": {d: list(v) for d, v in Q.HOLES.items()}, "sig": sig}
    (HERE / "kmf_comp_lastm_sig.json").write_text(json.dumps(out, ensure_ascii=False))
    for k, t in sig.items(): print(k, "신호 날", sum(1 for v in t.values() if v), "롱", sum(1 for v in t.values() if v and v[0][1] > 0))

if __name__ == "__main__":
    main()
