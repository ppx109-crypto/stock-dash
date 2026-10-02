import sys,types,unittest
from datetime import date
try:import requests
except ImportError:sys.modules['requests']=types.SimpleNamespace(RequestException=Exception,request=None)
from predash.flow import summarize_flow
from predash.kis import KIS

class FlowTests(unittest.TestCase):
    def test_signed_quantities_and_five_sessions(self):
        rows=[{'stck_bsop_date':f'202609{day:02d}','prsn_ntby_qty':'-2',
               'frgn_ntby_qty':'3','orgn_ntby_qty':'-1'} for day in (29,28,25,24,23,22)]
        result=summarize_flow(rows,date(2026,9,29))
        self.assertEqual(result['daily']['foreign'],3)
        self.assertEqual(result['five_day']['individual'],-10)
        self.assertEqual(result['sessions'],5)
        self.assertEqual(result['history'][0]['date'],'2026-09-22')
        self.assertEqual(result['history'][-1]['cumulative']['foreign'],18)
        self.assertEqual(result['history'][-1]['cumulative']['individual'],-12)
    def test_stale_or_invalid_holds(self):
        self.assertIsNone(summarize_flow([{'stck_bsop_date':'20260901'}],date(2026,9,29)))
    def test_kis_request_contract(self):
        client=KIS.__new__(KIS)
        client.token='token';client.key='key';client.secret='secret';client.authorize=lambda:None
        seen={}
        def call(method,path,**kwargs):
            seen.update({'method':method,'path':path,**kwargs})
            return None,{'rt_cd':'0','output':[]}
        client.call=call
        self.assertIsNone(client.investor_flow('005930'))
        self.assertEqual(seen['headers']['tr_id'],'FHKST01010900')
        self.assertEqual(seen['params']['FID_INPUT_ISCD'],'005930')

if __name__=='__main__':unittest.main()

