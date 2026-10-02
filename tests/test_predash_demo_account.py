import os,sys,types,unittest
from unittest.mock import patch
try:import requests
except ImportError:sys.modules['requests']=types.SimpleNamespace(RequestException=Exception,request=None)
from predash.kis import KIS,account_settings,BrokerError

class DemoAccountTests(unittest.TestCase):
    def test_demo_never_uses_real_keys(self):
        with patch.dict(os.environ,{'KIS_ENV':'real','KIS_APP_KEY':'real','KIS_APP_SECRET':'real',
                                    'KIS_CANO':'12345678','KIS_ACNT_PRDT_CD':'01'},clear=True):
            self.assertEqual(account_settings('demo')['key'],'')
            with self.assertRaises(BrokerError):KIS('demo')
    def test_separate_demo_credentials_select_demo_server(self):
        with patch.dict(os.environ,{'KIS_ENV':'real','KIS_APP_KEY':'real',
                'KIS_DEMO_APP_KEY':'demo','KIS_DEMO_APP_SECRET':'demo-secret',
                'KIS_DEMO_CANO':'87654321','KIS_DEMO_ACNT_PRDT_CD':'01'},clear=True):
            client=KIS('demo')
            self.assertEqual((client.key,client.cano,client.mode),('demo','87654321','demo'))
            self.assertIn('openapivts.',client.base)
    def test_legacy_demo_supported_but_partial_profile_not_mixed(self):
        env={'KIS_ENV':'demo','KIS_APP_KEY':'legacy','KIS_APP_SECRET':'secret',
             'KIS_CANO':'12345678','KIS_ACNT_PRDT_CD':'01'}
        with patch.dict(os.environ,env,clear=True):
            self.assertEqual(KIS('demo').key,'legacy')
            os.environ['KIS_DEMO_APP_KEY']='new'
            with self.assertRaises(BrokerError):KIS('demo')

if __name__=='__main__':unittest.main()

