import unittest
from datetime import date
from predash.dashboard import overview

class DashboardEvidence(unittest.TestCase):
    def test_distinct_sections_and_current_disclosure(self):
        positions=[{'code':'005930','name':'삼성전자','weight':33,'value':100},
                   {'code':'000660','name':'SK하이닉스','weight':20,'value':60}]
        reports={'000660':{'years':[{'year':2024,'profit':10},{'year':2025,'profit':20}],
                           'disclosures':[{'date':'20260926','title':'공시','url':'https://dart.fss.or.kr/'}]}}
        result=overview({'positions':positions},reports,date(2026,9,29))
        self.assertEqual(result['largest']['code'],'005930')
        self.assertEqual(result['earnings']['position']['code'],'000660')
        self.assertEqual(result['disclosure']['position']['code'],'000660')
    def test_absent_reports_never_invents_facts(self):
        result=overview({'positions':[{'code':'005930','name':'삼성전자','weight':100,'value':100}]},{},date(2026,9,29))
        self.assertIsNone(result['earnings'])
        self.assertIsNone(result['disclosure'])
    def test_old_disclosure_does_not_claim_recent(self):
        report={'disclosures':[{'date':'20260901','title':'과거'}]}
        result=overview({'positions':[{'code':'005930','weight':10}]},{'005930':report},date(2026,9,29))
        self.assertIsNone(result['disclosure'])
if __name__=='__main__':unittest.main()

