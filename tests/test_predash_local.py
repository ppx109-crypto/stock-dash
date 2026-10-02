import unittest
from datetime import date

import predash.local as L


class LocalFallback(unittest.TestCase):
    def test_price_rows_look_like_public_data(self):
        rows = L.price_rows('005930', date(2026, 10, 2))
        self.assertGreater(len(rows), 20)
        self.assertEqual(set(rows[-1]) >= {'srtnCd', 'basDt', 'clpr', 'itmsNm'}, True)
        self.assertEqual(rows[-1]['srtnCd'], '005930')

    def test_flow_and_index(self):
        self.assertIsNotNone(L.investor_flow('005930', date(2026, 10, 2)))
        self.assertGreater(len(L.index_rows('0001')), 20)

    def test_search_and_price(self):
        self.assertTrue(any(h['code'] == '005930' for h in L.search('삼성전자')))
        price, day, name = L.last_price('005930')
        self.assertTrue(price > 0 and len(day) == 8 and name)

    def test_stale_price_data_is_extended_by_investor_closes(self):
        rows = L.price_rows('003550', date(2026, 10, 2))   # LG: price-data는 09-22에서 멈춤
        self.assertGreaterEqual(rows[-1]['basDt'], '20260930')

    def test_metrics_from_repo_quarter_data(self):
        m = L.metrics('005930', date(2026, 10, 2))
        self.assertTrue(m and m['revenue'] > 0 and m['quarter'] in (1, 2, 3, 4))
        self.assertIn('standalone', m)
        self.assertIsNone(L.metrics('005930', date(2015, 1, 2)))

    def test_bad_code(self):
        self.assertEqual(L.price_rows('ABC', date(2026, 10, 2)), [])
        self.assertIsNone(L.last_price('999999'))


if __name__ == '__main__':
    unittest.main()
