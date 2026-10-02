"""Descriptive market regime for daily KIS index observations."""
from datetime import datetime, date
from math import isfinite

class MarketDataError(ValueError):
    pass

def index_lamp(rows, name, today=None):
    """Latest close > both means rise; < both fall; otherwise sideways."""
    today=today or date.today()
    observations={}
    for row in rows:
        try:
            stamp=str(row['stck_bsop_date'])
            day=datetime.strptime(stamp,'%Y%m%d').date()
            value=float(str(row['bstp_nmix_prpr']).replace(',',''))
            if day>today or value<=0 or not isfinite(value): raise ValueError
        except (KeyError,TypeError,ValueError):
            raise MarketDataError('지수 날짜·종가 응답을 확인하지 못했습니다.') from None
        if day in observations:
            if observations[day]!=value:raise MarketDataError('같은 날짜에 다른 지수 종가가 있습니다.')
        observations[day]=value
    ordered=sorted(observations.items(),reverse=True)
    if len(ordered)<20:return None
    latest=ordered[0][0]
    if (today-latest).days>5:return None
    close=ordered[0][1]
    previous=ordered[1][1]
    change=close-previous
    ma10=sum(value for _,value in ordered[:10])/10
    ma20=sum(value for _,value in ordered[:20])/20
    if close>max(ma10,ma20):state='상승 구간'
    elif close<min(ma10,ma20):state='하락 구간'
    else:state='횡보 구간'
    return {'name':name,'date':latest.isoformat(),'close':close,
            'ma10':ma10,'ma20':ma20,'state':state,'observations':20,
            'previous':previous,'previous_date':ordered[1][0].isoformat(),
            'change':change,'change_pct':change/previous*100}

def stock_lamp(rows, code, today=None):
    """Daily stock closes from public data, with the same 10/20 rule as indices."""
    converted=[]
    for row in rows:
        if str(row.get('srtnCd','')).removeprefix('A').zfill(6)!=code:
            continue
        converted.append({'stck_bsop_date':row.get('basDt'), 'bstp_nmix_prpr':row.get('clpr')})
    return index_lamp(converted,code,today)

def market_flow(rows, today=None):
    """Latest dated market net-buy amounts, retaining source units until verified."""
    today=today or date.today()
    values={}
    for row in rows:
        try:
            day=datetime.strptime(str(row['stck_bsop_date']),'%Y%m%d').date()
            if day>today:raise ValueError
            point={name:float(str(row[field]).replace(',','')) for name,field in
                   (('individual','prsn_ntby_tr_pbmn'),('institution','orgn_ntby_tr_pbmn'),('foreign','frgn_ntby_tr_pbmn'))}
            if not all(isfinite(v) for v in point.values()):raise ValueError
        except (KeyError,TypeError,ValueError):
            raise MarketDataError('시장 수급의 날짜·순매수 응답을 확인하지 못했습니다.') from None
        if day in values and values[day]!=point:raise MarketDataError('같은 날짜의 시장 수급이 서로 다릅니다.')
        values[day]=point
    if not values:raise MarketDataError('시장 수급 자료가 없습니다.')
    latest=max(values)
    if (today-latest).days>5:raise MarketDataError('시장 수급 기준일이 오래됐습니다.')
    return {'date':latest.isoformat(),'net':values[latest],'unit':'source','source':'KIS 시장별 일별 수급'}


def price_trend(rows,code,today):
    """Dated closes and trailing averages; never pad missing observations."""
    points={}
    for r in rows:
        if str(r.get('srtnCd','')).removeprefix('A').zfill(6)!=code:continue
        try:
            day=datetime.strptime(str(r['basDt']),'%Y%m%d').date()
            value=float(str(r['clpr']).replace(',',''))
            if day>today or value<=0 or not isfinite(value):raise ValueError
        except (KeyError,ValueError,TypeError):raise MarketDataError('종목 차트 날짜·가격 확인 실패') from None
        if day in points and points[day]!=value:raise MarketDataError('종목 차트 중복 가격 충돌')
        points[day]=value
    days=sorted(points)
    if len(days)<20 or (today-days[-1]).days>5:return []
    values=[points[d] for d in days]
    return [{'날짜':d.isoformat(),'종가':values[i],
             '10일선':sum(values[i-9:i+1])/10 if i>=9 else None,
             '20일선':sum(values[i-19:i+1])/20 if i>=19 else None}
            for i,d in enumerate(days)][-60:]

