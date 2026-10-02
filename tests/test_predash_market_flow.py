import os,sys,types,unittest
from datetime import date,timedelta
from unittest.mock import patch
try:import requests
except ImportError:sys.modules['requests']=types.SimpleNamespace(RequestException=Exception,request=None)
from predash.market import market_flow,index_lamp,MarketDataError
from predash.kis import KIS

def row(day='20260930',personal='100',foreign='-80',institution='-20'):
    return {'stck_bsop_date':day,'prsn_ntby_tr_pbmn':personal,'frgn_ntby_tr_pbmn':foreign,'orgn_ntby_tr_pbmn':institution}

class MarketFlowTests(unittest.TestCase):
    def test_signed_values_and_latest_date(self):
        result=market_flow([row('20260929'),row()],date(2026,9,30))
        self.assertEqual(result['date'],'2026-09-30')
        self.assertEqual(result['net'],{'individual':100,'foreign':-80,'institution':-20})
        self.assertEqual(result['unit'],'source')
    def test_missing_values_never_become_zero(self):
        data=row();del data['orgn_ntby_tr_pbmn']
        with self.assertRaises(MarketDataError):market_flow([data],date(2026,9,30))
    def test_future_stale_and_conflicting_rows_rejected(self):
        for rows in ([row('20261001')],[row('20260901')],[row(),row(personal='99')]):
            with self.assertRaises(MarketDataError):market_flow(rows,date(2026,9,30))
    def test_change_uses_previous_available_trading_session(self):
        end=date(2026,9,30)
        rows=[{'stck_bsop_date':(end-timedelta(days=i)).strftime('%Y%m%d'),'bstp_nmix_prpr':100-i} for i in range(20)]
        result=index_lamp(rows,'코스피',end)
        self.assertEqual(result['change'],1)
        self.assertAlmostEqual(result['change_pct'],1/99*100)
        rows[0]['bstp_nmix_prpr']=90
        self.assertEqual(index_lamp(rows,'코스피',end)['change'],-9)
    def test_market_code_and_date_request(self):
        env={'KIS_ENV':'real','KIS_APP_KEY':'test','KIS_APP_SECRET':'test','KIS_CANO':'12345678','KIS_ACNT_PRDT_CD':'01'}
        with patch.dict(os.environ,env,clear=True):client=KIS('real')
        client.token='test-token'
        with patch.object(client,'authorize'),patch.object(client,'call',return_value=(None,{'rt_cd':'0','output':[row()]})) as call:
            client.market_flow('1001',date(2026,9,30))
            args=call.call_args.kwargs
            self.assertEqual(args['headers']['tr_id'],'FHPTJ04040000')
            self.assertEqual(args['params']['FID_INPUT_ISCD_1'],'KSQ')
            self.assertEqual(args['params']['FID_INPUT_ISCD_2'],'1001')
            self.assertEqual(args['params']['FID_INPUT_DATE_1'],'20260930')
            self.assertNotIn('CANO',args['params'])

