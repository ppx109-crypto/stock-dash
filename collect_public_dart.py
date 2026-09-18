"""Collect only public issuer facts, never user watchlists or personal notes."""
import json
import os
import re
from datetime import date,timedelta
from pathlib import Path
from providers import Official, number


# Half-year statements report the cumulative figure in thstrm_add_amount; the
# plain thstrm_amount holds the quarter alone, so the two are never mixed.
def half(p, corp, year, basis):
    result = p.dart('fnlttSinglAcntAll.json', corp_code=corp, bsns_year=str(year), reprt_code='11012', fs_div=basis)
    if not result:
        return None
    rows = result.get('list', [])
    def account(ids, names):
        for row in rows:
            if row.get('sj_div') not in ('IS', 'CIS'):
                continue
            if row.get('account_id') in ids or row.get('account_nm') in names:
                raw = number(row.get('thstrm_add_amount')) or number(row.get('thstrm_amount'))
                if raw is not None:
                    return raw / 100_000_000
        return None
    receipt = next((r.get('rcept_no') for r in rows if r.get('rcept_no')), '')
    revenue = account(['ifrs-full_Revenue'], ['매출액', '수익(매출액)'])
    profit = account(['dart_OperatingIncomeLoss'], ['영업이익', '영업이익(손실)'])
    if revenue is None or profit is None:
        return None
    return {'period': f'{year}-06', 'revenue': revenue, 'profit': profit, 'receipt': receipt,
            'url': 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=' + receipt}


def collect(code):
    p=Official();corp=p.corp(code);today=date.today()
    years=None
    for year in range(today.year-1,today.year-4,-1):
        for basis in ('CFS','OFS'):
            series=[p.annual(corp,y,basis) for y in range(year-2,year+1)]
            if all(series):
                years=series;break
        if years:break
    if not years:raise ValueError('Missing annuals')
    info=p.dart('company.json',corp_code=corp) or {}
    recent=p.dart('list.json',corp_code=corp,bgn_de=(today-timedelta(days=90)).strftime('%Y%m%d'),end_de=today.strftime('%Y%m%d'),page_count=30,sort='date',sort_mth='desc') or {}
    try:excerpt=p.business_excerpt(years[-1].get('receipt'))
    except Exception:excerpt=''
    halves=[]
    for y in (today.year-1,today.year):
        try:
            found=half(p,corp,y,basis)
        except Exception:
            found=None
        if found:halves.append(found)
    return {'code':code,'name':info.get('stock_name') or info.get('corp_name'),'halves':halves,
            'company':{k:info.get(k,'') for k in ['corp_name','induty_code','hm_url','est_dt','acc_mt']},
            'years':years,'basis':basis,'business_excerpt':excerpt,'fetched':today.isoformat(),
            'disclosures':[{'title':r['report_nm'],'date':r['rcept_dt'],'url':'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+r['rcept_no']} for r in recent.get('list',[])]}


if __name__=='__main__':
    codes=[c.strip() for c in os.getenv('PUBLIC_CODES','005930,000660').split(',')]
    if not codes or len(codes)>10 or any(not re.fullmatch(r'[0-9]{6}',c) for c in codes):
        raise SystemExit('Use 1-10 six-digit public issuer codes')
    Path('public-data').mkdir(exist_ok=True)
    failures=0
    for code in codes:
        try:
            data=collect(code)
            Path('public-data',code+'.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            print(code,'public-data collected')
        except Exception:
            failures+=1;print(code,'collection failed; existing file retained')
    raise SystemExit(1 if failures else 0)
