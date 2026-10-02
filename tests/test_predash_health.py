import unittest
from datetime import date
from predash.health import status,events
class HealthTests(unittest.TestCase):
    def test_cost_based_rate_and_threshold(self):
        p={'average_cost':100,'quantity':2,'pnl':-10,'weight':40}
        s=status(p,None,date(2026,9,30))
        self.assertEqual(s['rate'],-5)
        self.assertTrue(s['warning'])
        self.assertIsNone(status(dict(p,average_cost=0),None,date(2026,9,30))['rate'])
    def test_negative_base_turnaround_not_fake_growth(self):
        r={'metrics':{'year':2026,'quarter':2,'prior_profit':-10,'profit':20}}
        s=status({},r,date(2026,9,30))
        self.assertEqual(s['earnings'],'흑자 전환')
        self.assertIsNone(s['growth'])
        r.pop('metrics')
        self.assertEqual(status({},r,date(2026,9,30))['earnings'],'최근 동기 실적 보류')
    def test_disclosure_title_is_not_buy_direction_and_future_excluded(self):
        r={'disclosures':[{'date':'20260930','title':'임원 주요주주 특정증권 소유상황보고서'},
            {'date':'20261001','title':'유상증자결정'}, {'date':'20260920','title':'[정정] 단일판매 공급계약 해지'}]}
        e=events(r,date(2026,9,30))
        self.assertEqual(len(e),2)
        self.assertEqual(e[0]['kind'],'ownership')
        self.assertTrue(e[1]['amended'])

