from datetime import datetime
import unittest
from predash.trades import normalize_kis,closed_trades,TradeDataError

class TradeRules(unittest.TestCase):
    def row(self,day,side,qty,price,order):
        return {'ord_dt':day,'ord_tmd':'101500','sll_buy_dvsn_cd':side,'pdno':'005930','prdt_name':'삼성전자',
                'tot_ccld_qty':str(qty),'avg_prvs':str(price),'odno':order,'cncl_yn':'N'}
    def test_fifo_partial_and_unmatched_opening(self):
        rows=[self.row('20260901','02',10,100,'1'),self.row('20260902','02',5,120,'2'),self.row('20260903','01',12,110,'3'),self.row('20260904','01',5,90,'4')]
        result=closed_trades(normalize_kis(rows))
        self.assertEqual([x['quantity'] for x in result['closed']],[10,2,3])
        self.assertEqual([x['gross_pnl'] for x in result['closed']],[100,-20,-90])
        self.assertEqual(result['unmatched_sells'][0]['quantity'],2)
    def test_no_duplicate_or_cancelled_fill(self):
        row=self.row('20260901','02',1,100,'1')
        self.assertEqual(len(normalize_kis([row,row,{**row,'cncl_yn':'Y'}])),1)
    def test_unknown_side_is_not_guessed(self):
        with self.assertRaises(TradeDataError):normalize_kis([self.row('20260901','03',1,100,'1')])
    def test_provider_prefix_and_alphanumeric_codes(self):
        row=self.row('20260901','02',1,100,'1')
        self.assertEqual(normalize_kis([{**row,'pdno':' A005930 '}])[0]['code'],'005930')
        self.assertEqual(normalize_kis([{**row,'pdno':'00279K'}])[0]['code'],'00279K')
        self.assertEqual(normalize_kis([{**row,'pdno':'Q500001'}])[0]['code'],'Q500001')
    def test_display_skip_is_explicit_and_analysis_stays_strict(self):
        row=self.row('20260901','02',1,100,'1')
        invalid={**row,'pdno':''};skipped=[]
        self.assertEqual(len(normalize_kis([invalid,row],skipped=skipped)),1)
        self.assertEqual(skipped[0]['row'],1)
        with self.assertRaises(TradeDataError):normalize_kis([invalid,row])
    def test_conflicting_order_aggregate_is_rejected(self):
        with self.assertRaises(TradeDataError):
            normalize_kis([self.row('20260901','02',1,100,'1'),self.row('20260901','02',2,100,'1')])
if __name__=='__main__':unittest.main()

class KISHistoryContract(unittest.TestCase):
    def test_recent_history_is_read_only_and_complete(self):
        import sys, types
        try: import requests  # noqa: F401
        except ImportError: sys.modules['requests']=types.SimpleNamespace()
        from predash.kis import KIS
        class Response:
            headers={'tr_cont':''}
        client=KIS.__new__(KIS)
        client.mode='demo';client.cano='12345678';client.product='01';client.key='test';client.secret='test';client.token='token'
        client.authorize=lambda:None
        calls=[]
        def read(method,path,**kwargs):
            calls.append((method,path,kwargs))
            return Response(),{'rt_cd':'0','output1':[]}
        client.call=read
        got=client.fills(7)
        self.assertEqual(got['rows'],[])
        self.assertEqual(calls[0][0],'GET')
        self.assertEqual(calls[0][1],'/uapi/domestic-stock/v1/trading/inquire-daily-ccld')
        self.assertEqual(calls[0][2]['headers']['tr_id'],'VTTC0081R')
        self.assertEqual(calls[0][2]['params']['CCLD_DVSN'],'01')

