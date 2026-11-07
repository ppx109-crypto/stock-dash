"""MPOS-0024 H-USD 보조 장부(가산 보완 · DESIGN.md 판 3) — 순수 함수(파일 · 자료를 직접 읽지 않음 · 받은 값만 씀).
BASE는 고정 장부: 날마다 (날, BASE NAV B, BASE 남는 현금 slack)만 받고 바꾸지 않음. 모든 값은 NAV 단위(BASE 첫날 1).
보조 장부 = 주식 수 q × 원주가 + 받을 분배(건별) + 보조 현금 K(K < 0 = BASE 남는 현금을 빌려 씀).
- 목표(달 첫 거래일 · d−1 장 끝 값): G = max(0, min(x·B, (H + slack + K − b·B) ÷ (1 + 비용))) — 이상적 목표 금액 모델(d 종가로 수량 · d 종가 체결).
- 억지 팔기(그날 거래 뒤): slack + K < 0이면 s = min(H, 모자람 ÷ (1 − 비용)) 팜 · 그래도 < 0이면 자금 불능(FUNDING_INFEASIBLE) 기록 · 메우지 않음.
- 분배: 분배락 날 전날 장 끝 수량 × 주당 금액을 건별 받을 돈으로 · 그 건 지급일(그날 또는 그 뒤 첫 장부 날)에 그 건만 K로. 받을 돈은 현금으로 치지 않음.
- 값 없는 날: 사고팔지 않음 · 마지막 값으로 평가 · 모자라면 자금 불능.
하루 순서(고정): ① d 종가 평가 ② 분배락 권리(전날 수량) ③ 지급(그 건만) ④ 달 첫날 맞춤(팔기 또는 사기 · d 종가)
⑤ BASE 그날 수요(slack_d · 받은 값) ⑥ 억지 팔기(보유 안에서) ⑦ 빚 없음 검사(slack + K ≥ 0 · b와 무관한 필수 조건).
비용식(순환 없음): G의 상한 (H + slack + K − b·B) ÷ (1 + 비용)은 '산 금액 ≤ G'이므로 G 전체에 비용을 매긴 보수적 상한.
실제 거래액 t = G − q·P_d(d 종가)이고 비용 = |t| × 비용률 · 그 뒤 ⑥ ⑦에서 실제 현금으로 다시 검사.
b(목표 완충)는 목표에만 쓰고, 빚 없음(⑦)은 b와 따로 늘 검사.
자금 자격: 자금 불능 날이 하루라도 있으면 "FAIL"(뒤에 현금이 회복돼도 유지). 첫 실패 날 뒤 행은 '빚 허용 진단'(진단 전용) 표시.
돌려줌: {"행": 날별 기록, "자금 불능 날": [...], "자금 자격": PASS/FAIL, "첫 자금 불능 날", "억지 팔기": n, "회전": 합, "비용": 합}."""

EPS = 1e-12


def run_sleeve(base, price, divs, x, b, cost=0.0005):
    """base: [(날, B, slack)] 날 순서 · price: {날: 원주가}(없으면 거래 안 됨) · divs: [{"분배락": 날, "지급일": 날, "주당": 금액}]."""
    days = [d for d, _, _ in base]
    assert days == sorted(days) and len(set(days)) == len(days)
    by_ex = {}
    for v in divs:
        by_ex.setdefault(v["분배락"], []).append(v)
    q, K, last = 0.0, 0.0, None
    recv = []                       # [(지급일, 금액)] 건별
    rows, bad = [], []
    forced, turn, paid_cost = 0, 0.0, 0.0
    prev = None                     # d−1 장 끝: (B, slack, H, K)
    for j, (d, B, slack) in enumerate(base):
        p = price.get(d)
        q_prev = q
        if p is not None:
            last = p
        # 분배락: 전날 장 끝 수량(오늘 거래 전)으로 건별 받을 돈
        for v in by_ex.get(d, []):
            if q_prev > EPS:
                recv.append((v["지급일"], q_prev * v["주당"]))
        # 지급: 그 건만 현금으로
        keep = []
        for pay, amt in recv:
            if pay <= d:
                K += amt
            else:
                keep.append((pay, amt))
        recv = keep
        # 달 첫 거래일 맞춤(d−1 장 끝 값으로 목표 · d 종가 체결)
        first = j > 0 and d[:6] != days[j - 1][:6]
        if first and prev is not None and p is not None:
            B0, s0, H0, K0 = prev
            G = max(0.0, min(x * B0, (H0 + s0 + K0 - b * B0) / (1 + cost)))
            t = G - q * p
            if t > EPS:
                q += t / p
                K -= t * (1 + cost)
            elif t < -EPS:
                sell = min(-t, q * p)
                q -= sell / p
                K += sell * (1 - cost)
            turn += abs(t)
            paid_cost += abs(t) * cost
        # 억지 팔기(그날 BASE 거래 · 위 맞춤 뒤)
        H = q * last if last is not None else 0.0
        if slack + K < -EPS and p is not None and q > EPS:
            need = -(slack + K) / (1 - cost)
            s = min(H, need)
            q -= s / p
            K += s * (1 - cost)
            forced += 1
            turn += s
            paid_cost += s * cost
            if q < EPS:
                q = 0.0
            H = q * p
        if slack + K < -1e-10:
            bad.append({"날": d, "모자람": -(slack + K), "값 있음": p is not None, "받을 분배": sum(a for _, a in recv)})
        R = sum(a for _, a in recv)
        rows.append({"날": d, "B": B, "slack": slack, "q": q, "H": H, "받을 분배": R, "K": K, "계좌": B + H + R + K, "빚 허용 진단": bool(bad)})
        prev = (B, slack, H, K)
    return {"행": rows, "자금 불능 날": bad, "자금 자격": "FAIL" if bad else "PASS", "첫 자금 불능 날": bad[0]["날"] if bad else None,
            "억지 팔기": forced, "회전": turn, "비용": paid_cost}
