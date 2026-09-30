"""Personal domestic-stock balance reader. No order endpoints."""
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests


class BrokerError(RuntimeError):
    pass


def amount(value):
    try:
        result = float(str(value).replace(',', ''))
        if not (-float('inf') < result < float('inf')):
            raise ValueError()
        return result
    except (TypeError, ValueError):
        raise BrokerError('잔고 응답의 숫자를 확인할 수 없습니다. 이전 자료를 유지합니다.') from None


class KIS:
    def __init__(self, account=True):
        # 시세와 투자의견은 계좌번호 없이 읽습니다. 잔고만 계좌를 요구합니다.
        self.key = os.getenv('KIS_APP_KEY', '').strip()
        self.secret = os.getenv('KIS_APP_SECRET', '').strip()
        self.cano = os.getenv('KIS_CANO', '').strip()
        self.product = os.getenv('KIS_ACNT_PRDT_CD', '').strip()
        self.mode = os.getenv('KIS_ENV', 'demo').strip()
        if not self.key or not self.secret:
            raise BrokerError('한국투자증권 App Key·App Secret을 설정하세요.')
        if account and (not re.fullmatch(r'[0-9]{8}', self.cano) or not re.fullmatch(r'[0-9]{2}', self.product)):
            raise BrokerError('한국투자증권 계좌 앞 8자리·뒤 2자리를 설정하세요.')
        if self.mode not in ('real', 'demo'):
            raise BrokerError('KIS_ENV는 real 또는 demo로 입력하세요.')
        self.base = 'https://openapi.koreainvestment.com:9443' if self.mode == 'real' else 'https://openapivts.koreainvestment.com:29443'
        self.token = None
        self.expires = 0
        # 여러 갈래로 한꺼번에 받을 때, 토큰을 두 번 받으러 가지 않게 합니다.
        # 증권사가 잦은 재발급을 막아 두어, 겹치면 둘 다 거절당합니다.
        self._gate = threading.Lock()

    # 증권사가 거절할 때 주는 코드 중, 사람이 할 일이 정해져 있는 것들입니다.
    REFUSALS = {
        'EGW00133': '접근토큰 발급이 잠시 제한되었습니다. 1분쯤 뒤에 다시 눌러 주세요.',
        'EGW00123': '앱키 또는 앱시크릿이 맞지 않습니다.',
        'EGW00201': '초당 호출 한도를 넘었습니다. 잠시 뒤 다시 눌러 주세요.',
    }

    # 증권사는 초당 호출 수를 제한합니다(EGW00201). 서른 해치를 받으려면 한
    # 종목에 예순 번 넘게 물어야 해서, 문 앞에서 줄을 세우지 않으면 금세
    # 한도에 닿습니다. 실제로 한 묶음 마흔 종목 중 서른여섯이 이 까닭으로
    # 실패하고 있었습니다. 갈래를 늘리면 더 빨리 닿습니다.
    #
    # 그래서 호출 사이 간격을 저장소 전체가 하나로 지킵니다. 갈래가 몇이든
    # 초당 호출 수는 같습니다. 그러고도 거절당하면 한 번에 두 배씩 쉬면서
    # 몇 번 다시 물어봅니다.
    _pace = threading.Lock()
    _next = 0.0

    @classmethod
    def _wait_turn(cls):
        gap = float(os.getenv('KIS_CALL_GAP', '0.35'))
        with cls._pace:
            now = time.monotonic()
            when = max(now, cls._next)
            cls._next = when + gap
        if when > now:
            time.sleep(when - now)

    def request(self, method, path, **kwargs):
        self._wait_turn()
        tries = max(1, int(os.getenv('KIS_RETRIES', '4')))
        rest = 1.0
        for turn in range(tries):
            try:
                return self._once(method, path, **kwargs)
            except BrokerError as error:
                if self.REFUSALS['EGW00201'] not in str(error) or turn == tries - 1:
                    raise
                time.sleep(rest)
                rest *= 2
                self._wait_turn()

    def _once(self, method, path, **kwargs):
        try:
            response = requests.request(method, self.base + path, timeout=(5, 20), **kwargs)
        except requests.RequestException:
            raise BrokerError('증권사에 연결하지 못했습니다. 네트워크와 서비스 상태를 '
                              '확인한 뒤 다시 조회하세요.') from None
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError()
        except ValueError:
            raise BrokerError(f'증권사 응답을 읽지 못했습니다. HTTP {response.status_code}.') from None
        if response.status_code >= 400:
            # 응답 본문에는 계좌번호가 들어 있을 수 있어 그대로 옮기지 않습니다.
            # 정해진 형태의 코드만 꺼내 씁니다.
            code = str(data.get('msg_cd') or data.get('error_code') or '').strip()
            code = code if re.fullmatch(r'[A-Z]{2,4}[0-9]{3,6}', code) else ''
            if code in self.REFUSALS:
                raise BrokerError(self.REFUSALS[code])
            raise BrokerError(f'증권사가 요청을 거절했습니다. HTTP {response.status_code}'
                              + (f' · {code}' if code else '')
                              + ' · 환경·키·서비스 상태를 확인하세요.')
        return response, data

    def _saved(self):
        """받아 둔 토큰을 다시 씁니다.

        증권사는 접근토큰을 하루 한 번 발급하는 것을 원칙으로 하고, 짧은
        사이에 여러 번 받으면 이용을 제한합니다. 한 작업 안에서 여러 단계가
        차례로 돌 때마다 새로 받으면 금세 그 한도에 닿습니다. 그래서
        KIS_TOKEN_FILE이 주어지면 그 파일에 두고 함께 씁니다. 저장소에는
        넣지 않습니다. 한 번 돌고 사라지는 자리에만 둡니다.
        """
        path = os.getenv('KIS_TOKEN_FILE', '').strip()
        if not path:
            return None
        try:
            with open(path, encoding='utf-8') as handle:
                kept = json.load(handle)
        except (OSError, ValueError):
            return None
        if kept.get('key') != self.key or kept.get('mode') != self.mode:
            return None
        if not kept.get('token') or time.time() >= float(kept.get('expires', 0)):
            return None
        return kept

    def _keep(self):
        path = os.getenv('KIS_TOKEN_FILE', '').strip()
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump({'key': self.key, 'mode': self.mode, 'token': self.token,
                           'expires': self.expires}, handle)
            os.chmod(path, 0o600)
        except OSError:
            pass

    def authorize(self):
        if self.token and time.time() < self.expires:
            return
        with self._gate:
            # 기다리는 사이에 다른 갈래가 받아 두었을 수 있습니다.
            if self.token and time.time() < self.expires:
                return
            kept = self._saved()
            if kept:
                self.token, self.expires = kept['token'], float(kept['expires'])
                return
            _, data = self.request('POST', '/oauth2/tokenP', json={'grant_type': 'client_credentials', 'appkey': self.key, 'appsecret': self.secret})
            if not data.get('access_token'):
                raise BrokerError('증권사 인증에 실패했습니다. 실전·모의 키가 선택 환경과 같은지 확인하세요.')
            self.token = data['access_token']
            self.expires = time.time() + max(0, amount(data.get('expires_in', 0)) - 120)
            self._keep()

    def opinions(self, code, days=180):
        """한 종목의 증권사 투자의견과 목표가를 기간으로 받아옵니다.

        국내주식 종목투자의견(국내주식-188) API입니다. 조회 전용이며 주문과
        무관합니다. 응답의 hts_goal_prc가 목표가, invt_opnn이 의견입니다.
        """
        today = datetime.now(ZoneInfo('Asia/Seoul')).date()
        begin = today - timedelta(days=max(days, 1))
        return self.opinions_between(code, begin.strftime('%Y%m%d'), today.strftime('%Y%m%d'))[0]

    OPINION_PAGE = 100      # 한 번에 오는 줄의 끝. 이만큼 오면 그 기간에 더 있을 수 있습니다.

    def opinions_between(self, code, start, end):
        """start~end(YYYYMMDD) 사이의 투자의견. (목표가 있는 줄들, 받은 줄 수)를 돌려줍니다.

        받은 줄 수가 OPINION_PAGE에 닿으면 그 기간에 더 있을 수 있으니, 부르는 쪽이 기간을 쪼갭니다.
        """
        if not re.fullmatch(r'[0-9]{6}', str(code)):
            raise BrokerError('종목코드는 숫자 6자리여야 합니다.')
        if not (re.fullmatch(r'[0-9]{8}', str(start)) and re.fullmatch(r'[0-9]{8}', str(end))):
            raise BrokerError('날짜는 숫자 8자리여야 합니다.')
        self.authorize()
        _, data = self.request(
            'GET', '/uapi/domestic-stock/v1/quotations/invest-opinion',
            headers={'authorization': 'Bearer ' + self.token, 'appkey': self.key,
                     'appsecret': self.secret, 'tr_id': 'FHKST663300C0', 'custtype': 'P'},
            params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_COND_SCR_DIV_CODE': '16633',
                    'FID_INPUT_ISCD': str(code), 'FID_INPUT_DATE_1': str(start),
                    'FID_INPUT_DATE_2': str(end)})
        if str(data.get('rt_cd')) != '0':
            # 응답 문구는 싣지 않고, 모양을 확인한 코드만 붙입니다.
            seen = str(data.get('msg_cd') or '').strip()
            seen = seen if re.fullmatch(r'[A-Z]{2,4}[0-9]{3,6}', seen) else ''
            raise BrokerError('투자의견 조회가 승인되지 않았습니다. API 신청 상태와 실전·모의 환경을 확인하세요.'
                              + (f' ({seen})' if seen else ''))
        rows = data.get('output')
        if rows is None:
            rows = []
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise BrokerError('투자의견 응답 형식이 달라 읽지 않았습니다.')
        found = []
        for row in rows:
            try:
                target = amount(row.get('hts_goal_prc'))
            except BrokerError:
                continue
            if target <= 0:
                continue
            day = str(row.get('stck_bsop_date', ''))
            found.append({'date': day, 'target': target,
                          'opinion': str(row.get('invt_opnn', '')).strip(),
                          'prior_opinion': str(row.get('rgbf_invt_opnn', '')).strip(),
                          'member': str(row.get('mbcr_name', '')).strip()})
        found.sort(key=lambda r: r['date'], reverse=True)
        return found, len(rows)

    def quote(self, code):
        """한 종목의 현재가. 장중에는 실시간, 장 마감 뒤에는 그날 종가입니다."""
        if not re.fullmatch(r'[0-9]{6}', str(code)):
            raise BrokerError('종목코드는 숫자 6자리여야 합니다.')
        self.authorize()
        _, data = self.request(
            'GET', '/uapi/domestic-stock/v1/quotations/inquire-price',
            headers={'authorization': 'Bearer ' + self.token, 'appkey': self.key,
                     'appsecret': self.secret, 'tr_id': 'FHKST01010100', 'custtype': 'P'},
            params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': str(code)})
        if str(data.get('rt_cd')) != '0':
            raise BrokerError('현재가 조회가 승인되지 않았습니다. API 신청 상태를 확인하세요. '
                              + str(data.get('msg1', ''))[:40])
        row = data.get('output')
        if not isinstance(row, dict) or not row.get('stck_prpr'):
            raise BrokerError('현재가 응답 형식이 달라 읽지 않았습니다.')
        price = amount(row.get('stck_prpr'))
        if price <= 0:
            raise BrokerError('현재가가 0으로 와서 사용하지 않았습니다.')
        change = 0.0
        try:
            change = amount(row.get('prdy_vrss'))
        except BrokerError:
            change = 0.0
        # 부호는 따로 옵니다. 1·2는 상승, 4·5는 하락입니다.
        if str(row.get('prdy_vrss_sign', '')) in ('4', '5'):
            change = -abs(change)
        rate = None
        try:
            rate = amount(row.get('prdy_ctrt'))
        except BrokerError:
            rate = None
        cap = None
        try:
            # hts_avls는 억원 단위 시가총액입니다. 대상 종목을 고를 때 씁니다.
            cap = amount(row.get('hts_avls'))
        except BrokerError:
            cap = None
        return {'price': price, 'change': change, 'rate': rate, 'market_cap': cap,
                'name': str(row.get('hts_kor_isnm', '')).strip(),
                'at': datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M')}

    def daily(self, code, start, end, detail=False):
        """하루치 종가를 기간으로 받아옵니다. 한 번에 100거래일까지 옵니다.

        국내주식기간별시세(일/주/월/년) API입니다. 조회 전용입니다.
        detail=True면 종가 대신 시가·고가·저가·거래량까지 담은 묶음을
        돌려줍니다. 기본은 예전처럼 (날짜, 종가)입니다.

        FID_ORG_ADJ_PRC=0은 수정주가입니다. 액면분할·무상증자 자리에서 주가가
        뚝 끊기면 수익률 계산이 통째로 틀어지므로 수정주가를 씁니다.
        """
        if not re.fullmatch(r'[0-9]{6}', str(code)):
            raise BrokerError('종목코드는 숫자 6자리여야 합니다.')
        self.authorize()
        _, data = self.request(
            'GET', '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice',
            headers={'authorization': 'Bearer ' + self.token, 'appkey': self.key,
                     'appsecret': self.secret, 'tr_id': 'FHKST03010100', 'custtype': 'P'},
            params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': str(code),
                    'FID_INPUT_DATE_1': str(start), 'FID_INPUT_DATE_2': str(end),
                    'FID_PERIOD_DIV_CODE': 'D', 'FID_ORG_ADJ_PRC': '0'})
        if str(data.get('rt_cd')) != '0':
            raise BrokerError('기간별 시세 조회가 승인되지 않았습니다. API 신청 상태를 확인하세요.')
        rows = data.get('output2')
        if rows is None:
            rows = []
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise BrokerError('기간별 시세 응답 형식이 달라 읽지 않았습니다.')
        found = []
        for row in rows:
            day = str(row.get('stck_bsop_date', '')).strip()
            if not re.fullmatch(r'[0-9]{8}', day):
                continue
            try:
                close = amount(row.get('stck_clpr'))
            except BrokerError:
                continue
            if close <= 0:
                continue
            if not detail:
                found.append((day, close))
                continue
            # 거래량과 거래대금까지 함께 둡니다. 실제로 살 수 있었는지를
            # 가리려면 종가만으로는 모자랍니다.
            got = {'종가': close}
            for name, key in (('시가', 'stck_oprc'), ('고가', 'stck_hgpr'),
                              ('저가', 'stck_lwpr')):
                try:
                    price = amount(row.get(key))
                except BrokerError:
                    continue
                if price > 0:
                    got[name] = price
            for name, key in (('거래량', 'acml_vol'), ('거래대금', 'acml_tr_pbmn')):
                try:
                    got[name] = amount(row.get(key))
                except BrokerError:
                    pass
            found.append((day, got))
        found.sort(key=lambda one: one[0])
        return found

    def history(self, code, days=1200, pause=0.0, detail=False):
        """있는 만큼 거슬러 올라가며 일봉을 이어 붙입니다. 오래된 날이 먼저입니다.

        days는 거슬러 갈 한계일 뿐이고, 상장 이전에 닿으면 거기서 멈춥니다.
        그래서 넉넉히 주면 그 종목이 가진 만큼을 다 받습니다.

        쉬는 것은 request가 저장소 전체로 지키므로 여기서 또 쉬지 않습니다.
        """
        from datetime import date as _date
        last = datetime.now(ZoneInfo('Asia/Seoul')).date()
        first = last - timedelta(days=max(days, 1))
        collected = {}
        cursor = last
        for _ in range(400):
            begin = max(first, cursor - timedelta(days=140))
            rows = self.daily(code, begin.strftime('%Y%m%d'),
                              cursor.strftime('%Y%m%d'), detail=detail)
            if not rows:
                break
            before = len(collected)
            collected.update(dict(rows))
            oldest = _date(int(rows[0][0][:4]), int(rows[0][0][4:6]), int(rows[0][0][6:8]))
            # 더 거슬러 올라가지 못하면 상장 이전입니다. 거기서 멈춥니다.
            if oldest <= first or len(collected) == before:
                break
            cursor = oldest - timedelta(days=1)
            if cursor < first:
                break
            time.sleep(pause)
        return sorted(collected.items())

    def flows(self, code):
        """누가 사고 누가 팔았는지. 개인·외국인·기관을 날짜별로 받습니다.

        국내주식 투자자 API입니다. 조회 전용입니다. 이 API는 기간을 받지 않고
        최근 며칠만 돌려줍니다. 그래서 과거를 한꺼번에 받을 수는 없고, 매일
        받아 쌓아야 기간이 길어집니다.
        """
        if not re.fullmatch(r'[0-9]{6}', str(code)):
            raise BrokerError('종목코드는 숫자 6자리여야 합니다.')
        self.authorize()
        _, data = self.request(
            'GET', '/uapi/domestic-stock/v1/quotations/inquire-investor',
            headers={'authorization': 'Bearer ' + self.token, 'appkey': self.key,
                     'appsecret': self.secret, 'tr_id': 'FHKST01010900', 'custtype': 'P'},
            params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': str(code)})
        if str(data.get('rt_cd')) != '0':
            raise BrokerError('투자자 매매동향 조회가 승인되지 않았습니다. '
                              'API 신청 상태를 확인하세요.')
        rows = data.get('output')
        if rows is None:
            rows = []
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise BrokerError('투자자 매매동향 응답 형식이 달라 읽지 않았습니다.')
        found = []
        for row in rows:
            day = str(row.get('stck_bsop_date', '')).strip()
            if not re.fullmatch(r'[0-9]{8}', day):
                continue
            def number(key):
                try:
                    return amount(row.get(key))
                except BrokerError:
                    return None
            found.append({'date': day,
                          '개인': number('prsn_ntby_qty'),
                          '외국인': number('frgn_ntby_qty'),
                          '기관': number('orgn_ntby_qty'),
                          '종가': number('stck_clpr')})
        found.sort(key=lambda r: r['date'])
        return found

    # 종목별 투자자매매동향(일별). 날짜를 주면 그날까지 서른 거래일을 줍니다.
    # 투신(ivtr) · 연기금(fund) · 사모(pe_fund)가 따로 있어 과거 수급을 거슬러 받을 수 있습니다.
    INVESTORS = (('개인', 'prsn_ntby_qty'), ('외국인', 'frgn_ntby_qty'), ('기관', 'orgn_ntby_qty'),
                 ('투신', 'ivtr_ntby_qty'), ('연기금', 'fund_ntby_qty'), ('사모', 'pe_fund_ntby_vol'))

    def investor_daily(self, code, day):
        """그날까지 서른 거래일의 투자자별 순매수(주)와 종가. 오래된 날이 먼저입니다. 조회 전용입니다."""
        if not re.fullmatch(r'[0-9]{6}', str(code)) or not re.fullmatch(r'[0-9]{8}', str(day)):
            raise BrokerError('종목코드는 숫자 6자리, 날짜는 8자리여야 합니다.')
        self.authorize()
        _, data = self.request(
            'GET', '/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily',
            headers={'authorization': 'Bearer ' + self.token, 'appkey': self.key,
                     'appsecret': self.secret, 'tr_id': 'FHPTJ04160001', 'custtype': 'P'},
            params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': str(code),
                    'FID_INPUT_DATE_1': str(day), 'FID_ORG_ADJ_PRC': '', 'FID_ETC_CLS_CODE': ''})
        if str(data.get('rt_cd')) != '0':
            # 정해진 꼴의 코드만 붙입니다. 응답 본문은 옮기지 않습니다.
            code_seen = str(data.get('msg_cd') or '').strip()
            code_seen = code_seen if re.fullmatch(r'[A-Z]{2,4}[0-9]{3,6}', code_seen) else ''
            raise BrokerError('투자자 매매동향(일별) 조회가 거절되었습니다.' + (f' · {code_seen}' if code_seen else ''))
        rows = data.get('output2')
        if rows is None:
            rows = []
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise BrokerError('투자자 매매동향(일별) 응답 형식이 달라 읽지 않았습니다.')
        found = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            when = str(row.get('stck_bsop_date', '')).strip()
            if not re.fullmatch(r'[0-9]{8}', when):
                continue
            got = {'date': when}
            for name, key in self.INVESTORS + (('종가', 'stck_clpr'),):
                try:
                    got[name] = amount(row.get(key))
                except BrokerError:
                    got[name] = None
            found.append(got)
        found.sort(key=lambda r: r['date'])
        return found

    def _market_rows(self, path, tr_id, params, what, key=None):
        """시세 쪽 조회 한 번. 줄 목록(dict)만 돌려줍니다. 조회 전용입니다."""
        return self._market_page(path, tr_id, params, what, key)[0]

    def _market_page(self, path, tr_id, params, what, key=None, continuation=''):
        """시세 쪽 조회 한 쪽. (줄 목록, 다음 쪽 있음)을 돌려줍니다. 다음 쪽은 continuation='N'으로 묻습니다. 조회 전용입니다."""
        self.authorize()
        response, data = self.request('GET', path, headers={
            'authorization': 'Bearer ' + self.token, 'appkey': self.key,
            'appsecret': self.secret, 'tr_id': tr_id, 'custtype': 'P', 'tr_cont': continuation}, params=params)
        more = getattr(response, 'headers', {}).get('tr_cont') in ('F', 'M')
        if str(data.get('rt_cd')) != '0':
            code_seen = str(data.get('msg_cd') or '').strip()
            code_seen = code_seen if re.fullmatch(r'[A-Z]{2,4}[0-9]{3,6}', code_seen) else ''
            raise BrokerError(f'{what} 조회가 거절되었습니다.' + (f' · {code_seen}' if code_seen else ''))
        if key:
            rows = data.get(key)
        else:
            rows = data.get('output2') if data.get('output2') is not None else data.get('output')
        if rows is None:
            rows = []
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise BrokerError(f'{what} 응답 형식이 달라 읽지 않았습니다.')
        return [r for r in rows if isinstance(r, dict)], more

    @staticmethod
    def _numbers(row, names):
        got = {}
        for name, key in names:
            try:
                got[name] = amount(row.get(key))
            except BrokerError:
                got[name] = None
        return got

    @staticmethod
    def _check(code=None, *days):
        if code is not None and not re.fullmatch(r'[0-9]{6}', str(code)):
            raise BrokerError('종목코드는 숫자 6자리여야 합니다.')
        if not all(re.fullmatch(r'[0-9]{8}', str(d)) for d in days):
            raise BrokerError('날짜는 숫자 8자리여야 합니다.')

    def _dated(self, rows, date_key, names):
        found = []
        for row in rows:
            day = str(row.get(date_key, '')).strip()
            if re.fullmatch(r'[0-9]{8}', day):
                found.append({'date': day, **self._numbers(row, names)})
        return sorted(found, key=lambda r: r['date'])

    def program_daily(self, code, day):
        """종목별 프로그램매매추이(일별, FHPPG04650201). day까지 서른 거래일. 오래된 날이 먼저."""
        self._check(code, day)
        rows = self._market_rows('/uapi/domestic-stock/v1/quotations/program-trade-by-stock-daily', 'FHPPG04650201',
                                 {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': str(code),
                                  'FID_INPUT_DATE_1': str(day)}, '프로그램매매 일별', key='output')
        return self._dated(rows, 'stck_bsop_date', (
            ('순매수량', 'whol_smtn_ntby_qty'), ('순매수대금', 'whol_smtn_ntby_tr_pbmn'),
            ('매수량', 'whol_smtn_shnu_vol'), ('매도량', 'whol_smtn_seln_vol'),
            ('거래량', 'acml_vol'), ('종가', 'stck_clpr')))

    def loan_daily(self, code, start, end):
        """종목별 일별 대차거래추이(HHPST074500C0). 기간 안 날마다 신규·상환·잔고 주수와 잔고 금액."""
        self._check(code, start, end)
        rows = self._market_rows('/uapi/domestic-stock/v1/quotations/daily-loan-trans', 'HHPST074500C0',
                                 {'MRKT_DIV_CLS_CODE': '3', 'MKSC_SHRN_ISCD': str(code), 'START_DATE': str(start),
                                  'END_DATE': str(end), 'CTS': ''}, '대차거래 일별', key='output1')
        return self._dated(rows, 'bsop_date', (
            ('신규주수', 'new_stcn'), ('상환주수', 'rdmp_stcn'), ('잔고주수', 'rmnd_stcn'), ('잔고금액', 'rmnd_amt'),
            ('거래량', 'acml_vol'), ('종가', 'stck_prpr')))

    def trade_side_daily(self, code, start, end):
        """종목별 일별 매수·매도 체결량(FHKST03010800). 매수 쪽이 먼저 부른 체결량과 매도 쪽 체결량."""
        self._check(code, start, end)
        rows = self._market_rows('/uapi/domestic-stock/v1/quotations/inquire-daily-trade-volume', 'FHKST03010800',
                                 {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': str(code), 'FID_PERIOD_DIV_CODE': 'D',
                                  'FID_INPUT_DATE_1': str(start), 'FID_INPUT_DATE_2': str(end)}, '매수·매도 체결량',
                                 key='output2')
        return self._dated(rows, 'stck_bsop_date', (('매수체결량', 'total_shnu_qty'), ('매도체결량', 'total_seln_qty')))

    def index_daily(self, index, start, end):
        """업종(지수) 기간별 시세(FHKUP03500100). 0001 코스피 · 1001 코스닥. 한 번에 약 50일."""
        self._check(None, start, end)
        if not re.fullmatch(r'[0-9]{4}', str(index)):
            raise BrokerError('지수 코드는 숫자 4자리여야 합니다.')
        rows = self._market_rows('/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice', 'FHKUP03500100',
                                 {'FID_COND_MRKT_DIV_CODE': 'U', 'FID_INPUT_ISCD': str(index), 'FID_INPUT_DATE_1': str(start),
                                  'FID_INPUT_DATE_2': str(end), 'FID_PERIOD_DIV_CODE': 'D'}, '지수 일별', key='output2')
        return self._dated(rows, 'stck_bsop_date', (
            ('시가', 'bstp_nmix_oprc'), ('고가', 'bstp_nmix_hgpr'), ('저가', 'bstp_nmix_lwpr'),
            ('종가', 'bstp_nmix_prpr'), ('거래량', 'acml_vol'), ('거래대금', 'acml_tr_pbmn')))

    def market_investor_daily(self, market, day):
        """시장별 투자자매매동향(일별, FHPTJ04040000). day까지 약 300거래일, 투자자별 순매수 대금."""
        self._check(None, day)
        index, short = {'KSP': ('0001', 'KSP'), 'KSQ': ('1001', 'KSQ')}[market]
        rows = self._market_rows('/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market', 'FHPTJ04040000',
                                 {'FID_COND_MRKT_DIV_CODE': 'U', 'FID_INPUT_ISCD': index, 'FID_INPUT_DATE_1': str(day),
                                  'FID_INPUT_ISCD_1': short, 'FID_INPUT_DATE_2': str(day), 'FID_INPUT_ISCD_2': index},
                                 '시장별 투자자 일별', key='output')
        return self._dated(rows, 'stck_bsop_date', (
            ('개인', 'prsn_ntby_tr_pbmn'), ('외국인', 'frgn_ntby_tr_pbmn'), ('기관', 'orgn_ntby_tr_pbmn'),
            ('투신', 'ivtr_ntby_tr_pbmn'), ('연기금', 'fund_ntby_tr_pbmn'), ('사모', 'pe_fund_ntby_tr_pbmn'),
            ('금융투자', 'scrt_ntby_tr_pbmn'), ('보험', 'insu_ntby_tr_pbmn'), ('은행', 'bank_ntby_tr_pbmn'),
            ('지수', 'bstp_nmix_prpr')))

    def market_program_daily(self, market, start, end):
        """프로그램매매 종합현황(일별, FHPPG04600001). K 코스피 · Q 코스닥. 차익·비차익 순매수 대금."""
        self._check(None, start, end)
        if market not in ('K', 'Q'):
            raise BrokerError('시장은 K 또는 Q여야 합니다.')
        rows = self._market_rows('/uapi/domestic-stock/v1/quotations/comp-program-trade-daily', 'FHPPG04600001',
                                 {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_MRKT_CLS_CODE': market, 'FID_INPUT_DATE_1': str(start),
                                  'FID_INPUT_DATE_2': str(end)}, '프로그램매매 종합 일별', key='output')
        return self._dated(rows, 'stck_bsop_date', (
            ('차익순매수', 'arbt_smtn_ntby_tr_pbmn'), ('비차익순매수', 'nabt_smtn_ntby_tr_pbmn'),
            ('전체순매수', 'whol_smtn_ntby_tr_pbmn')))

    def market_funds(self, day):
        """국내 증시자금 종합(FHKST649100C0). day까지 약 100거래일: 고객예탁금 · 신용융자잔고 · 미수금 등."""
        self._check(None, day)
        rows = self._market_rows('/uapi/domestic-stock/v1/quotations/mktfunds', 'FHKST649100C0',
                                 {'FID_INPUT_DATE_1': str(day)}, '증시자금 종합', key='output')
        return self._dated(rows, 'bsop_date', (
            ('고객예탁금', 'cust_dpmn_amt'), ('신용융자잔고', 'crdt_loan_rmnd'), ('미수금', 'uncl_amt'),
            ('대주잔고', 'secu_lend_amt'), ('선물예수금', 'futs_tfam_amt'), ('MMF', 'mmf_amt'), ('지수', 'bstp_nmix_prpr')))

    def financial_ratio(self, code, quarterly=False):
        """재무비율(FHKST66430300). 연간(2004~) 또는 분기(2019~): ROE · EPS · BPS · 매출/영업이익/순이익 증가율 · 부채비율."""
        self._check(code)
        rows = self._market_rows('/uapi/domestic-stock/v1/finance/financial-ratio', 'FHKST66430300',
                                 {'FID_DIV_CLS_CODE': '1' if quarterly else '0', 'fid_cond_mrkt_div_code': 'J',
                                  'fid_input_iscd': str(code)}, '재무비율', key='output')
        found = []
        for row in rows:
            ym = str(row.get('stac_yymm', '')).strip()
            if re.fullmatch(r'[0-9]{6}', ym):
                found.append({'결산월': ym, **self._numbers(row, (
                    ('매출증가율', 'grs'), ('영업이익증가율', 'bsop_prfi_inrt'), ('순이익증가율', 'ntin_inrt'),
                    ('ROE', 'roe_val'), ('EPS', 'eps'), ('SPS', 'sps'), ('BPS', 'bps'), ('유보율', 'rsrv_rate'),
                    ('부채비율', 'lblt_rate')))})
        return sorted(found, key=lambda r: r['결산월'])

    def short_daily(self, code, start, end):
        """공매도 일별추이(FHPST04830000). 기간 안의 날마다 공매도 수량·비중과 거래량. 오래된 날이 먼저."""
        if not re.fullmatch(r'[0-9]{6}', str(code)) or not all(re.fullmatch(r'[0-9]{8}', str(d)) for d in (start, end)):
            raise BrokerError('종목코드는 숫자 6자리, 날짜는 8자리여야 합니다.')
        rows = self._market_rows('/uapi/domestic-stock/v1/quotations/daily-short-sale', 'FHPST04830000',
                                 {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': str(code),
                                  'FID_INPUT_DATE_1': str(start), 'FID_INPUT_DATE_2': str(end)}, '공매도 일별추이')
        found = []
        for row in rows:
            day = str(row.get('stck_bsop_date', '')).strip()
            if re.fullmatch(r'[0-9]{8}', day):
                found.append({'date': day, **self._numbers(row, (
                    ('공매도량', 'ssts_cntg_qty'), ('공매도비중', 'ssts_vol_rlim'), ('거래량', 'acml_vol'),
                    ('종가', 'stck_clpr')))})
        return sorted(found, key=lambda r: r['date'])

    def credit_daily(self, code, day):
        """신용잔고 일별추이(FHPST04760000). 그 결제일까지 서른 거래일. 오래된 날이 먼저(매매일 기준)."""
        if not re.fullmatch(r'[0-9]{6}', str(code)) or not re.fullmatch(r'[0-9]{8}', str(day)):
            raise BrokerError('종목코드는 숫자 6자리, 날짜는 8자리여야 합니다.')
        rows = self._market_rows('/uapi/domestic-stock/v1/quotations/daily-credit-balance', 'FHPST04760000',
                                 {'fid_cond_mrkt_div_code': 'J', 'fid_cond_scr_div_code': '20476',
                                  'fid_input_iscd': str(code), 'fid_input_date_1': str(day)}, '신용잔고 일별추이')
        found = []
        for row in rows:
            when = str(row.get('deal_date', '')).strip()
            if re.fullmatch(r'[0-9]{8}', when):
                found.append({'date': when, **self._numbers(row, (
                    ('잔고율', 'whol_loan_rmnd_rate'), ('잔고주수', 'whol_loan_rmnd_stcn'),
                    ('공여율', 'whol_loan_gvrt'), ('신규주수', 'whol_loan_new_stcn'), ('상환주수', 'whol_loan_rdmp_stcn')))})
        return sorted(found, key=lambda r: r['date'])

    def balance(self):
        self.authorize()
        rows, seen = [], set()
        fk = nk = continuation = ''
        summary = {}
        for _ in range(100):
            response, data = self.request('GET', '/uapi/domestic-stock/v1/trading/inquire-balance',
                headers={'authorization': 'Bearer ' + self.token, 'appkey': self.key, 'appsecret': self.secret,
                         'tr_id': 'TTTC8434R' if self.mode == 'real' else 'VTTC8434R', 'custtype': 'P', 'tr_cont': continuation},
                params={'CANO': self.cano, 'ACNT_PRDT_CD': self.product, 'AFHR_FLPR_YN': 'N', 'OFL_YN': '',
                        'INQR_DVSN': '02', 'UNPR_DVSN': '01', 'FUND_STTL_ICLD_YN': 'N',
                        'FNCG_AMT_AUTO_RDPT_YN': 'N', 'PRCS_DVSN': '00', 'CTX_AREA_FK100': fk, 'CTX_AREA_NK100': nk})
            if str(data.get('rt_cd')) != '0':
                raise BrokerError('잔고 조회가 승인되지 않았습니다. 계좌·상품코드와 API 신청 상태를 확인하세요.')
            if not isinstance(data.get('output1'), list) or not isinstance(data.get('output2'), list):
                raise BrokerError('잔고 응답 형식이 달라 조회를 중단했습니다.')
            rows.extend(data['output1'])
            if data['output2'] and not summary:
                summary = data['output2'][0]
            if response.headers.get('tr_cont') not in ('F', 'M'):
                break
            fk, nk = data.get('ctx_area_fk100', '').strip(), data.get('ctx_area_nk100', '').strip()
            if not nk or (fk, nk) in seen:
                raise BrokerError('잔고의 다음 페이지를 확인하지 못했습니다. 일부 잔고를 전체로 표시하지 않습니다.')
            seen.add((fk, nk))
            continuation = 'N'
            time.sleep(0.6)
        else:
            raise BrokerError('잔고 페이지 한도를 초과했습니다. 조회 범위를 확인하세요.')
        positions = []
        codes = set()
        for row in rows:
            quantity = amount(row.get('hldg_qty'))
            if quantity <= 0:
                continue
            code = str(row.get('pdno', ''))
            if code in codes:
                raise BrokerError('종목별 잔고에 중복 응답이 있어 확인이 필요합니다.')
            codes.add(code)
            positions.append({'code': code, 'name': row.get('prdt_name', code), 'quantity': quantity,
                              'average_cost': amount(row.get('pchs_avg_pric')), 'price': amount(row.get('prpr')),
                              'value': amount(row.get('evlu_amt')), 'pnl': amount(row.get('evlu_pfls_amt'))})
        total = sum(p['value'] for p in positions)
        for position in positions:
            position['weight'] = position['value'] / total * 100 if total > 0 else 0
        return {'positions': positions, 'value': total, 'pnl': sum(p['pnl'] for p in positions),
                'cash': amount(summary['dnca_tot_amt']) if summary.get('dnca_tot_amt') not in (None, '') else None,
                'mode': self.mode, 'fetched': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()}


_market = None


def market():
    """시세·투자의견 전용 연결. 계좌번호 없이 쓰고 토큰을 재사용합니다."""
    global _market
    key = os.getenv('KIS_APP_KEY', '').strip()
    if _market is None or _market.key != key or _market.mode != os.getenv('KIS_ENV', 'demo').strip():
        _market = KIS(account=False)
    return _market
