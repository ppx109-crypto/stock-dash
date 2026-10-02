import sys,types,unittest
from datetime import date,timedelta
from predash.market import index_lamp,stock_lamp,MarketDataError

class MarketLampRules(unittest.TestCase):
    def rows(self,latest,values):
        return [{'stck_bsop_date':(latest-timedelta(days=i)).strftime('%Y%m%d'),
                 'bstp_nmix_prpr':str(value)} for i,value in enumerate(values)]
    def test_three_states_and_crossed_averages(self):
        today=date(2026,9,28)
        self.assertEqual(index_lamp(self.rows(today,[130]+[120]*9+[100]*10),'코스피',today)['state'],'상승 구간')
        self.assertEqual(index_lamp(self.rows(today,[70]+[80]*9+[100]*10),'코스피',today)['state'],'하락 구간')
        self.assertEqual(index_lamp(self.rows(today,[100]+[120]*9+[80]*10),'코스피',today)['state'],'횡보 구간')
        self.assertEqual(index_lamp(self.rows(today,[100]+[80]*9+[120]*10),'코스피',today)['state'],'횡보 구간')
    def test_stale_or_insufficient_is_held(self):
        today=date(2026,9,28)
        self.assertIsNone(index_lamp(self.rows(today,[100]*19),'코스피',today))
        self.assertIsNone(index_lamp(self.rows(today-timedelta(days=6),[100]*20),'코스피',today))
    def test_stock_uses_only_exact_code_and_same_lamp_rule(self):
        today=date(2026,9,28)
        rows=[{'basDt':r['stck_bsop_date'],'clpr':r['bstp_nmix_prpr'],'srtnCd':'005930'}
              for r in self.rows(today,[130]+[120]*9+[100]*10)]
        rows.append({'basDt':'20260928','clpr':'99999','srtnCd':'000660'})
        result=stock_lamp(rows,'005930',today)
        self.assertEqual((result['state'],result['close'],result['observations']),('상승 구간',130,20))
        self.assertIsNone(stock_lamp(rows,'111111',today))
    def test_future_or_conflicting_duplicate_rejected(self):
        today=date(2026,9,28)
        with self.assertRaises(MarketDataError):index_lamp(self.rows(today+timedelta(days=1),[100]*20),'코스피',today)
        rows=self.rows(today,[100]*20)
        with self.assertRaises(MarketDataError):index_lamp(rows+[dict(rows[0],bstp_nmix_prpr='101')],'코스피',today)
    def test_kis_contract(self):
        try:import requests
        except ImportError:sys.modules['requests']=types.SimpleNamespace()
        from predash.kis import KIS
        client=KIS.__new__(KIS)
        client.key='key';client.secret='secret';client.token='token';client.authorize=lambda:None
        calls=[]
        def call(method,path,**kw):
            calls.append((method,path,kw));return None,{'rt_cd':'0','output2':[]}
        client.call=call
        self.assertEqual(client.index_bars('0001',date(2026,9,28)),[])
        self.assertEqual(calls[0][1],'/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice')
        self.assertEqual(calls[0][2]['headers']['tr_id'],'FHKUP03500100')
        self.assertEqual(calls[0][2]['params']['FID_COND_MRKT_DIV_CODE'],'U')
if __name__=='__main__':unittest.main()

class PriceTrendTests(unittest.TestCase):
    def test_trailing_averages_and_conflicting_duplicates(self):
        from predash.market import price_trend,MarketDataError
        from datetime import date
        rows=[{'srtnCd':'005930','basDt':f'202609{i:02d}','clpr':str(i)} for i in range(1,21)]
        chart=price_trend(rows,'005930',date(2026,9,20))
        self.assertIsNone(chart[0]['20일선'])
        self.assertEqual(chart[-1]['20일선'],10.5)
        self.assertEqual(chart[-1]['10일선'],15.5)
        with self.assertRaises(MarketDataError):price_trend(rows+[dict(rows[-1],clpr='25')],'005930',date(2026,9,20))

