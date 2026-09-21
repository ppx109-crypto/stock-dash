"""증권사 투자의견·목표가 읽기. 실제 서버 대신 정해 둔 응답으로 확인합니다."""
import os
import unittest
from unittest.mock import patch

import broker_kis
from broker_kis import KIS, BrokerError


class FakeResponse:
    headers = {}


class Stub(KIS):
    """인증과 통신을 대신하는 껍데기."""

    def __init__(self, payload, status="0"):
        os.environ.update({"KIS_APP_KEY": "k", "KIS_APP_SECRET": "s",
                           "KIS_CANO": "12345678", "KIS_ACNT_PRDT_CD": "01",
                           "KIS_ENV": "real"})
        super().__init__()
        self.payload = payload
        self.status = status
        self.sent = None

    def authorize(self):
        self.token = "test-token"

    def request(self, method, path, **kwargs):
        self.sent = {"method": method, "path": path, **kwargs}
        return FakeResponse(), {"rt_cd": self.status, "output": self.payload, "msg1": "거부"}


ROWS = [
    {"stck_bsop_date": "20260910", "invt_opnn": "매수", "rgbf_invt_opnn": "매수",
     "hts_goal_prc": "420000", "mbcr_name": "가증권"},
    {"stck_bsop_date": "20260915", "invt_opnn": "중립", "rgbf_invt_opnn": "매수",
     "hts_goal_prc": "380,000", "mbcr_name": "나증권"},
    {"stck_bsop_date": "20260901", "invt_opnn": "매수", "rgbf_invt_opnn": "",
     "hts_goal_prc": "0", "mbcr_name": "다증권"},
]


class Opinions(unittest.TestCase):
    def tearDown(self):
        for key in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_CANO", "KIS_ACNT_PRDT_CD", "KIS_ENV"):
            os.environ.pop(key, None)

    def test_newest_opinion_comes_first(self):
        found = Stub(ROWS).opinions("005930")
        self.assertEqual([r["date"] for r in found], ["20260915", "20260910"])

    def test_a_row_without_a_target_price_is_left_out(self):
        found = Stub(ROWS).opinions("005930")
        self.assertNotIn("다증권", [r["member"] for r in found])

    def test_a_target_with_commas_is_read_as_a_number(self):
        found = Stub(ROWS).opinions("005930")
        self.assertEqual(found[0]["target"], 380000.0)

    def test_the_right_api_and_period_are_asked_for(self):
        client = Stub(ROWS)
        client.opinions("005930", days=90)
        self.assertIn("invest-opinion", client.sent["path"])
        self.assertEqual(client.sent["headers"]["tr_id"], "FHKST663300C0")
        params = client.sent["params"]
        self.assertEqual(params["FID_INPUT_ISCD"], "005930")
        self.assertLess(params["FID_INPUT_DATE_1"], params["FID_INPUT_DATE_2"])

    def test_a_refusal_is_reported_not_swallowed(self):
        with self.assertRaises(BrokerError):
            Stub(ROWS, status="1").opinions("005930")

    def test_an_empty_answer_is_simply_empty(self):
        self.assertEqual(Stub([]).opinions("005930"), [])
        self.assertEqual(Stub(None).opinions("005930"), [])

    def test_a_bad_code_is_refused_before_calling(self):
        with self.assertRaises(BrokerError):
            Stub(ROWS).opinions("12")


QUOTE = {"stck_prpr": "71,200", "prdy_vrss": "1500", "prdy_vrss_sign": "5",
         "prdy_ctrt": "-2.06", "hts_kor_isnm": "삼성전자"}


class Quote(unittest.TestCase):
    def tearDown(self):
        for key in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_CANO", "KIS_ACNT_PRDT_CD", "KIS_ENV"):
            os.environ.pop(key, None)

    def test_a_fall_comes_back_negative(self):
        # 등락폭은 늘 양수로 오고 방향은 부호 항목에 따로 옵니다.
        found = Stub(QUOTE).quote("005930")
        self.assertEqual(found["price"], 71200.0)
        self.assertEqual(found["change"], -1500.0)
        self.assertEqual(found["rate"], -2.06)

    def test_a_rise_keeps_its_sign(self):
        found = Stub({**QUOTE, "prdy_vrss_sign": "2"}).quote("005930")
        self.assertEqual(found["change"], 1500.0)

    def test_the_right_api_is_asked_for(self):
        client = Stub(QUOTE)
        client.quote("005930")
        self.assertIn("inquire-price", client.sent["path"])
        self.assertEqual(client.sent["headers"]["tr_id"], "FHKST01010100")

    def test_a_refusal_is_reported(self):
        with self.assertRaises(BrokerError):
            Stub(QUOTE, status="1").quote("005930")

    def test_a_zero_price_is_not_used(self):
        with self.assertRaises(BrokerError):
            Stub({**QUOTE, "stck_prpr": "0"}).quote("005930")


class WithoutAnAccount(unittest.TestCase):
    def tearDown(self):
        for key in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_CANO", "KIS_ACNT_PRDT_CD", "KIS_ENV"):
            os.environ.pop(key, None)

    def test_market_data_needs_no_account_number(self):
        # 시세와 투자의견은 계좌 없이 읽습니다. 계좌를 요구하면 키만 넣은 사람이 막힙니다.
        os.environ.update({"KIS_APP_KEY": "k", "KIS_APP_SECRET": "s", "KIS_ENV": "real"})
        KIS(account=False)

    def test_a_balance_still_needs_an_account_number(self):
        os.environ.update({"KIS_APP_KEY": "k", "KIS_APP_SECRET": "s", "KIS_ENV": "real"})
        with self.assertRaises(BrokerError):
            KIS()


class Refusals(unittest.TestCase):
    """증권사가 거절했을 때 무엇을 하면 되는지 화면에 적히는지 봅니다."""

    def setUp(self):
        os.environ.update({"KIS_APP_KEY": "k", "KIS_APP_SECRET": "top-secret",
                           "KIS_CANO": "12345678", "KIS_ACNT_PRDT_CD": "01",
                           "KIS_ENV": "real"})

    def tearDown(self):
        for key in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_CANO", "KIS_ACNT_PRDT_CD", "KIS_ENV"):
            os.environ.pop(key, None)

    def answer(self, status, payload):
        class Sent:
            status_code = status
            headers = {}
            def json(self):
                return payload
        return Sent()

    def test_a_token_limit_says_to_wait_a_minute(self):
        # 이 거절은 키가 틀린 것이 아니라 잠시 뒤 다시 누르면 되는 것입니다.
        sent = self.answer(403, {"msg_cd": "EGW00133", "msg1": "일시적으로 제한"})
        with patch.object(broker_kis.requests, "request", return_value=sent):
            with self.assertRaises(BrokerError) as caught:
                KIS(account=False).authorize()
        self.assertIn("1분", str(caught.exception))

    def test_a_refusal_never_echoes_the_response(self):
        sent = self.answer(403, {"msg_cd": "ZZ99", "msg1": "top-secret 12345678"})
        with patch.object(broker_kis.requests, "request", return_value=sent):
            with self.assertRaises(BrokerError) as caught:
                KIS(account=False).authorize()
        self.assertNotIn("top-secret", str(caught.exception))
        self.assertNotIn("12345678", str(caught.exception))

    def test_an_unreadable_answer_says_the_http_code(self):
        class Broken:
            status_code = 502
            headers = {}
            def json(self):
                raise ValueError()
        with patch.object(broker_kis.requests, "request", return_value=Broken()):
            with self.assertRaises(BrokerError) as caught:
                KIS(account=False).authorize()
        self.assertIn("502", str(caught.exception))

    def test_one_token_is_reused_instead_of_asked_for_again(self):
        # 진단을 누를 때마다 새 토큰을 받으면 증권사가 발급을 제한합니다.
        sent = self.answer(200, {"access_token": "t", "expires_in": 86400})
        with patch.object(broker_kis.requests, "request", return_value=sent) as asked:
            client = KIS(account=False)
            client.authorize()
            client.authorize()
        self.assertEqual(asked.call_count, 1)


if __name__ == "__main__":
    unittest.main()
