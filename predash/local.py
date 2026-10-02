"""PlanX 저장소에 이미 쌓아 둔 자료로 교실 화면을 채우는 대체 자료(2026-10-02 · 사용자 "미비된 것 전부 조치").

공공데이터포털 시세 키나 한투 연결이 없거나 거절돼도 관심종목 · 투자 근거가 비지 않게,
매일 밤 GitHub 작업이 받아 두는 한투 일봉(price-data · kosdaq-data) · 투자자 수급(investor-data) · 종목 이름을 씁니다.
모두 '전날 장 마감까지' 자료입니다. 키나 계좌 정보는 쓰지 않습니다.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = '저장소 한투 일봉(전날 장 마감까지)'


def _load(rel):
    try:
        return json.loads((ROOT / rel).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _names():
    found = dict(_load('study/names.json') or {})
    kq = _load('study/kosdaq_codes.json') or {}
    found.update({c: n for c, n in (kq.get('names') or {}).items() if c not in found})
    return found


def name_of(code):
    body = _load(f'price-data/{code}.json') or {}
    return body.get('name') or _names().get(code) or code


def market_of(code):
    """KOSPI · KOSDAQ · None(모름)."""
    tag = (_load('hourly-data/suffix.json') or {}).get(code)
    if tag == 'KS':
        return 'KOSPI'
    if tag == 'KQ':
        return 'KOSDAQ'
    if code in set((_load('study/kosdaq_codes.json') or {}).get('codes') or []):
        return 'KOSDAQ'
    if (ROOT / 'price-data' / f'{code}.json').exists():
        return 'KOSPI'          # 앱 대상 일봉(price-data)은 코스피 시총 위쪽 종목
    return None


def closes(code):
    """[(YYYYMMDD, 종가)] 오래된 것부터. price-data 먼저, 없으면 코스닥 일봉."""
    body = _load(f'price-data/{code}.json')
    if body and body.get('closes'):
        return [(str(d), float(c)) for d, c in body['closes'] if c]
    body = _load(f'kosdaq-data/{code}.json')
    if body and body.get('rows'):
        cols = body.get('cols') or []
        i = cols.index('종가') if '종가' in cols else 4
        return [(str(r[0]), float(r[i])) for r in body['rows'] if r[i]]
    return []


def price_rows(code, asof, days=60):
    """공공데이터포털 일별 시세와 같은 꼴(srtnCd · basDt · clpr · itmsNm · mrktCtg)로 최근 days일 돌려줌."""
    if not re.fullmatch(r'[0-9]{6}', str(code)):
        return []
    end = asof.strftime('%Y%m%d') if isinstance(asof, date) else str(asof)
    begin = ((asof if isinstance(asof, date) else datetime.strptime(end, '%Y%m%d').date()) - timedelta(days=days)).strftime('%Y%m%d')
    name, market = name_of(code), market_of(code)
    rows = []
    for d, c in closes(code):
        if begin <= d <= end:
            row = {'srtnCd': code, 'basDt': d, 'clpr': str(int(round(c))), 'itmsNm': name}
            if market:
                row['mrktCtg'] = market
            rows.append(row)
    return rows


def investor_flow(code, today):
    """투자자 순매수 수량(개인 · 외국인 · 기관)을 교실 수급 꼴로(predash.flow.summarize_flow)."""
    body = _load(f'investor-data/{code}.json') or {}
    cols = body.get('cols') or []
    if not body.get('rows') or not all(c in cols for c in ('date', '개인', '외국인', '기관')):
        return None
    at = {c: cols.index(c) for c in ('date', '개인', '외국인', '기관')}
    rows = []
    for r in body['rows'][-30:]:
        if any(r[at[c]] is None for c in ('개인', '외국인', '기관')):
            continue
        rows.append({'stck_bsop_date': str(r[at['date']]), 'prsn_ntby_qty': int(r[at['개인']]),
                     'frgn_ntby_qty': int(r[at['외국인']]), 'orgn_ntby_qty': int(r[at['기관']])})
    from predash.flow import summarize_flow
    got = summarize_flow(rows, today)
    if got is None and rows:
        # 주말 · 연휴로 5일이 넘었으면 기준을 마지막 날로(그래도 표시는 그 날짜 그대로)
        last = datetime.strptime(rows[-1]['stck_bsop_date'], '%Y%m%d').date()
        if (today - last).days <= 10:
            got = summarize_flow(rows, last)
    return got


def planx_codes():
    """PlanX 오늘의 후보(1일봉 · 1시간봉 · 15분봉 후보와 1개 모자란 종목) 코드 — 관심종목 처음 목록용."""
    found = []
    for rel, keys in (('daily-live/today.json', ('candidates', 'near')), ('hourly-live/plan.json', ('candidates', 'near')),
                      ('hourly-live/near-now.json', ('picks', 'near')), ('m15-live/near-now.json', ('picks', 'near'))):
        body = _load(rel) or {}
        for k in keys:
            for one in body.get(k) or []:
                code = str((one or {}).get('code', ''))
                if re.fullmatch(r'[0-9]{6}', code) and code not in found:
                    found.append(code)
    return found


def index_rows(market_code):
    """코스피(0001) · 코스닥(1001) 일별 지수를 한투 지수 일봉 꼴(stck_bsop_date · bstp_nmix_prpr)로."""
    name = 'KOSPI' if market_code == '0001' else 'KOSDAQ'
    body = _load(f'market-data/index_{name}.json') or {}
    return [{'stck_bsop_date': str(r['date']), 'bstp_nmix_prpr': str(r['종가'])}
            for r in (body.get('rows') or [])[-80:] if r.get('date') and r.get('종가')]


def last_price(code):
    """(종가, YYYYMMDD, 이름) — 매매 연습 체결 기준가용. 없으면 None."""
    got = closes(code)
    if not got:
        return None
    d, c = got[-1]
    return int(round(c)), d, name_of(code)


def search(query):
    """저장소 종목 이름표에서 찾기(DART · 공공데이터 검색이 안 될 때)."""
    q = re.sub(r'\s+', '', str(query or '')).casefold()
    if not q:
        return []
    names = _names()
    hits = [{'code': c, 'name': n} for c, n in names.items() if q in re.sub(r'\s+', '', n).casefold() or q == c]
    exact = [h for h in hits if q in (h['code'], re.sub(r'\s+', '', h['name']).casefold())]
    return exact or hits[:30]
