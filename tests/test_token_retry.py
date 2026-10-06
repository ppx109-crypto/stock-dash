"""출입증(접근토큰) 받기: 1분 안 두 번째 발급 거절(EGW00133)이면 1분 기다려 보관 파일부터 보고 한 번 더(2026-10-06 검토)."""
import json
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

import broker_kis as B


def client(path):
    c = B.KIS.__new__(B.KIS)
    c.key, c.secret, c.mode, c.token, c.expires = "k", "s", "real", None, 0
    c._gate = threading.Lock()
    return c


class TokenRetry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "t.json")
        self.env = mock.patch.dict(os.environ, {"KIS_TOKEN_FILE": self.path, "KIS_TOKEN_RETRY_WAIT": "0"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_retry_once_after_egw00133(self):
        c = client(self.path)
        calls = []

        def req(method, path, **kw):
            calls.append(path)
            if len(calls) == 1:
                raise B.BrokerError(B.KIS.REFUSALS["EGW00133"])
            return None, {"access_token": "T2", "expires_in": 86400}
        with mock.patch.object(c, "request", side_effect=req):
            c.authorize()
        self.assertEqual(c.token, "T2")
        self.assertEqual(len(calls), 2)

    def test_uses_token_another_job_saved_meanwhile(self):
        c = client(self.path)

        def req(method, path, **kw):
            with open(self.path, "w") as f:      # 그 사이 다른 작업이 받아 둔 것
                json.dump({"key": "k", "mode": "real", "token": "OTHER", "expires": time.time() + 3600}, f)
            raise B.BrokerError(B.KIS.REFUSALS["EGW00133"])
        with mock.patch.object(c, "request", side_effect=req) as r:
            c.authorize()
        self.assertEqual(c.token, "OTHER")
        self.assertEqual(r.call_count, 1)

    def test_other_errors_not_retried(self):
        c = client(self.path)
        with mock.patch.object(c, "request", side_effect=B.BrokerError(B.KIS.REFUSALS["EGW00123"])) as r, \
                self.assertRaises(B.BrokerError):
            c.authorize()
        self.assertEqual(r.call_count, 1)

    def test_broken_saved_file_ignored(self):
        c = client(self.path)
        for body in ("[1, 2]", '{"key": "k", "mode": "real", "token": "x", "expires": null}', '"text"'):
            with open(self.path, "w") as f:
                f.write(body)
            self.assertIsNone(c._saved())


if __name__ == "__main__":
    unittest.main()
