import unittest

from collect_events import kind_of


class KindOf(unittest.TestCase):
    def test_provisional_earnings_is_its_own_kind(self):
        self.assertEqual(kind_of("연결재무제표기준영업(잠정)실적(공정공시)"), "잠정실적")
        self.assertEqual(kind_of("영업(잠정)실적(공정공시)"), "잠정실적")
        self.assertEqual(kind_of("[기재정정]연결재무제표기준영업(잠정)실적(공정공시)"), "잠정실적")

    def test_other_earnings_titles_unchanged(self):
        self.assertEqual(kind_of("매출액또는손익구조30%(대규모법인은15%)이상변경"), "실적공시")
        self.assertEqual(kind_of("결산실적공시예고(안내공시)"), "실적공시")
        self.assertEqual(kind_of("영업실적등에대한전망(공정공시)"), "실적공시")
        self.assertIsNone(kind_of("임원ㆍ주요주주특정증권등소유상황보고서"))


if __name__ == "__main__":
    unittest.main()
