import unittest
from unittest import mock

import predash.kis as K


class Answer:
    def __init__(self, status, body):
        self.status_code, self.body = status, body

    def json(self):
        return self.body

    def raise_for_status(self):
        pass


SETTINGS = dict(mode='real', key='k' * 10, secret='s' * 10, cano='12345678', product='01')


class TokenShare(unittest.TestCase):
    def setUp(self):
        K._TOKENS.clear()

    def test_two_sessions_share_one_token(self):
        asked = []

        def fake(method, url, **kw):
            asked.append(url)
            return Answer(200, {'access_token': 'T', 'expires_in': 86400})
        with mock.patch.object(K.requests, 'request', side_effect=fake):
            K.KIS(settings=SETTINGS).authorize()
            K.KIS(settings=SETTINGS).authorize()
        self.assertEqual(len([u for u in asked if u.endswith('/oauth2/tokenP')]), 1)

    def test_403_shows_only_safe_code(self):
        body = {'msg_cd': 'EGW00133', 'msg1': '계좌 12345678 비밀 내용'}
        with mock.patch.object(K.requests, 'request', return_value=Answer(403, body)):
            with self.assertRaises(K.BrokerError) as caught:
                K.KIS(settings=SETTINGS).authorize()
        text = str(caught.exception)
        self.assertIn('EGW00133', text)
        self.assertIn('1분', text)
        self.assertNotIn('12345678', text)

    def test_403_unknown_code_is_named(self):
        with mock.patch.object(K.requests, 'request', return_value=Answer(403, {'msg_cd': 'EGW00999'})):
            with self.assertRaises(K.BrokerError) as caught:
                K.KIS(settings=SETTINGS).authorize()
        self.assertIn('EGW00999', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
