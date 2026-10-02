import unittest
from datetime import date,timedelta
from predash.macro import relative,parse_vix,benchmark,MacroError
class MacroTests(unittest.TestCase):
    def rows(self,stock_end,market_end):
        dates=[(date(2026,9,30)-timedelta(days=20-i)).strftime('%Y%m%d') for i in range(21)]
        return ([{'srtnCd':'005930','basDt':d,'clpr':stock_end if i==20 else 100} for i,d in enumerate(dates)],
                [{'stck_bsop_date':d,'bstp_nmix_prpr':market_end if i==20 else 100} for i,d in enumerate(dates)])
    def test_twenty_sessions_requires_twenty_one_observations(self):
        s,m=self.rows(106,102);r=relative(s,m,'005930',date(2026,9,30))
        self.assertEqual(r[-1]['status'],'매우 우수')
        self.assertAlmostEqual(r[-1]['multiple'],3)
        self.assertEqual(relative(s,m[1:],'005930',date(2026,9,30))[-1]['status'],'자료 부족')
    def test_down_market_is_not_excellent_when_stock_falls_more(self):
        s,m=self.rows(94,98);r=relative(s,m,'005930',date(2026,9,30))
        self.assertEqual(r[0]['status'],'하락장 상대 약세');self.assertIsNone(r[0]['multiple'])
        s,m=self.rows(103,100.01)
        self.assertIsNone(relative(s,m,'005930',date(2026,9,30))[0]['multiple'])
    def test_missing_trading_observation_and_market_mapping(self):
        s,m=self.rows(106,102);s.pop(10)
        self.assertEqual(relative(s,m,'005930',date(2026,9,30))[-1]['status'],'자료 부족')
        self.assertEqual(benchmark([{'srtnCd':'005930','mrktCtg':'KOSPI'}],'005930'),'코스피')
    def test_vix_threshold_staleness_nan(self):
        text='DATE,CLOSE\n09/29/2026,19\n09/30/2026,30\n'
        self.assertEqual(parse_vix(text,date(2026,9,30))['level'],'높음')
        with self.assertRaises(MacroError):parse_vix(text,date(2026,10,10))
        with self.assertRaises(MacroError):parse_vix(text.replace(',30',',NaN'),date(2026,9,30))

