import sys,types,unittest
try:import requests
except ImportError:sys.modules['requests']=types.SimpleNamespace(RequestException=Exception,request=None)
from predash.kis import KIS,BrokerError

class KISErrorRules(unittest.TestCase):
    def test_diagnostic_code_does_not_echo_message(self):
        error=KIS.result_error({'msg_cd':'EGW00123','msg1':'계좌번호 12345678 및 비밀'},'잔고 조회 실패')
        self.assertIn('EGW00123',str(error))
        self.assertNotIn('12345678',str(error))
    def test_malformed_code_is_hidden(self):
        error=KIS.result_error({'msg_cd':'account/12345678'},'인증 실패')
        self.assertIn('미확인',str(error))
        self.assertNotIn('12345678',str(error))
    def test_account_mismatch_has_specific_guidance(self):
        error=KIS.result_error({'msg_cd':'OPSQ2000','msg1':'account 12345678'},'잔고 조회 실패')
        self.assertIn('계좌번호 검사 실패',str(error))
        self.assertIn('KIS_ENV',str(error))
        self.assertNotIn('12345678',str(error))
if __name__=='__main__':unittest.main()

