import re
import unittest
from predash.visuals import annual_bars,compact_dashboard,allocation

class EvidenceGraphics(unittest.TestCase):
    def test_negative_profit_and_zero_are_faithful(self):
        chart=annual_bars([{'year':2024,'profit':-20},{'year':2025,'profit':0}], 'profit','영업이익')
        self.assertIn('2024년 -20.0억',chart)
        self.assertIn('2025년 0.0억',chart)
        self.assertIn("fill='#1b5ca0'",chart)
        self.assertTrue(all(float(v)>=0 for v in re.findall(r"height='([0-9.]+)'",chart)))
    def test_missing_data_produces_no_chart_marks(self):
        result=compact_dashboard({'positions':[]},{})
        self.assertNotIn('<svg',result)
        self.assertNotIn('conic-gradient',result)
        self.assertIn('조회',result)
    def test_allocation_groups_rest_without_inventing_weight(self):
        result=allocation([{'name':str(i),'weight':10} for i in range(10)])
        self.assertIn('기타',result);self.assertIn('50.0%',result)
        self.assertIn('100.0000%',result)
    def test_untrusted_text_and_links_escaped(self):
        position={'code':'000001','name':'<script>bad</script>','weight':100,'quantity':1,'value':10,'pnl':-1}
        result=compact_dashboard({'positions':[position]}, {'000001':{'disclosures':[{'date':'20260930','title':'<img>','url':'javascript:alert(1)'}]}})
        self.assertNotIn('<script>',result);self.assertNotIn('javascript:',result)
        self.assertIn('&lt;img&gt;',result)

