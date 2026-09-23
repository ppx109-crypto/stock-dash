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

    def request(self, method, path, **kwargs):
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
        if not re.fullmatch(r'[0-9]{6}', str(code)):
            raise BrokerError('종목코드는 숫자 6자리여야 합니다.')
        self.authorize()
        today = datetime.now(ZoneInfo('Asia/Seoul')).date()
        begin = today - timedelta(days=max(days, 1))
        _, data = self.request(
            'GET', '/uapi/domestic-stock/v1/quotations/invest-opinion',
            headers={'authorization': 'Bearer ' + self.token, 'appkey': self.key,
                     'appsecret': self.secret, 'tr_id': 'FHKST663300C0', 'custtype': 'P'},
            params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_COND_SCR_DIV_CODE': '16633',
                    'FID_INPUT_ISCD': str(code), 'FID_INPUT_DATE_1': begin.strftime('%Y%m%d'),
                    'FID_INPUT_DATE_2': today.strftime('%Y%m%d')})
        if str(data.get('rt_cd')) != '0':
            raise BrokerError('투자의견 조회가 승인되지 않았습니다. API 신청 상태와 실전·모의 환경을 확인하세요. '
                              + str(data.get('msg1', ''))[:40])
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
        return found

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

    def history(self, code, days=1200, pause=0.2, detail=False):
        """있는 만큼 거슬러 올라가며 일봉을 이어 붙입니다. 오래된 날이 먼저입니다.

        days는 거슬러 갈 한계일 뿐이고, 상장 이전에 닿으면 거기서 멈춥니다.
        그래서 넉넉히 주면 그 종목이 가진 만큼을 다 받습니다.
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
