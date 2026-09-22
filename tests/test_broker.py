import os
import unittest
from unittest.mock import Mock, patch
from broker_kis import KIS, BrokerError


class BalanceTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'KIS_APP_KEY':'test-key', 'KIS_APP_SECRET':'test-secret', 'KIS_CANO':'12345678', 'KIS_ACNT_PRDT_CD':'01', 'KIS_ENV':'demo'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def row(self, code, qty, value):
        return {'pdno':code, 'prdt_name':'fixture', 'hldg_qty':str(qty), 'pchs_avg_pric':'100', 'prpr':'120', 'evlu_amt':str(value), 'evlu_pfls_amt':'20'}

    def response(self, rows, continuation='', nk=''):
        return Mock(headers={'tr_cont':continuation}), {'rt_cd':'0', 'output1':rows, 'output2':[{'dnca_tot_amt':'1000'}], 'ctx_area_fk100':'f', 'ctx_area_nk100':nk}

    def test_complete_pages_and_zero_positions(self):
        client = KIS()
        with patch.object(client, 'authorize'), patch.object(client, 'request', side_effect=[self.response([self.row('005930',1,100)],'M','next'),self.response([self.row('000660',2,300),self.row('035420',0,0)])]) as request, patch('broker_kis.time.sleep'):
            client.token='test-token'
            snapshot=client.balance()
        self.assertEqual(len(snapshot['positions']),2)
        self.assertEqual(snapshot['positions'][1]['weight'],75)
        self.assertEqual(snapshot['value'],400)
        self.assertEqual(request.call_args.kwargs['headers']['tr_cont'],'N')
        self.assertEqual(request.call_args.kwargs['headers']['tr_id'],'VTTC8434R')

    def test_incomplete_page_is_not_success(self):
        client=KIS();client.token='test-token'
        with patch.object(client,'authorize'),patch.object(client,'request',return_value=self.response([self.row('005930',1,100)],'M','')):
            with self.assertRaises(BrokerError):client.balance()

    def test_broker_error_does_not_echo_response(self):
        client=KIS();client.token='test-token'
        with patch.object(client,'authorize'),patch.object(client,'request',return_value=(Mock(),{'rt_cd':'1','msg1':'test-secret 12345678'})):
            with self.assertRaises(BrokerError) as error:client.balance()
        self.assertNotIn('test-secret',str(error.exception))
        self.assertNotIn('12345678',str(error.exception))

    def test_empty_account(self):
        client=KIS();client.token='test-token'
        with patch.object(client,'authorize'),patch.object(client,'request',return_value=self.response([])):
            result=client.balance()
        self.assertEqual(result['positions'],[])
        self.assertEqual(result['value'],0)


class DailyDetail(unittest.TestCase):
    """일봉에서 거래량까지 받아 오는 길. 종가만으로는 살 수 있었는지 모릅니다."""

    def setUp(self):
        self.env = patch.dict(os.environ, {'KIS_APP_KEY': 'k', 'KIS_APP_SECRET': 's',
                                           'KIS_ENV': 'demo'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def client(self, rows):
        one = KIS(account=False)
        one.token = 'x'
        one.authorize = lambda: None
        one.request = Mock(return_value=(200, {'rt_cd': '0', 'output2': rows}))
        return one

    def row(self, day, close, volume):
        return {'stck_bsop_date': day, 'stck_clpr': str(close),
                'stck_oprc': str(close - 1), 'stck_hgpr': str(close + 2),
                'stck_lwpr': str(close - 3), 'acml_vol': str(volume),
                'acml_tr_pbmn': str(volume * close)}

    def test_plain_call_still_gives_pairs(self):
        """옛 수집기가 그대로 돌아야 합니다."""
        got = self.client([self.row('20200102', 100, 5000)]).daily('005930',
                                                                   '20200101', '20200103')
        self.assertEqual(got, [('20200102', 100.0)])

    def test_detail_brings_the_volume(self):
        got = self.client([self.row('20200102', 100, 5000)]).daily(
            '005930', '20200101', '20200103', detail=True)
        self.assertEqual(got[0][0], '20200102')
        self.assertEqual(got[0][1]['종가'], 100.0)
        self.assertEqual(got[0][1]['거래량'], 5000.0)
        self.assertEqual(got[0][1]['고가'], 102.0)

    def test_detail_keeps_the_days_in_order(self):
        rows = [self.row('20200106', 103, 7000), self.row('20200102', 100, 5000)]
        got = self.client(rows).daily('005930', '20200101', '20200107', detail=True)
        self.assertEqual([day for day, _ in got], ['20200102', '20200106'])

    def test_a_day_without_a_close_is_dropped(self):
        rows = [{'stck_bsop_date': '20200102', 'stck_clpr': '0', 'acml_vol': '10'}]
        self.assertEqual(self.client(rows).daily('005930', '20200101', '20200103',
                                                 detail=True), [])
