import json
import unittest
from pathlib import Path

import dashboard_ui as D

ROOT = Path(__file__).resolve().parents[1]


class FinalBoard(unittest.TestCase):
    def test_note_switches_when_final_runs(self):
        self.assertFalse(D.final_active(None))
        self.assertIn("시작 날을 정하면 켜짐", D.mix_note(None))
        self.assertIn("15분봉 50%", D.mix_note({}))
        on = {"last_day": "20261102", "held": {"122630": 10}, "B": 1.0, "applied": "상승"}
        self.assertTrue(D.final_active(on))
        note = D.mix_note(on)
        self.assertIn("운영 중", note)
        self.assertIn("바구니 30%", note)
        self.assertIn("15분봉 뺌", note)

    def test_regime_same_as_bot(self):
        fx = json.loads((ROOT / "tests/fixtures/overlay_states.json").read_text(encoding="utf-8"))
        r = D.overlay_regime(fx["closes"])
        self.assertEqual((r["day"], r["state"]), (fx["last"], fx["states"][fx["last"]]))
        self.assertEqual(len(r["recent"]), 5)
        self.assertEqual([x[2] for x in r["recent"]], [fx["states"][d] for d, _, _ in r["recent"]])
        self.assertEqual(D.overlay_regime([("20260101", 1.0)]), {})

    def test_panels_render(self):
        off = D.overlay_panel(None, None, {"day": "20261008", "state": "상승", "recent": [("20261008", "하락", "상승")]})
        self.assertIn("아직 켜지 않음", off)
        self.assertIn("KODEX 레버리지 40%", off)
        on = D.overlay_panel({"last_day": "20261102", "held": {"114800": 300}, "applied": None, "unconfirmed": {"left": {"122630": 5}}},
                             {"orders": [{"at": "2026-11-02 15:12", "side": "sell", "code": "122630", "qty": 5, "why": "국면 횡보", "status": "접수"}]})
        self.assertIn("KODEX 인버스(114800) 300주", on)
        self.assertIn("다시 맞춤 기다림", on)
        self.assertIn("체결이 확인되지 않은 매도", on)
        mini = D.overlay_mini({"last_day": "20261102", "held": {"122630": 7}}, None, {"122630": {"price": 12345.0, "rate": 1.2}})
        self.assertIn("12,345원", mini)
        self.assertIn("켜짐", mini)
        self.assertIn("아직 켜지 않음", D.overlay_mini(None, None))
        self.assertIn("+34.1%", D.OVERLAY_RULES)

    def test_lever_card(self):
        on = {"last_day": "20261012", "held": {"122630": 7}}
        card = D.lever_card(on, {"day": "20261012", "state": "상승"}, left_15m=2)
        self.assertIn("레버리지 봇", card)
        self.assertIn("KODEX 레버리지(122630) 계좌의 40%", card)
        self.assertIn("KODEX 레버리지 7주", card)
        self.assertIn("남은 2종목", card)
        self.assertIn("쉼(든 것을 모두 팖)", D.lever_card(on, {"day": "20261012", "state": "하락"}))
        self.assertIn("국면 셈 기다림", D.lever_card(None, {}))
        self.assertNotIn("덧붙임", D.OVERLAY_RULES + D.mix_note(on) + D.overlay_mini(on, None) + D.FINAL_MIX)


if __name__ == "__main__":
    unittest.main()
