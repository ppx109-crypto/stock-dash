import sys,types,unittest
try:import requests
except ImportError:sys.modules['requests']=types.SimpleNamespace(RequestException=Exception,request=None)
from predash.customs import parse_rows,summarize,month_index,CustomsError

def xml(hs='8504',country='US',amount='150822',month='2026.08'):
    return f'<response><header><resultCode>00</resultCode></header><body><items><item><year>{month}</year><hsCd>{hs}</hsCd><statCd>{country}</statCd><expDlr>{amount}</expDlr></item></items></body></response>'.encode()

class ExportSignals(unittest.TestCase):
    def test_official_usd_value_retained(self):
        idx=month_index('202608');result=parse_rows(xml(),'8504','US',idx,idx)
        self.assertEqual(result[idx],150822)
    def test_cross_country_and_wrong_code_rejected(self):
        idx=month_index('202608')
        for content in [xml(country='CN'),xml(hs='8505'),xml(amount='nan')]:
            with self.assertRaises(CustomsError):parse_rows(content,'8504','US',idx,idx)
    def test_missing_month_not_filled_and_three_month_average(self):
        idx=month_index('202608');result=summarize({idx-12:100,idx-2:200,idx-1:300,idx:400})
        self.assertEqual(len(result),4)
        self.assertEqual(result[-1]['yoy_pct'],300)
        self.assertEqual(result[-1]['ma3_usd'],300)
        result=summarize({idx-2:200,idx:400})
        self.assertIsNone(result[-1]['ma3_usd'])
        self.assertIsNone(result[-1]['yoy_pct'])
    def test_pagination_and_unsafe_document_rejected(self):
        idx=month_index('202608')
        content=xml().replace(b'<body>',b'<body><totalCount>2</totalCount>')
        with self.assertRaises(CustomsError):parse_rows(content,'8504','US',idx,idx)
        with self.assertRaises(CustomsError):parse_rows(b'<!DOCTYPE x>'+xml(),'8504','US',idx,idx)

