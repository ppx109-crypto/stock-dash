"""Optional KRX daily market activity, separate from account and fundamentals."""
import re
from datetime import date,timedelta
import requests

class KRXError(ValueError):
    pass

def daily_activity(key,code,asof=None):
    """Latest validated KOSPI/KOSDAQ daily record, not intraday activity."""
    if not key or not re.fullmatch(r'[0-9]{6}',code):
        raise KRXError('KRX 키 또는 종목코드를 확인하세요.')
    asof=asof or date.today()
    for offset in range(6):
        day=asof-timedelta(days=offset)
        if day.weekday()>=5:continue
        for api in ('stk_bydd_trd','ksq_bydd_trd'):
            try:
                response=requests.get(f'https://data-dbg.krx.co.kr/svc/apis/sto/{api}',
                    headers={'AUTH_KEY':key},params={'basDd':day.strftime('%Y%m%d')},timeout=(5,12))
                response.raise_for_status()
                rows=response.json().get('OutBlock_1')
                if not isinstance(rows,list):raise KRXError('KRX 응답 형식을 확인하지 못했습니다.')
            except (requests.RequestException,ValueError) as exc:
                raise KRXError('KRX 시세 조회에 실패했습니다. 인증키와 서비스 이용 승인을 확인하세요.') from exc
            for row in rows:
                if str(row.get('ISU_SRT_CD','')).zfill(6)!=code or str(row.get('BAS_DD',''))!=day.strftime('%Y%m%d'):
                    continue
                try:
                    volume=int(str(row['ACC_TRDVOL']).replace(',',''))
                    turnover=int(str(row['ACC_TRDVAL']).replace(',',''))
                    cap=int(str(row['MKTCAP']).replace(',',''))
                    if min(volume,turnover,cap)<0:raise ValueError
                except (KeyError,ValueError,TypeError):
                    raise KRXError('KRX 거래량·거래대금·시가총액 응답을 확인하지 못했습니다.') from None
                return {'date':day.isoformat(),'volume':volume,'turnover':turnover,'market_cap':cap,
                        'market':'코스피' if api=='stk_bydd_trd' else '코스닥'}
    return None

