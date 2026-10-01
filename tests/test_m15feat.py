import unittest

import numpy as np

import m15feat as F

SLOTS = [f"{9 + m // 60:02d}{m % 60:02d}" for m in range(0, 26 * 15, 15)]


def fake(days=30, seed=0):
    rng = np.random.default_rng(seed)
    t = [f"202509{d + 1:02d}{s}" for d in range(days) for s in SLOTS]
    c = 100 * np.cumprod(1 + rng.normal(0, 0.002, len(t)))
    o = np.r_[100.0, c[:-1]] * (1 + rng.normal(0, 0.001, len(t)))
    h = np.maximum(o, c) * 1.001
    l = np.minimum(o, c) * 0.999
    v = rng.integers(100, 1000, len(t)).astype(float)
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": v}


def cut(b, n):
    return {k: (b[k][:n] if k == "t" else np.asarray(b[k])[:n]) for k in b}


class NoPeek(unittest.TestCase):
    """봉 k까지의 값은 봉 k 뒤를 지우거나 바꿔도 같아야 함."""

    def test_features_use_only_bars_up_to_now(self):
        b = fake()
        n = 26 * 20 + 7
        for fn in (F.relvol, F.gap, F.day_ret, F.vwap_dev):
            full, part = fn(b), fn(cut(b, n))
            np.testing.assert_allclose(full[:n], part, equal_nan=True, err_msg=fn.__name__)
            changed = {k: (list(b[k]) if k == "t" else np.array(b[k], float)) for k in b}
            for k in ("o", "h", "l", "c", "v"):
                changed[k][n:] *= 3
            np.testing.assert_allclose(fn(changed)[:n], full[:n], equal_nan=True, err_msg=fn.__name__)

    def test_market_at_a_time_ignores_later_bars(self):
        data = {str(i): fake(seed=i) for i in range(6)}
        n = 26 * 10 + 3
        full = F.market(data)
        part = F.market({k: cut(b, n) for k, b in data.items()})
        for s, x in part.items():
            self.assertAlmostEqual(full[s], x)


class Values(unittest.TestCase):
    def test_simple_values(self):
        t = ["202509010900", "202509010915", "202509020900", "202509020915"]
        b = {"t": t, "o": np.array([100, 101, 110, 111.0]), "h": np.array([101, 102, 111, 112.0]),
             "l": np.array([99, 100, 109, 110.0]), "c": np.array([101, 102, 111, 112.0]), "v": np.array([1, 1, 1, 1.0])}
        g = F.gap(b)
        self.assertTrue(np.isnan(g[0]))
        self.assertAlmostEqual(g[2], 110 / 102 - 1)
        self.assertAlmostEqual(F.day_ret(b)[3], 112 / 110 - 1)
        self.assertTrue(np.isnan(F.relvol(b)[3]), "지난 날이 모자라면 값 없음")


if __name__ == "__main__":
    unittest.main()
