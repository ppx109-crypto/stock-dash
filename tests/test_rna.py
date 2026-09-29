import unittest

import numpy as np

import rna


class States(unittest.TestCase):
    def test_rising_line_is_fully_ordered(self):
        closes = np.linspace(100, 300, 400)
        s = rna.states(closes, (5, 20, 60))
        self.assertEqual(s["배열"][-1], 2)
        self.assertEqual(s["정배열"][-1], 1)
        self.assertGreater(s["정배열지속"][-1], 100)
        self.assertGreater(s["기울기5"][-1], 0)
        self.assertGreater(s["이격60"][-1], s["이격5"][-1])

    def test_no_lookahead(self):
        closes = np.r_[np.linspace(100, 200, 300), np.linspace(200, 100, 100)]
        a = rna.states(closes, (5, 20))
        b = rna.states(closes[:300], (5, 20))
        for k in ("배열", "이격20", "이격속도20_5", "가속도20", "이격밴드20"):
            np.testing.assert_allclose(a[k][:300], b[k], equal_nan=True)


if __name__ == "__main__":
    unittest.main()
