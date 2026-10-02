import unittest
from datetime import datetime, timedelta
from predash.trades import purchase_range, TradeDataError

class PriceRangeRules(unittest.TestCase):
    def setUp(self):
        self.fill={'side':'buy','at':datetime(2026,9,28,10),'code':'005930','name':'삼성전자','price':180}
        self.rows=[{'stck_bsop_date':(datetime(2026,9,27)-timedelta(days=i)).strftime('%Y%m%d'),
                    'stck_hgpr':'200','stck_lwpr':'100'} for i in range(20)]
    def test_position_and_prior_only(self):
        result=purchase_range(self.fill,self.rows)
        self.assertTrue(result['upper_20'])
        self.assertEqual(result['position_pct'],80)
        self.assertEqual(result['to'],'2026-09-27')
    def test_future_bar_rejected(self):
        with self.assertRaises(TradeDataError):
            purchase_range(self.fill,self.rows+[{'stck_bsop_date':'20260928','stck_hgpr':'200','stck_lwpr':'100'}])
    def test_missing_data_held(self):
        self.assertIsNone(purchase_range(self.fill,self.rows[:19]))
    def test_duplicate_rejected(self):
        with self.assertRaises(TradeDataError):purchase_range(self.fill,self.rows+[self.rows[0]])
    def test_discontinuity_held(self):
        self.rows[0]['stck_hgpr']='400'
        self.assertIsNone(purchase_range(self.fill,self.rows))
    def test_kis_endpoint_previous_day(self):
        import sys,types
        try:import requests  # noqa
        except ImportError:sys.modules['requests']=types.SimpleNamespace()
        from predash.kis import KIS
        client=KIS.__new__(KIS)
        client.key='key';client.secret='secret';client.token='token';client.authorize=lambda:None
        calls=[]
        def call(method,path,**kw):
            calls.append((method,path,kw));return None,{'rt_cd':'0','output2':self.rows}
        client.call=call
        self.assertEqual(client.daily_bars('005930',self.fill['at'].date()),self.rows)
        self.assertEqual(calls[0][1],'/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice')
        self.assertEqual(calls[0][2]['params']['FID_INPUT_DATE_2'],'20260927')
        self.assertEqual(calls[0][2]['params']['FID_ORG_ADJ_PRC'],'1')
if __name__=='__main__':unittest.main()

