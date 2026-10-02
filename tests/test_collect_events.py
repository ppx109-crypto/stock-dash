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
        self.assertIsNone(kind_of("주주총회소집공고"))

    def test_new_kinds_from_probe(self):
        self.assertEqual(kind_of("주식소각결정"), "주식소각")
        self.assertEqual(kind_of("기업설명회(IR)개최(안내공시)"), "기업설명회")
        self.assertEqual(kind_of("주식등의대량보유상황보고서(일반)"), "대량보유")
        self.assertEqual(kind_of("임원ㆍ주요주주특정증권등소유상황보고서"), "임원소유")
        self.assertEqual(kind_of("최대주주등소유주식변동신고서"), "최대주주지분변동")
        self.assertEqual(kind_of("조회공시요구(풍문또는보도)에대한답변(미확정)"), "조회공시")
        self.assertEqual(kind_of("신규시설투자등"), "시설투자")
        self.assertEqual(kind_of("생산중단"), "생산중단")
        self.assertEqual(kind_of("주식매수선택권부여에관한신고"), "주식매수선택권")

    def test_old_kinds_keep_first_match(self):
        self.assertEqual(kind_of("주요사항보고서(자기주식처분결정)"), "자사주처분")
        self.assertEqual(kind_of("최대주주변경"), "최대주주변경")
        self.assertEqual(kind_of("현금ㆍ현물배당결정"), "배당")


if __name__ == "__main__":
    unittest.main()
