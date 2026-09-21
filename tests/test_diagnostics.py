"""전체 연결 진단. 한 번 늦은 것과 정말 안 되는 것을 갈라 봅니다."""
import os
import unittest
from unittest.mock import patch

import requests

import data_registry


def spec(provider_id):
    return next(s for s in data_registry.PROVIDERS if s.provider_id == provider_id)


class Reply:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class Dart(unittest.TestCase):
    def setUp(self):
        os.environ["DART_CRTFC_KEY"] = "test"

    def tearDown(self):
        os.environ.pop("DART_CRTFC_KEY", None)

    def test_one_slow_answer_is_not_a_failure(self):
        # 한 번 늦었다고 멀쩡한 키를 '확인 필요'로 적으면 안 됩니다.
        answers = [requests.Timeout(), Reply({"status": "000"})]
        with patch.object(data_registry.requests, "get",
                          side_effect=lambda *a, **k: _pop(answers)), \
             patch.object(data_registry.time, "sleep"):
            found = data_registry.health(spec("opendart"))
        self.assertEqual(found["status"], "ok")

    def test_two_timeouts_are_reported_as_a_delay_not_a_bad_key(self):
        with patch.object(data_registry.requests, "get", side_effect=requests.Timeout()), \
             patch.object(data_registry.time, "sleep"):
            found = data_registry.health(spec("opendart"))
        self.assertEqual(found["status"], "error")
        self.assertIn("지연", found["detail"])

    def test_a_rejected_key_still_says_so(self):
        with patch.object(data_registry.requests, "get", return_value=Reply({"status": "010"})):
            found = data_registry.health(spec("opendart"))
        self.assertEqual(found["detail"], "키 미등록")

    def test_the_diagnostic_waits_as_long_as_the_real_fetch(self):
        seen = {}
        def record(*args, **kwargs):
            seen.update(kwargs)
            return Reply({"status": "000"})
        with patch.object(data_registry.requests, "get", side_effect=record):
            data_registry.health(spec("opendart"))
        self.assertEqual(seen["timeout"], (10, 30))


class Registry(unittest.TestCase):
    def test_the_broker_is_listed_with_its_two_jobs(self):
        found = spec("kis_domestic")
        self.assertEqual(found.env_keys, ("KIS_APP_KEY", "KIS_APP_SECRET"))
        self.assertIn("stock.opinion", found.capabilities)
        self.assertIn("stock.live_quote", found.capabilities)

    def test_a_provider_without_keys_is_marked_not_configured(self):
        for key in ("KIS_APP_KEY", "KIS_APP_SECRET"):
            os.environ.pop(key, None)
        self.assertEqual(data_registry.health(spec("kis_domestic"))["status"], "not_configured")


def _pop(answers):
    answer = answers.pop(0)
    if isinstance(answer, Exception):
        raise answer
    return answer


if __name__ == "__main__":
    unittest.main()
