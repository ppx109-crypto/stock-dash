import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import idle_signal as S


def flat(n=60, v=100.0):
    return np.full(n, v)


class IdleSignalTest(unittest.TestCase):
    def base(self):
        return {c: flat() for c in ("069500", "229200", "138230") + S.ROT}

    def test_engine_off_when_daily_busy(self):
        out = S.decide(self.base(), breadth=30, used=0.5)
        self.assertFalse(out["엔진"])
        self.assertEqual(out["돌리기"], {})

    def test_dip_first(self):
        px = self.base()
        px["069500"] = np.r_[flat(55), [100, 99, 97, 96, 94]]       # 5일 −6%
        out = S.decide(px, breadth=30, used=0.0)
        self.assertTrue(out["급락"])
        self.assertEqual(out["돌리기"], {})

    def test_dip_needs_weak_breadth(self):
        px = self.base()
        px["069500"] = np.r_[flat(55), [100, 99, 97, 96, 94]]
        self.assertFalse(S.decide(px, breadth=60, used=0.0)["급락"])

    def test_dollar_in_downtrend(self):
        px = self.base()
        px["069500"] = np.r_[flat(59), [98.0]]                        # 20일선 아래 · 5일 −2%(급락 아님)
        px["138230"] = np.r_[flat(40), np.linspace(100, 103, 20)]   # 20일 +3%
        out = S.decide(px, breadth=40, used=0.1)
        self.assertTrue(out["하락추세"])

    def test_rotation_top_two_positive(self):
        px = self.base()
        for c, g in zip(S.ROT, (0.05, 0.02, -0.01, 0.03)):
            px[c] = np.r_[flat(40), np.linspace(100, 100 * (1 + g), 20)]
        out = S.decide(px, breadth=80, used=0.0)
        self.assertEqual(set(out["돌리기"]), {"133690", "148070"})

    def test_kosdaq_inverse(self):
        px = self.base()
        px["229200"] = np.r_[flat(50), np.linspace(100, 111, 10)]
        self.assertTrue(S.decide(px, breadth=80, used=0.9)["코스닥인버스"])
        px["229200"] = np.r_[flat(50), np.linspace(100, 109.7, 10)]
        self.assertFalse(S.decide(px, breadth=80, used=0.9)["코스닥인버스"])
        self.assertTrue(S.decide(px, breadth=80, used=0.9, at_1515=True)["코스닥인버스"])


    def test_mood_candidate(self):
        self.assertTrue(S.decide(self.base(), breadth=80, used=0.0, mood=75)["분위기사기"])
        self.assertFalse(S.decide(self.base(), breadth=80, used=0.0, mood=60)["분위기사기"])
        self.assertFalse(S.decide(self.base(), breadth=80, used=0.5, mood=90)["분위기사기"])
        self.assertFalse(S.decide(self.base(), breadth=80, used=0.0)["분위기사기"])


if __name__ == "__main__":
    unittest.main()
