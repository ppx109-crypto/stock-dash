import unittest
from unittest.mock import patch
from providers import Official, demo
from automatic import brief


class AutomaticTests(unittest.TestCase):
    def provider(self):
        with patch.dict('os.environ', {'DART_CRTFC_KEY':'test','DATA_GO_KR_SERVICE_KEY':'test'}):
            p=Official()
        p.corps={'005930':'1','000660':'2','009150':'3'}
        p.names={'005930':'삼성전자','000660':'SK하이닉스','009150':'삼성전기'}
        return p

    def test_name_code_and_partial_search(self):
        p=self.provider()
        self.assertEqual(p.search('삼성전자')[0]['code'],'005930')
        self.assertEqual(len(p.search('삼성')),2)
        self.assertEqual(p.search('sk 하이닉스')[0]['code'],'000660')
        self.assertEqual(p.search('005930')[0]['name'],'삼성전자')
        self.assertEqual(p.search('없음'),[])
        self.assertEqual(p.search(''),[])

    def report(self):
        return {**demo(), 'sample':False,'price':20000,'shares':10_000_000,
            'anchors':[{'multiple':5},{'multiple':7}], 'company':{'induty_code':'26110'},
            'business_excerpt':'주요 사업은 반도체 메모리 제조입니다.'}

    def test_auto_value_units_and_sector(self):
        r=self.report();r['years'][-1]['profit']=100
        result=brief(r)
        self.assertEqual(result['fair']['base'],6000)
        self.assertEqual(result['fair']['gap'],-70)
        self.assertEqual(result['scores']['가치'],0)
        self.assertEqual(result['sectors'][0]['sector'],'반도체')

    def test_no_fabricated_value(self):
        r=self.report();r['anchors']=[]
        self.assertIsNone(brief(r)['fair'])
        # 금융업 코드만으로는 막지 않습니다. 지주회사가 함께 걸리기 때문입니다.
        # 매출을 한 해도 읽지 못한 금융회사만 산출을 보류합니다.
        r=self.report();r['company']['induty_code']='64121'
        for year in r['years']: year['revenue']=None
        self.assertIsNone(brief(r)['fair'])
        r=self.report();r['company']['induty_code']='64121'
        self.assertIsNotNone(brief(r)['fair'])
        r=self.report();r['years'][-1]['profit']=-1
        self.assertIsNone(brief(r)['fair'])
        self.assertEqual(brief(r)['growth'],'적자 · 회복 확인')

    def test_low_base_is_not_positive_growth(self):
        r=self.report();r['years'][-2]['profit']=-10
        out=brief(r)
        self.assertIsNone(out['profit_growth'])
        self.assertEqual(out['growth'],'흑자 전환')

if __name__=='__main__': unittest.main()
