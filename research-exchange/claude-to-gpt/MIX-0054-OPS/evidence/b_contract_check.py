"""MIX-0054-OPS 산술 점검 — 모의계좌 '바탕 가상 계좌 계약'(수량 · B)이 연구 regime_dev.account()의 vb · ve · cash · A를 그대로 지키는지.
연구 쪽은 account()의 바꿈 · 덜기 줄을 그대로 옮긴 식(아래 research_*), 모의 쪽은 실제 현금 K · 바탕 든 것 H · 덧붙임 수량 q · 값 p · B만 씀.
대응: vb ↔ NAV_b = K + B + H · ve ↔ q × p · cash ↔ −B · A ↔ NAV = K + H + q × p.
알려진 차이 하나: 연구는 맞추는 날 '바탕 몫을 A로 되돌리는 가상 이동'에도 비용(줄이면 0.30% · 늘리면 0.05%)을 매김. 모의계좌에서는 바탕이 실제로
사고팔지 않으므로 이 비용이 없음 → 아래에서 그 항만 따로 셈(연구가 그만큼 보수적)."""
COST_ETF, COST_BASE_DOWN, COST_BASE_UP = 0.0005, 0.0030, 0.0005
ok = 0


def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)


def close(a, b, eps=1e-9):
    return abs(a - b) < eps


def research_rebal(vb, ve, cash, fe, same_code=True, base_cost=True):
    A = vb + ve + cash
    tb, te = A, fe * A                       # fb = 1(세 국면 모두)
    cost = (COST_BASE_DOWN * max(0, vb - tb) + COST_BASE_UP * max(0, tb - vb)) if base_cost else 0.0
    cost += COST_ETF * abs(te - ve) if same_code else COST_ETF * (ve + te)
    A -= cost
    vb, ve = A, fe * A
    return vb, ve, A - vb - ve


def research_trim(vb, ve, cash, cut):
    return vb, ve - cut, cash + cut * (1 - COST_ETF)


class Live:
    def __init__(self, K, H):
        self.K, self.H, self.q, self.p, self.B = K, H, 0.0, 1.0, 0.0

    nav = property(lambda s: s.K + s.H + s.q * s.p)
    nav_b = property(lambda s: s.K + s.B + s.H)
    cash_b = property(lambda s: s.K + s.B)

    def rebal(self, fe, same_code=True):
        """맞추는 날: 덧붙임만 실제로 사고팜(비용은 실제 현금에서) → B = 맞춘 뒤 덧붙임 평가액(조정 후 자금잔액)."""
        ve = self.q * self.p
        A = self.nav
        # 연구와 같은 순서: 비용은 '비용 빼기 전 목표 fe × A'로 셈 → A에서 뺌 → 목표 = fe × (A − 비용)
        cost = COST_ETF * abs(fe * A - ve) if same_code else COST_ETF * (ve + fe * A)
        te = fe * (A - cost)
        self.K -= (te - ve) + cost
        self.q = te / self.p
        self.B = te                          # 조정 후 자금잔액 = 맞춘 뒤 덧붙임 평가액(연구 cash = −ve)

    def move(self, base_r, etf_r):
        self.H *= 1 + base_r                 # 바탕 든 것의 등락(바탕 현금은 그대로)
        self.p *= 1 + etf_r

    def trim(self, cut):
        """덜기: 덧붙임을 cut만큼 팜 → 실제 현금 + 순수입 · B는 순수입만큼 줄어듦(가격 등락으로는 안 바뀜)."""
        self.q -= cut / self.p
        self.K += cut * (1 - COST_ETF)
        self.B -= cut * (1 - COST_ETF)


def same(L, r):
    vb, ve, cash = r
    return close(L.nav_b, vb) and close(L.q * L.p, ve) and close(-L.B, cash) and close(L.nav, vb + ve + cash)


# 바탕: 계좌 100 · 그 가운데 바탕 든 것 50(바탕 현금 비율 0.5) · 덧붙임 없음
L = Live(K=50.0, H=50.0)
r = (100.0, 0.0, 0.0)                         # 연구: vb = 바탕 전체(현금 포함) · ve 0 · cash 0
check("0 시작: 모의 NAV_b · 덧붙임 · −B · NAV = 연구 vb · ve · cash · A", same(L, r))
L.rebal(0.4); r = research_rebal(*r, 0.4)
check("1 첫 맞춤(상승 0.4): B = 맞춘 뒤 덧붙임 평가액 · 연구와 같음(바탕 가상 이동 없음 → 비용 항 0)", same(L, r) and close(L.B, L.q * L.p))
# 덧붙임 40 → 가격 −5% → 38 · 바탕 든 것 +4%
h0 = L.H; L.move(0.04, -0.05); r = (r[0] + (L.H - h0), r[1] * 0.95, r[2])
check("2 맞추지 않는 날: 가격 등락으로 B 안 바뀜 · 연구 cash 그대로 · vb는 바탕 등락만", same(L, r) and close(L.B, -r[2]))
# 달 첫날 같은 종목 다시 맞춤(덧붙임 38 → 목표 0.4 × A ≈ 40.x: 사는 쪽)
r_nobc = research_rebal(*r, 0.4, base_cost=False); r_bc = research_rebal(*r, 0.4)
L.rebal(0.4)
check("3 달 첫날 38 → 약 40(같은 종목 · 사기): B = 맞춘 뒤 평가액 · 연구(바탕 가상 이동 비용 뺀 식)와 같음", same(L, r_nobc))
gap = (r_nobc[0] + r_nobc[1] + r_nobc[2]) - (r_bc[0] + r_bc[1] + r_bc[2])
print(f"   연구가 더 뺀 바탕 가상 이동 비용 = {gap:.6f}(계좌 대비 {gap / L.nav * 100:.4f}%)")
r = r_nobc
# 덧붙임 +10% → 약 44 · 바탕 −3% → 달 첫날 다시 맞춤(44 → 약 40: 파는 쪽 · GPT 예시 40 → 38과 같은 방향)
h0 = L.H; L.move(-0.03, 0.10); r = (r[0] + (L.H - h0), r[1] * 1.10, r[2])
check("4 등락 뒤 대응 유지", same(L, r))
L.rebal(0.4); r = research_rebal(*r, 0.4, base_cost=False)
check("5 달 첫날 약 44 → 약 40(같은 종목 · 팔기): B = 맞춘 뒤 평가액(그날 순거래 −4가 아님)", same(L, r) and L.B > 39)
# GPT 예시 그대로: 덧붙임 40 → 38(목표가 줄어든 경우), 38 → 41
for a, b in ((40.0, 38.0), (38.0, 41.0)):
    L2 = Live(K=60.0, H=40.0); L2.q, L2.p, L2.B, L2.K = a, 1.0, a, 60.0 - a
    A = L2.nav; fe = b / A
    r2 = research_rebal(L2.nav_b, a, -a, fe, base_cost=False)
    L2.rebal(fe)
    check(f"6 GPT 예시 {a:.0f} → {b:.0f}: B ≈ {b:.0f}(순거래 {b - a:+.0f}가 아님) · 연구와 같음", same(L2, r2) and abs(L2.B - b) < 0.1)
# 덜기: 바탕이 현금을 다시 써서 실제 현금이 모자람 → 덧붙임 5를 팖
L.trim(5.0); r = research_trim(*r, 5.0)
check("7 덜기 매도: B는 순수입만큼만 줄고 바탕 현금 cash_b는 그대로 · 연구와 같음", same(L, r))
# 하락 → 덧붙임 다 팖
L.rebal(0.0); r = research_rebal(*r, 0.0, base_cost=False)
check("8 완전 청산(하락): B = 0 · 덧붙임 0 · NAV_b = NAV", same(L, r) and close(L.B, 0.0) and close(L.nav_b, L.nav))
# 종목 바꿈(횡보 인버스 0.4) — 다른 종목이면 비용 = c × (팔 것 + 살 것)
L.rebal(0.4); r = research_rebal(*r, 0.4, base_cost=False)
L.rebal(0.4, same_code=False); r = research_rebal(*r, 0.4, same_code=False, base_cost=False)
check("9 종목 바꿈(레버리지 → 인버스): B = 맞춘 뒤 평가액 · 연구와 같음", same(L, r))
print(f"모두 {ok}개 통과")
