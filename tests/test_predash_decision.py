import unittest,json
from datetime import date,timedelta
from predash.decision import comparison,brief,export_review,EvidenceError

def data():
    today=date(2026,9,30)
    dates=[(today-timedelta(days=i)).strftime('%Y%m%d') for i in range(20)]
    stock=[{'srtnCd':'005930','basDt':d,'clpr':str(100+i)} for i,d in enumerate(dates)]
    market=[{'stck_bsop_date':d,'bstp_nmix_prpr':str(1000+i*2)} for i,d in enumerate(dates)]
    return today,stock,market

class DecisionEvidenceTests(unittest.TestCase):
    def test_same_base_and_only_shared_dates(self):
        today,stock,market=data();market=market[2:]
        result=comparison(stock,market,'005930',today)
        self.assertEqual(len(result),18)
        self.assertEqual(result[0]['stock'],100)
        self.assertEqual(result[0]['market'],100)
        self.assertEqual(result[-1]['date'],'2026-09-28')
    def test_insufficient_and_conflicting_history_rejected(self):
        today,stock,market=data()
        with self.assertRaises(EvidenceError):comparison(stock[:5],market,'005930',today)
        stock.append({**stock[0],'clpr':'999'})
        with self.assertRaises(EvidenceError):comparison(stock,market,'005930',today)
    def test_missing_financials_do_not_invent_score(self):
        item={'code':'005930','name':'기업','fetched':'2026-09-30','metrics':None,'lamp':None,'flow':None}
        report=json.loads(export_review(item,[],{'sector':'기록'},'코스피'))
        self.assertIsNone(report['investment_score'])
        self.assertIn('자동 검증 아님',report['industry_note']['verification'])
        self.assertTrue(any('보류' in line for line in brief(item)))
    def test_previous_profit_missing_not_reported_as_growth(self):
        item={'metrics':{'year':2026,'quarter':2,'revenue':100,'profit':-10,'growth_pct':None}}
        self.assertTrue(any('조건 미충족' in line for line in brief(item)))

