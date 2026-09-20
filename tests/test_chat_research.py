import copy
import json
import unittest
from pathlib import Path

import pandas as pd

from chat_research import parse_bundle, validate, growth, trends, request_text


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.bundle=json.loads((Path(__file__).parents[1]/'research/initial-examples.json').read_text())

    def test_initial_reports_have_real_source_financials(self):
        result=parse_bundle(json.dumps(self.bundle))
        self.assertEqual(len(result),2)
        self.assertEqual(growth(120,100),'+20.0%')
        self.assertEqual(growth(5,-10),'흑자 전환')

    def test_mismatched_cumulative_period_rejected(self):
        r=copy.deepcopy(self.bundle['reports'][0]);r['financial']['prior_period']='2024-06'
        with self.assertRaises(ValueError):validate(r)

    def test_peer_currency_mismatch_rejected(self):
        r=copy.deepcopy(self.bundle['reports'][0]);r['peers']['rows'][0]['currency']='USD'
        with self.assertRaises(ValueError):validate(r)

    def test_request_excludes_private_positions(self):
        text=request_text([{'name':'삼성전자','code':'005930','quantity':982734,'account':'private-account'}])
        self.assertNotIn('982734',text);self.assertNotIn('private-account',text)

    def test_daily_and_completed_weekly(self):
        dates=pd.bdate_range('2025-01-01', periods=160)
        prices={'rows':[{'date':str(d.date()),'close':i+100} for i,d in enumerate(dates)]}
        t,_=trends(prices,'2025-09-01')
        self.assertEqual(t['daily'],'상승 정렬');self.assertEqual(t['weekly'],'상승 정렬')
        t,_=trends({'rows':prices['rows'][:30]},'2025-09-01')
        self.assertEqual(t['daily'],'기간 부족')


class GrowthWording(unittest.TestCase):
    """부호가 바뀌는 변화는 퍼센트가 아니라 말로 적습니다."""

    def test_profit_turning_negative_is_not_a_percentage(self):
        self.assertEqual(growth(-56, 405), '적자 전환')
        self.assertEqual(growth(0, 500), '적자 전환')

    def test_ordinary_change_stays_a_percentage(self):
        self.assertEqual(growth(600, 500), '+20.0%')

    def test_loss_turning_positive_is_still_a_turnaround(self):
        self.assertEqual(growth(1200, -300), '흑자 전환')
