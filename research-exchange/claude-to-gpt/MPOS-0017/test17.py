"""MPOS-0017 주차 원장 합성 시험(GPT #442 round 2 요청 · 시장 자료 없음)."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos17")
import park17 as P

f = P.ETF_SIDE


def setup(Pv, mode="PARK"):
    P.S.update(mode=mode, poison="", P=Pv, gain=0.0, cost=0.0, traded=0.0, over=-1e9, miss=0, days=0, bond={"a": 100.0, "b": 102.0, "c": 99.0})


def test_price_up_no_trade_cost():
    setup(100.0)
    g = P.park_gain("a", "b")            # +2%
    assert abs(g - 2.0) < 1e-12 and abs(P.S["P"] - 102.0) < 1e-12
    c = P.park_trade(102.0)              # 잔여 = 평가액(다른 흐름 없음)
    assert abs(c) < 1e-12 and abs(P.S["P"] - 102.0) < 1e-12


def test_price_down_no_trade_cost():
    setup(100.0)
    P.S["bond"] = {"a": 100.0, "b": 99.0}
    P.park_gain("a", "b")
    assert abs(P.park_trade(99.0)) < 1e-12 and abs(P.S["P"] - 99.0) < 1e-12


def test_buy_cost_within_slack():
    setup(0.0)
    c = P.park_trade(0.5)
    assert abs(P.S["P"] + c - 0.5) < 1e-12 and P.S["P"] <= 0.5 - c + 1e-12


def test_partial_release():
    setup(0.5)
    c = P.park_trade(0.3)
    assert abs((0.3 - c) - P.S["P"]) < 1e-12 and P.S["P"] < 0.5


def test_full_release_cost_flag():
    setup(0.5)
    c = P.park_trade(0.0)                # 잔여 0 · 전액 해제 → 비용이 잔여를 넘음(원판 빚 0 단계가 메움)
    assert P.S["P"] == 0.0 and abs(c - 0.5 * f) < 1e-15


def test_zero_mode_no_gain():
    setup(100.0, "ZERO")
    assert P.park_gain("a", "b") == 0.0 and P.S["P"] == 100.0


def test_off_mode_noop():
    setup(100.0, "OFF")
    assert P.park_gain("a", "b") == 0.0 and P.park_trade(5.0) == 0.0


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("PASS", k)
