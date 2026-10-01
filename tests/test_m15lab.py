"""15분봉 엔진(m15lab): 읽기 · 잠금 · 잘라내기 · 더럽히기 · hlab 계좌 모의가 12자리 시각을 받는지(인공 자료)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import m15lab as M


def write_days(home, code, days, slots=26, start=100.0, drift=0.002):
    folder = Path(home) / code
    folder.mkdir(parents=True, exist_ok=True)
    lines, price = [], start
    for d in days:
        for k in range(slots):
            h, m = divmod(9 * 60 + 15 * k, 60)
            o = price
            price *= 1 + drift * np.sin(k + len(lines) / 7.0) + 0.0005
            hi, lo = max(o, price) * 1.001, min(o, price) * 0.999
            lines.append(f"{d}{h:02d}{m:02d},{o:.2f},{hi:.2f},{lo:.2f},{price:.2f},1000")
    (folder / f"{days[0][:4]}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


DAYS = [f"2026{m:02d}{d:02d}" for m in (1, 2, 3, 4, 5) for d in range(1, 21)]


class Load(unittest.TestCase):
    def test_reads_12_digit_bars_and_drops_short_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_days(tmp, "000001", DAYS)
            write_days(tmp, "000002", ["20260101"], slots=5)          # 반쪽 날뿐 → 빠짐
            got = M.load(home=tmp)
            self.assertEqual(set(got), {"000001"})
            b = got["000001"]
            self.assertEqual(b["t"][0], "202601010900")
            self.assertEqual(b["t"][25], "202601011515")
            self.assertEqual(len(b["t"]), 26 * len(DAYS))

    def test_cut_and_poison_follow_hlab_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_days(tmp, "000001", DAYS)
            full = M.load(home=tmp)["000001"]
            with mock.patch.dict(os.environ, {"HLAB_CUT": "2026030214"}):
                cut = M.load(home=tmp)["000001"]
            self.assertEqual(cut["t"][-1], "202603021345")              # 14시부터 없음
            n = len(cut["t"])
            self.assertTrue(np.array_equal(cut["c"], full["c"][:n]))
            with mock.patch.dict(os.environ, {"HLAB_POISON": "2026030214"}):
                bad = M.load(home=tmp)["000001"]
            self.assertTrue(np.array_equal(bad["c"][:n], full["c"][:n]))   # 앞은 그대로
            self.assertFalse(np.array_equal(bad["c"][n:], full["c"][n:]))  # 뒤만 엉뚱하게

    def test_holdout_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_days(tmp, "000001", DAYS + ["20260930", "20261001"])
            got = M.load(home=tmp)["000001"]
            self.assertLess(got["t"][-1], "202609300000")


class Simulate(unittest.TestCase):
    def test_hlab_account_runs_on_15min_and_audits(self):
        with tempfile.TemporaryDirectory() as tmp:
            for code in ("000001", "000002"):
                write_days(tmp, code, DAYS)
            data = M.load(home=tmp)
            entry = lambda c, b: M.at(b, "1000")                       # 10:00 봉이 닫히면 → 10:15 시가에 삼
            exit_rule = lambda c, b, p, k: "all" if k - p["i"] >= 8 else 0
            res = M.simulate(data, entry, exit_rule, lambda c, b, k: 2, seeds=2,
                             periods=(("앞", ("202601010000", "202603010000")), ("뒤", ("202603010000", "202606010000"))))
            self.assertTrue(res["앞"] and res["뒤"])
            buys = {t["산 때"][8:] for t in res["앞"]["목록"]}
            self.assertEqual(buys, {"1015"})                           # 다음 봉 시가 체결


class Coverage(unittest.TestCase):
    def test_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_days(tmp, "000001", DAYS[:10])
            write_days(tmp, "000002", DAYS[:4])
            n, mid, first, last = M.coverage(tmp)
            self.assertEqual((n, first, last), (2, DAYS[0], DAYS[9]))


if __name__ == "__main__":
    unittest.main()


class Hours(unittest.TestCase):
    def test_to_hours_merges_quarters_and_closing(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_days(tmp, "000001", DAYS[:3])
            b = M.load(home=tmp, min_bars=10)["000001"]
            h = M.to_hours({"000001": b})["000001"]
            self.assertEqual([t[8:] for t in h["t"][:6]], ["0900", "1000", "1100", "1200", "1300", "1400"])
            self.assertEqual(len(h["t"]), 6 * 3)
            self.assertAlmostEqual(h["o"][0], b["o"][0])
            self.assertAlmostEqual(h["c"][0], b["c"][3])                 # 09:45 칸 종가
            self.assertAlmostEqual(h["c"][5], b["c"][25])                # 14시 봉에 15:00 · 15:15 칸까지
            self.assertAlmostEqual(h["h"][0], max(b["h"][:4]))
