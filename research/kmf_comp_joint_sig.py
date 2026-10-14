"""COMP-0003 H2(GPT #344) 공개 신호 표 — P2 v1.3이 아직 거래할 수 있는 날, P2가 들고 있지 않은 분에 보완 봇이 쓸 신호를 미리 뽑아 둡니다.
신호(고정 규칙 그대로 · 새 문턱 없음): R0 = kmf_nb.sig_r0(k 1.0 · 손절 1.0 ATR · 목표 = 신호 때 EMA10 · 15:15 정리)
  · S3 = kmf_rlk4.s3(T2 손절 1.5 ATR + 15분 기울기/ATR ≤ 0.5 · 정리 = 15분 종가가 EMA10을 거꾸로 건넌 봉 끝 또는 15:15).
신호 분 m0 = 닫힌 15분봉의 '끝 분'(= 다음 봉 첫 분 · 그 분 시가 진입 · 지연 0). 진입 분 me = m0부터 처음 있는 1분봉(kmf_nb.execute와 같은 규칙) · me ≥ 정리 분이면 버림.
평가 날 = 01-08 ~ 10-12(COMP-0001 · 0002와 같은 183일). 빈 29분 9구간 = kmf_r0q.HOLES(스트레스판에서 들고 지나가면 그 안 손절가 도달로 봄).
python3 research/kmf_comp_joint_sig.py → research/kmf_comp_joint_sig.json(비공개 결합 엔진의 입력 · 해시를 잠금에 적음)"""
import sys, json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import kmf_nb as K, kmf_rlk4 as R4, kmf_r0q as Q, kmf_hdd_pre as P
DAYS = [d for d in K.DAYS if "20260108" <= d <= "20261012"]

def table(f):
    out = {}
    for d in DAYS:
        x = K.BY[d]; rows = []
        for (m0, side, tg, sd, mx) in f(d):
            me = next((mm for mm in range(m0, 935) if mm in x), None)
            if me is None or me >= mx: continue
            rows.append([me, side, tg, sd, mx, m0])
        out[d] = rows
    return out

def main():
    data_sha = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
    assert data_sha == P.DATA_EXPECT
    sig = {"R0": table(lambda d: K.sig_r0(d)), "S3": table(lambda d: R4.s3(d))}
    out = {"meta": {"days": DAYS, "data_sha256": data_sha, "열": ["진입 분 me", "방향", "목표(없으면 null)", "손절 폭", "정리 분", "신호 분 m0"],
                    "code_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ("kmf_comp_joint_sig.py", "kmf_nb.py", "kmf_rlk4.py", "kmf_r0q.py", "kmf_hdd_pre.py")}},
           "holes": {d: list(v) for d, v in Q.HOLES.items()}, "sig": sig}
    (HERE / "kmf_comp_joint_sig.json").write_text(json.dumps(out, ensure_ascii=False))
    for k, t in sig.items(): print(k, "신호 수", sum(len(v) for v in t.values()), "신호 있는 날", sum(1 for v in t.values() if v))

if __name__ == "__main__":
    main()
