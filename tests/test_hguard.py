"""1시간봉 미래 참조 막기(hlab · hguard)의 인공 자료 시험."""
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

import hlab as H


def days(n, start=20240101):
    out, d = [], start
    while len(out) < n:
        y, m, dd = d // 10000, d // 100 % 100, d % 100
        if dd <= 28:
            out.append(str(d))
        d = d + 1 if dd < 28 else (y * 10000 + (m + 1) * 100 + 1 if m < 12 else (y + 1) * 10000 + 101)
    return out


def make_world(n_days=80, codes=("000001", "000002", "000003")):
    rng = np.random.default_rng(1)
    data = {}
    for c in codes:
        ts, rows = [], []
        px = 100.0
        for d in days(n_days):
            for hh in ("09", "10", "11", "12", "13", "14"):
                o = px
                px = px * float(np.exp(rng.normal(0, 0.01)))
                ts.append(d + hh)
                rows.append((o, max(o, px) * 1.003, min(o, px) * 0.997, px, 1000.0))
        a = np.array(rows)
        data[c] = {"t": ts, "o": a[:, 0], "h": a[:, 1], "l": a[:, 2], "c": a[:, 3], "v": a[:, 4]}
    return data


def cut(data, T):
    out = {}
    for c, b in data.items():
        k = sum(1 for t in b["t"] if t <= T)
        out[c] = {"t": b["t"][:k], **{x: b[x][:k] for x in "ohlcv"}}
    return out


def fair(c, b):          # 봉까지의 값만: 종가가 5봉 전보다 1% 넘게 높으면
    m = np.zeros(len(b["t"]), bool)
    m[5:] = b["c"][5:] > b["c"][:-5] * 1.01
    return m


def peek(c, b):          # 일부러 다음 봉을 봄
    nxt = np.r_[b["c"][1:], b["c"][-1]]
    return nxt > b["c"] * 1.005


exit8 = lambda c, b, p, k: "all" if k - p["i"] >= 8 else 0
two = lambda c, b, k: 2
PER = (("전체", ("2024010100", "2099010100")),)


def closed(res, T):
    return {(t["code"], t["산 때"], t["판 때"], t["칸"], t["손익"]) for t in res["전체"]["목록"]
            if not t["판 때"].startswith("끝") and t["판 때"] <= T}


class PrefixInvariance(unittest.TestCase):
    def test_fair_rule_same_before_cut_and_peek_rule_differs(self):
        data = make_world()
        cuts = [data["000001"]["t"][k] for k in range(100, 400, 23)]
        for entry, same in ((fair, True), (peek, False)):
            hits = 0
            full = H.simulate(data, entry, exit8, two, periods=PER, seeds=1, slots=4)
            for T in cuts:
                part_data = cut(data, T)
                part = H.simulate(part_data, entry, exit8, two, periods=PER, seeds=1, slots=4)
                sig_full = {c: [bool(v) for v in np.asarray(entry(c, b))[: len(part_data[c]["t"])]] for c, b in data.items()}
                sig_part = {c: [bool(v) for v in np.asarray(entry(c, b))] for c, b in part_data.items()}
                if sig_full != sig_part or closed(full, T) != closed(part, T):
                    hits += 1
            if same:
                self.assertEqual(hits, 0)          # 봉까지의 값만 쓰는 규칙: 어느 자르기에서도 같음
            else:
                self.assertGreater(hits, 0)        # 엿보기 규칙: 검사가 잡아야 함

    def test_swap_rule_same_before_cut(self):
        data = make_world()
        T = data["000001"]["t"][300]
        st = lambda p: p["now"] - p["i"] >= 3
        full = H.simulate(data, fair, exit8, two, periods=PER, seeds=1, slots=2, stale_of=st)
        part = H.simulate(cut(data, T), fair, exit8, two, periods=PER, seeds=1, slots=2, stale_of=st)
        self.assertEqual(closed(full, T), closed(part, T))


class Audit(unittest.TestCase):
    def test_audit_catches_wrong_bar(self):
        asked = {("사기", "x"): 5}
        with self.assertRaises(AssertionError):
            H._audit(asked, ("사기", "x"), 7)
        asked = {("사기", "x"): 6}
        H._audit(asked, ("사기", "x"), 7)

    def test_audit_price_range(self):
        b = {"t": ["2024010109"], "l": np.array([9.0]), "h": np.array([11.0])}
        H._audit_price(b, 0, 10.0, "손절")
        with self.assertRaises(AssertionError):
            H._audit_price(b, 0, 8.0, "손절")


class LoadWorlds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = H.HOME
        H.HOME = Path(self.tmp.name)
        folder = H.HOME / "000001"
        folder.mkdir()
        lines = []
        for d in days(60, 20260801):
            for hh in ("09", "10", "11", "12", "13", "14"):
                lines.append(f"{d}{hh},100,101,99,100,1000")
        (folder / "2026.csv").write_text("\n".join(lines), encoding="utf-8")
        self.env = {k: os.environ.pop(k, None) for k in ("HLAB_CUT", "HLAB_POISON", "HLAB_OPEN_HOLDOUT")}

    def tearDown(self):
        H.HOME = self.old
        for k, v in self.env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        self.tmp.cleanup()

    def test_holdout_locked_unless_opened(self):
        got = H.load()["000001"]["t"]
        self.assertTrue(all(t < H.HOLDOUT for t in got))
        os.environ["HLAB_OPEN_HOLDOUT"] = "1"
        self.assertTrue(any(t >= H.HOLDOUT for t in H.load()["000001"]["t"]))

    def test_cut_drops_later_bars(self):
        os.environ["HLAB_CUT"] = "2026090812"
        got = H.load()["000001"]["t"]
        self.assertEqual(got[-1], "2026090812")
        self.assertEqual(H.day_limit(), "20260908")

    def test_poison_changes_only_later_bars(self):
        base = H.load()["000001"]
        os.environ["HLAB_POISON"] = "2026090812"
        bad = H.load()["000001"]
        k = base["t"].index("2026090812") + 1
        self.assertTrue(np.array_equal(base["c"][:k], bad["c"][:k]))
        self.assertFalse(np.array_equal(base["c"][k:], bad["c"][k:]))


class CalmThreshold(unittest.TestCase):
    def test_future_rows_do_not_move_past_months(self):
        rng = np.random.default_rng(3)
        rows = [{"date": d, "변동성": float(v)} for d, v in zip(np.repeat(days(200), 40), rng.uniform(0, 5, 8000))]
        more = rows + [{"date": "20991231", "변동성": 999.0}] * 5000
        a, b = H.calm_by_month(rows, 0.4), H.calm_by_month(more, 0.4)
        self.assertTrue(a)
        for m, v in a.items():
            self.assertEqual(v, b[m])


if __name__ == "__main__":
    unittest.main()
