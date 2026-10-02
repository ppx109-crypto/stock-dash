import unittest
from datetime import date,datetime
from predash.trades import daily_activity

def fill(day,side,quantity,price,hour=10):
    return {'at':datetime(2026,9,day,hour),'side':side,'quantity':quantity,'price':price,'code':'005930','name':'삼성전자'}

class DailyActivityTest(unittest.TestCase):
    def test_prior_day_purchase_and_today_sell(self):
        result=daily_activity([fill(29,'buy',10,100),fill(30,'sell',5,120)],date(2026,9,30))
        self.assertEqual(result['buy'],0)
        self.assertEqual(result['sell'],600)
        self.assertEqual(result['pnl'],100)
        self.assertAlmostEqual(result['return_pct'],100/600*100)
    def test_unmatched_sell_blocks_profit(self):
        result=daily_activity([fill(30,'sell',5,120)],date(2026,9,30))
        self.assertEqual(result['sell'],600)
        self.assertIsNone(result['pnl'])
        self.assertIsNone(result['return_pct'])
    def test_same_day_loss_uses_two_sided_turnover(self):
        result=daily_activity([fill(30,'buy',10,100),fill(30,'sell',10,90,11)],date(2026,9,30))
        self.assertEqual(result['amount'],1900)
        self.assertEqual(result['pnl'],-100)
        self.assertAlmostEqual(result['return_pct'],-100/1900*100)
    def test_incomplete_and_empty(self):
        result=daily_activity([fill(30,'buy',10,100)],date(2026,9,30),True)
        self.assertIsNone(result['buy']);self.assertIsNone(result['pnl'])
        empty=daily_activity([],date(2026,9,30))
        self.assertEqual(empty['amount'],0);self.assertIsNone(empty['return_pct'])
    def test_ambiguous_same_time_blocks_profit(self):
        result=daily_activity([fill(30,'buy',10,100),fill(30,'sell',10,110)],date(2026,9,30))
        self.assertIsNone(result['pnl'])

    def test_provider_amount_used_for_turnover(self):
        item=fill(30,'buy',3,100.3);item['amount']=301
        self.assertEqual(daily_activity([item],date(2026,9,30))['buy'],301)

