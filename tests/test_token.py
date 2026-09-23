"""접근토큰 아껴 쓰기. 증권사는 잦은 발급을 제한합니다."""
import json
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import broker_kis
from broker_kis import KIS, BrokerError


class Reply:
    status_code = 200
    headers = {}

    def json(self):
        return {"access_token": "새-토큰", "expires_in": 86400}


class SharedToken(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "token.json")
        os.environ.update({"KIS_APP_KEY": "k", "KIS_APP_SECRET": "s", "KIS_ENV": "real",
                           "KIS_TOKEN_FILE": self.path})

    def tearDown(self):
        for key in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ENV", "KIS_TOKEN_FILE"):
            os.environ.pop(key, None)

    def test_a_second_run_reuses_the_saved_token(self):
        # 단계마다 새로 받으면 하루 한도에 금세 닿습니다.
        with patch.object(broker_kis.requests, "request", return_value=Reply()) as asked:
            KIS(account=False).authorize()
            KIS(account=False).authorize()
            KIS(account=False).authorize()
        self.assertEqual(asked.call_count, 1)

    def test_an_expired_token_is_asked_for_again(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"key": "k", "mode": "real", "token": "옛것",
                       "expires": time.time() - 10}, handle)
        with patch.object(broker_kis.requests, "request", return_value=Reply()) as asked:
            client = KIS(account=False)
            client.authorize()
        self.assertEqual(asked.call_count, 1)
        self.assertEqual(client.token, "새-토큰")

    def test_another_key_never_borrows_the_token(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"key": "다른키", "mode": "real", "token": "남의것",
                       "expires": time.time() + 9999}, handle)
        with patch.object(broker_kis.requests, "request", return_value=Reply()):
            client = KIS(account=False)
            client.authorize()
        self.assertEqual(client.token, "새-토큰")

    def test_a_broken_file_does_not_stop_the_run(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("망가진 내용")
        with patch.object(broker_kis.requests, "request", return_value=Reply()):
            client = KIS(account=False)
            client.authorize()
        self.assertEqual(client.token, "새-토큰")

    def test_without_the_setting_nothing_is_written(self):
        os.environ.pop("KIS_TOKEN_FILE")
        with patch.object(broker_kis.requests, "request", return_value=Reply()):
            KIS(account=False).authorize()
        self.assertFalse(os.path.exists(self.path))


if __name__ == "__main__":
    unittest.main()


class OneTokenForEveryLane(unittest.TestCase):
    """여러 갈래로 한꺼번에 받을 때 토큰을 두 번 받으러 가면 안 됩니다.

    증권사는 잦은 재발급을 막아 둡니다(EGW00133). 네 갈래가 동시에 인증을
    부르면 넷 다 거절당해, 그날 수집이 통째로 멈춥니다.
    """

    def test_four_lanes_ask_for_one_token(self):
        env = patch.dict(os.environ, {"KIS_APP_KEY": "k", "KIS_APP_SECRET": "s",
                                      "KIS_ENV": "demo"})
        env.start()
        self.addCleanup(env.stop)
        client = KIS(account=False)
        asked = []

        def slow(method, path, **kwargs):
            asked.append(path)
            time.sleep(0.05)
            return Mock(headers={}), {"access_token": "t", "expires_in": 86400}

        with patch.object(client, "_saved", return_value=None), \
             patch.object(client, "_keep"), \
             patch.object(client, "request", side_effect=slow):
            lanes = [threading.Thread(target=client.authorize) for _ in range(4)]
            for lane in lanes:
                lane.start()
            for lane in lanes:
                lane.join()
        self.assertEqual(asked, ["/oauth2/tokenP"])
        self.assertEqual(client.token, "t")


class CallPacing(unittest.TestCase):
    """증권사는 초당 호출 수를 제한합니다. 한 묶음 마흔 종목 중 서른여섯이
    이 까닭으로 실패하고 있었습니다."""

    def setUp(self):
        env = patch.dict(os.environ, {"KIS_APP_KEY": "k", "KIS_APP_SECRET": "s",
                                      "KIS_ENV": "demo", "KIS_CALL_GAP": "0.05"})
        env.start()
        self.addCleanup(env.stop)
        KIS._next = 0.0
        self.client = KIS(account=False)

    def test_calls_are_spaced_even_across_lanes(self):
        when = []

        def note(method, path, **kwargs):
            when.append(time.monotonic())
            return Mock(headers={}), {"rt_cd": "0"}

        with patch.object(self.client, "_once", side_effect=note):
            lanes = [threading.Thread(target=self.client.request, args=("GET", "/x"))
                     for _ in range(6)]
            for lane in lanes:
                lane.start()
            for lane in lanes:
                lane.join()
        when.sort()
        gaps = [b - a for a, b in zip(when, when[1:])]
        self.assertEqual(len(when), 6)
        self.assertTrue(all(g >= 0.04 for g in gaps), gaps)

    def test_a_rate_limit_refusal_is_tried_again(self):
        tries = []

        def sometimes(method, path, **kwargs):
            tries.append(1)
            if len(tries) < 3:
                raise BrokerError(KIS.REFUSALS["EGW00201"])
            return Mock(headers={}), {"rt_cd": "0"}

        with patch.object(self.client, "_once", side_effect=sometimes), \
             patch("broker_kis.time.sleep"):
            _, data = self.client.request("GET", "/x")
        self.assertEqual(len(tries), 3)
        self.assertEqual(data["rt_cd"], "0")

    def test_other_refusals_are_not_tried_again(self):
        tries = []

        def always(method, path, **kwargs):
            tries.append(1)
            raise BrokerError(KIS.REFUSALS["EGW00123"])

        with patch.object(self.client, "_once", side_effect=always), \
             patch("broker_kis.time.sleep"):
            with self.assertRaises(BrokerError):
                self.client.request("GET", "/x")
        self.assertEqual(len(tries), 1)

    def test_it_gives_up_after_enough_tries(self):
        tries = []

        def always(method, path, **kwargs):
            tries.append(1)
            raise BrokerError(KIS.REFUSALS["EGW00201"])

        with patch.dict(os.environ, {"KIS_RETRIES": "3"}), \
             patch.object(self.client, "_once", side_effect=always), \
             patch("broker_kis.time.sleep"):
            with self.assertRaises(BrokerError):
                self.client.request("GET", "/x")
        self.assertEqual(len(tries), 3)
