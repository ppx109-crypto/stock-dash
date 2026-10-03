"""빈칸 엔진 · 코스닥 과열 인버스 '오늘의 신호' 계산기(I 갈래 정리 · 주문 없음 · 운영 파일 아님).
모의투자 넣기를 사용자가 정하면 paper_trade.py 쪽에서 이 판단을 그대로 쓰게 하려고 미리 만듦.

판단(그날 15:15 값 또는 종가 · 미래 참조 없음):
  엔진 켬     : 1일봉(+1시간봉)이 돈을 20% 미만 쓰고 있음(used < 0.2)
  ① 급락 되돌림: 시장 폭 < 50 · KODEX 200 5일 수익 ≤ −5%(15:15 판단이면 −4.5%) → 069500 · 익절 +3 · 손절 −3 · 20일 · 손절 뒤 20일 쉬기
  ② 하락 추세  : 원 · 달러(138230) 20일 > +2% · 코스피 < 20일선 → 138230 달러선물
  ③ 돌리기     : 나스닥100(133690) · 달러선물(138230) · 금(132030) · 국채10년(148070) 중 20일 수익 > 0 인 위 2개 반반(주 마지막 거래일에 고름)
  코스닥 과열 인버스(엔진과 따로 · 1일봉이 비운 몫으로): 코스닥150(229200) 10일 수익 ≥ +10%(15:15면 +9.5%) → 251340 · 익절 +1.5 · 손절 −1.5 · 10일
  (후보 · 아직 최종 판 아님) 분위기 단계: 시장 분위기 점수(research/mood.py) ≥ 70이면 엔진 돈으로 KODEX 200 · 익절 +8 · 손절 −3 · 10일
연구 근거: docs/RL-INVERSE.md · RL-INVERSE-CARD.md(i013 · i014 · i020 · i025)."""
import sys

import numpy as np

ROT = ("133690", "138230", "132030", "148070")


def _ret(a, n):
    return a[-1] / a[-1 - n] - 1 if len(a) > n and a[-1 - n] > 0 else float("nan")


def decide(px, breadth, used, at_1515=False, mood=None):
    """px: {코드: 종가 배열(오래된 → 오늘)} · breadth: 오늘 시장 폭(%) · used: 1일봉이 쓰는 몫(0 ~ 1).
    돌려줌: {'엔진': bool, '급락': bool, '하락추세': bool, '돌리기': {코드: 몫}, '코스닥인버스': bool, '까닭': [글]}"""
    k, q, dol = (np.asarray(px[c], float) for c in ("069500", "229200", "138230"))
    why = []
    engine = used < 0.2
    why.append(f"1일봉 쓴 몫 {used * 100:.0f}% → 엔진 {'켬' if engine else '끔(20% 넘음)'}")
    dip_th, q_th = (-0.045, 0.095) if at_1515 else (-0.05, 0.10)
    r5 = _ret(k, 5)
    dip = engine and breadth < 50 and r5 <= dip_th
    why.append(f"코스피 5일 {r5 * 100:+.1f}% · 시장 폭 {breadth:.0f} → 급락 되돌림 {'예' if dip else '아니오'}")
    ma20 = k[-20:].mean() if len(k) >= 20 else float("nan")
    d20 = _ret(dol, 20)
    down = engine and not dip and d20 > 0.02 and k[-1] < ma20
    why.append(f"원 · 달러 20일 {d20 * 100:+.1f}% · 코스피 {'<' if k[-1] < ma20 else '≥'} 20일선 → 하락 추세(달러) {'예' if down else '아니오'}")
    rot = {}
    if engine and not dip and not down:
        sc = sorted(((_ret(np.asarray(px[c], float), 20), c) for c in ROT if c in px), reverse=True)
        top = [c for r, c in sc if r == r and r > 0][:2]
        rot = {c: 1 / 2 for c in top} if len(top) == 2 else ({top[0]: 0.5} if top else {})
        why.append("돌리기 20일: " + " · ".join(f"{c} {r * 100:+.1f}%" for r, c in sc) + f" → {', '.join(rot) or '현금(모두 −)'}")
    q10 = _ret(q, 10)
    qinv = q10 >= q_th
    why.append(f"코스닥150 10일 {q10 * 100:+.1f}% → 코스닥 인버스 {'예' if qinv else '아니오'}")
    mood_buy = bool(engine and mood is not None and mood == mood and mood >= 70)
    if mood is not None:
        why.append(f"(후보) 시장 분위기 점수 {mood:.0f} → KODEX 200 {'사기' if mood_buy else '아님'}")
    return {"엔진": engine, "급락": dip, "하락추세": down, "돌리기": rot, "코스닥인버스": qinv, "분위기사기": mood_buy, "까닭": why}


if __name__ == "__main__":
    sys.path.insert(0, "/home/user/stock-dash/research")
    import itools as I
    used = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    px = {c: np.nan_to_num(I.px(c), nan=np.nan) for c in ("069500", "229200", "138230") + ROT}
    px = {c: a[~np.isnan(a)] for c, a in px.items()}
    br = I.breadth()
    b = br[~np.isnan(br)][-1] if np.isfinite(br).any() else 100.0
    import mood as MOOD
    sc, _ = MOOD.build(I.DAYS)
    last = sc[np.isfinite(sc)]
    out = decide(px, b, used, mood=float(last[-1]) if len(last) else None)
    print(f"== 오늘의 빈칸 엔진 신호({I.DAYS[-1]} 종가 기준 · 1일봉 쓴 몫 {used * 100:.0f}%) ==")
    for w in out["까닭"]:
        print("  ·", w)
