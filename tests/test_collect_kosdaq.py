"""코스닥 일봉 모으기: 공개 종목 목록에서 주식만 · 스팩 빼고 고르고, 운영 폴더와 섞지 않음."""
import unittest
from pathlib import Path

import collect_kosdaq as K


def line(code, name, group):
    head = code.ljust(9).encode("cp949") + b"KR7" + b"0" * 9 + name.encode("cp949")
    tail = group.encode("cp949") + b" " * 220
    return head + tail


class Master(unittest.TestCase):
    def test_keeps_stocks_only(self):
        raw = b"\n".join([line("247540", "에코프로비엠", "ST"), line("123456", "어떤스팩1호", "ST"),
                          line("229200", "KODEX 코스닥150", "EF"), line("Q12345", "이상한것", "ST")])
        self.assertEqual(K.parse_master(raw), [("247540", "에코프로비엠")])

    def test_separate_folder(self):
        self.assertEqual(K.OUT, Path("kosdaq-data"))
        self.assertNotIn(str(K.OUT), ("price-data", "volume-data"))


if __name__ == "__main__":
    unittest.main()
