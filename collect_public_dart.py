"""Collect only public issuer facts, never user watchlists or personal notes."""
import json
import os
import re
from datetime import date,timedelta
from pathlib import Path
from providers import Official, number


# 반기보고서는 1~6월 누적을 thstrm_add_amount에, 4~6월 석 달만을
# thstrm_amount에 적습니다. 둘을 섞으면 작년 누적과 올해 석 달을 견주게 되어
# 성장·적자 판정이 통째로 뒤집힙니다. 어느 칸을 썼는지 남겨 두고, 매출과
# 영업이익이 서로 다른 칸에서 나왔으면 그 반기는 쓰지 않습니다.
def half(p, corp, year, basis):
    result = p.dart('fnlttSinglAcntAll.json', corp_code=corp, bsns_year=str(year), reprt_code='11012', fs_div=basis)
    if not result:
        return None
    rows = result.get('list', [])
    seen = []
    def account(ids, names):
        for row in rows:
            if row.get('sj_div') not in ('IS', 'CIS'):
                continue
            if row.get('account_id') in ids or row.get('account_nm') in names:
                # 0도 값입니다. 빈 칸일 때만 석 달 칸으로 내려갑니다.
                added = number(row.get('thstrm_add_amount'))
                plain = number(row.get('thstrm_amount'))
                raw, used = (added, 'cumulative') if added is not None else (plain, 'quarter')
                seen.append({'account_nm': row.get('account_nm'), 'sj_div': row.get('sj_div'),
                             'thstrm_nm': row.get('thstrm_nm'), 'used': used,
                             'add': row.get('thstrm_add_amount'), 'amount': row.get('thstrm_amount')})
                if raw is not None:
                    return raw / 100_000_000, used
        return None, None
    receipt = next((r.get('rcept_no') for r in rows if r.get('rcept_no')), '')
    revenue, revenue_from = account(['ifrs-full_Revenue'], ['매출액', '수익(매출액)'])
    profit, profit_from = account(['dart_OperatingIncomeLoss'], ['영업이익', '영업이익(손실)'])
    if revenue is None or profit is None or revenue_from != profit_from:
        return None
    return {'period': f'{year}-06', 'revenue': revenue, 'profit': profit, 'receipt': receipt,
            'matched': seen[:4], 'measure': revenue_from,
            'url': 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=' + receipt}


# DART의 전체 재무제표 API는 2015 사업연도부터 답합니다. 그 앞은 물어도
# 빈손이라 여기서 멈춥니다.
FIRST_YEAR = int(os.getenv('PUBLIC_FIRST_YEAR', '2015'))


def collect(code,p=None):
    p=p or Official();corp=p.corp(code);today=date.today()
    # 먼저 어느 기준(연결·별도)으로 읽히는지 최근 세 해로 정합니다. 그런 다음
    # 그 기준 그대로 옛 해까지 거슬러 갑니다. 해마다 기준이 바뀌면 성장률이
    # 기준 차이 때문에 튀므로, 한 종목은 한 기준으로만 읽습니다.
    years=None;basis=None
    for anchor in range(today.year-1,today.year-4,-1):
        for option in ('CFS','OFS'):
            series=[p.annual(corp,y,option) for y in range(anchor-2,anchor+1)]
            if all(series):
                years=series;basis=option;break
        if years:break
    if not years:raise ValueError('Missing annuals')
    # 옛 해를 앞에 붙입니다. 실적 조건을 오래전 날짜에도 붙이려면 그때 이미
    # 공시돼 있던 결산이 있어야 합니다.
    older=[]
    for y in range(years[0]['year']-1, FIRST_YEAR-1, -1):
        found=p.annual(corp,y,basis)
        if not found or found.get('revenue') is None:
            break
        older.append(found)
    years=list(reversed(older))+years
    info=p.dart('company.json',corp_code=corp) or {}
    recent=p.dart('list.json',corp_code=corp,bgn_de=(today-timedelta(days=90)).strftime('%Y%m%d'),end_de=today.strftime('%Y%m%d'),page_count=30,sort='date',sort_mth='desc') or {}
    # 사업보고서 원문은 종목당 수십 MB라 여러 종목을 모을 때는 건너뜁니다.
    excerpt=''
    if os.getenv('PUBLIC_WITH_EXCERPT','1').strip() not in ('0','false','False'):
        try:excerpt=p.business_excerpt(years[-1].get('receipt'))
        except Exception:excerpt=''
    halves=[]
    for y in range(FIRST_YEAR, today.year+1):
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
    if not codes or len(codes)>25 or any(not re.fullmatch(r'[0-9]{6}',c) for c in codes):
        raise SystemExit('Use 1-25 six-digit public issuer codes')
    Path('public-data').mkdir(exist_ok=True)
    failures=0
    shared=Official()
    for code in codes:
        try:
            data=collect(code,shared)
            Path('public-data',code+'.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            print(code,'public-data collected')
        except Exception:
            failures+=1;print(code,'collection failed; existing file retained')
    # 한 종목이 실패해도 나머지는 받아 둔 것이므로 저장까지 마칩니다. 우선주처럼
    # 따로 공시하지 않는 종목이 목록에 섞여 있다고 전체를 버릴 이유가 없습니다.
    print(f'{len(codes)-failures}/{len(codes)} collected')
    raise SystemExit(1 if failures==len(codes) else 0)
