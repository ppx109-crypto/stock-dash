import hashlib
from pathlib import Path
import json
import re
from datetime import date

import pandas as pd
import streamlit as st

from ui_v2 import hero, card
from automatic import brief
from bi_view import theme, overview, detail, peers_chart
from chat_research import published, parse_bundle, trends, growth, request_text
from dashboard_ui import (SORTIE_RULES, M15_RULES, IDLE_RULES, fold, idle_panel, sortie_panel, GROUP_RULES, GROUP_TITLES, NAME_A, NAME_B, RULE_TEXT, SHOWN_PER_GROUP,
                          CLOSE_RULES, close_panel, ledger_mini, top_bar, kospi_box, lights_box, frame_open, near_panel, as_day,
                          board_basis,
                          chip_label, close_frame, frame, group_buckets, header,
                          live_note, period_label, price_now, section, slot_head,
                          stock_cards)
import final_group
import market
import broker_kis


@st.cache_data(ttl=60, show_spinner=False)
def live_quote(code):
    """현재가 한 건. 장중에는 1분마다 새로 받아 실시간에 가깝게 따라갑니다.

    키가 없거나 조회가 막히면 None을 돌려주고, 화면은 그대로 종가를 씁니다.
    """
    try:
        return broker_kis.market().quote(code)
    except broker_kis.BrokerError:
        return None


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def broker_targets(code):
    """증권사 목표주가. 하루에 몇 건 나오지 않으므로 6시간 두고 씁니다."""
    try:
        # 화면은 최근 석 달만 씁니다. 그 안에 아무것도 없는 종목을 위해 한 해치를
        # 받아 두고, 넓혀 쓸 때는 몇 달치인지 화면에 밝힙니다.
        return broker_kis.market().opinions(code, days=365)
    except broker_kis.BrokerError:
        return None


# 아래 네 탭(어떤 기업인가요? · 실적은 어떤가요? · 주가 흐름 · 가격과 확인 사항)은 누를 때
# 그 종목의 최신 자료를 받아 옵니다. 누른 탭 것만 받고, 같은 종목을 다시 누르면 잠시 모아 둔
# 것을 씁니다. 공시·결산은 하루에 몇 번 바뀌지 않아 30분, 주가·수급은 5분 둡니다.
FRESH_FAILED = '최신 자료를 받지 못했습니다. 잠시 뒤 탭을 다시 눌러 보세요. 아래는 저장된 조사 결과입니다.'


def _is_code(code):
    return bool(re.fullmatch(r'[0-9]{6}', str(code or '')))


@st.cache_resource(show_spinner=False)
def _official():
    """DART 기업 목록은 크므로 한 번 받은 것을 계속 씁니다."""
    from providers import Official
    return Official()


@st.cache_data(ttl=1800, show_spinner=False)
def _fresh_report(code):
    return _official().automatic(code)


def fresh_report(code):
    """최신 공시·결산. (자료, 실패 안내) 둘 중 하나만 채워 돌려줍니다."""
    from providers import DataError
    with st.spinner('최신 공시·실적을 받는 중'):
        try:
            return _fresh_report(code), None
        except DataError as error:
            # 우리가 만든 안내문만 담깁니다. 응답 본문은 싣지 않습니다.
            first = str(error)[:80]
        except Exception:
            first = FRESH_FAILED
        # 시세 쪽이 막혀도 DART만으로 받을 수 있는 것은 받아 옵니다.
        try:
            return _fresh_filings(code), None
        except Exception:
            return None, first


@st.cache_data(ttl=1800, show_spinner=False)
def _fresh_filings(code):
    return _official().filings(code)


@st.cache_data(ttl=300, show_spinner=False)
def fresh_closes(code):
    """최근 약 1년 일봉 종가. 증권사 수정주가를 먼저 쓰고, 막히면 공공데이터 시세를 씁니다."""
    from datetime import timedelta
    from urllib.parse import unquote
    import os
    today = date.today()
    try:
        rows = broker_kis.market().history(code, days=400)
        if rows:
            return rows, '증권사 수정주가'
    except broker_kis.BrokerError:
        pass
    key = unquote(os.getenv('DATA_GO_KR_SERVICE_KEY', '').strip())
    if not key:
        return [], None
    try:
        return market.daily_closes(code, key, span_days=400), '공공데이터포털 시세(수정주가 아님)'
    except Exception:
        return [], None


@st.cache_data(ttl=300, show_spinner=False)
def fresh_flows(code):
    """최근 며칠 외국인·기관·개인 순매수(주)."""
    try:
        return broker_kis.market().flows(code)
    except broker_kis.BrokerError:
        return []


def years_table(report):
    """결산 3개년 매출·영업이익(억원)과 전년 대비 변화."""
    table, prev = [], None
    for year in report.get('years') or []:
        rev, pro = year.get('revenue'), year.get('profit')
        table.append({'결산연도': str(year.get('year', '')),
                      '매출(억원)': f'{rev:,.0f}' if rev is not None else '—',
                      '매출 변화': growth(rev, prev['revenue']) if prev and rev is not None and prev.get('revenue') is not None else '—',
                      '영업이익(억원)': f'{pro:,.0f}' if pro is not None else '—',
                      '영업이익 변화': growth(pro, prev['profit']) if prev and pro is not None and prev.get('profit') is not None else '—'})
        prev = year
    return table


def flow_sums(rows, days=5):
    """최근 days거래일 순매수 합계. 값이 빠진 날은 건너뜁니다."""
    recent = rows[-days:]
    sums = {}
    for who in ('외국인', '기관', '개인'):
        values = [r.get(who) for r in recent if r.get(who) is not None]
        sums[who] = sum(values) if values else None
    return sums, (recent[0]['date'] if recent else None), (recent[-1]['date'] if recent else None)


def _day(text):
    text = str(text or '')
    return f'{text[:4]}-{text[4:6]}-{text[6:8]}' if len(text) == 8 and text.isdigit() else text


def latest_company(code):
    report, problem = fresh_report(code)
    with st.container(border=True):
        st.markdown('**최신 공시 기준 · 방금 받아 온 자료**')
        if problem:
            st.caption(problem); return
        company = report.get('company') or {}
        facts = [f"설립 {_day(company['est_dt'])}" if company.get('est_dt') else '',
                 f"결산월 {company['acc_mt']}월" if company.get('acc_mt') else '',
                 f"업종코드 {company['induty_code']}" if company.get('induty_code') else '']
        st.caption(' · '.join(f for f in facts if f) + f" · 받은 날 {report.get('fetched', '')}")
        excerpt = (report.get('business_excerpt') or '').strip()
        if excerpt:
            st.write(excerpt[:600] + ('…' if len(excerpt) > 600 else ''))
            if len(excerpt) > 600:
                with st.expander('사업보고서 원문 더 보기'):
                    st.write(excerpt[:6000])
        if company.get('hm_url'):
            url = company['hm_url'] if company['hm_url'].startswith('http') else 'https://' + company['hm_url']
            st.link_button('회사 홈페이지', url)
        for d in (report.get('disclosures') or [])[:5]:
            st.markdown(f"- [{d['title'].strip()}]({d['url']}) · {_day(d['date'])}")


def latest_results(code):
    report, problem = fresh_report(code)
    with st.container(border=True):
        st.markdown('**최신 결산 실적 · 방금 받아 온 자료**')
        if problem:
            st.caption(problem); return
        st.caption(f"DART 사업보고서 · {'연결' if report.get('basis') == 'CFS' else '별도'} 기준 · 받은 날 {report.get('fetched', '')}")
        st.dataframe(years_table(report), hide_index=True, width='stretch')
        info = brief(report)
        if info.get('margin') is not None:
            st.caption(f"최근 결산 영업이익률 {info['margin']:.1f}% · {info['growth']}")


def latest_prices(code):
    with st.container(border=True):
        st.markdown('**최신 주가 흐름 · 방금 받아 온 자료**')
        with st.spinner('최신 주가를 받는 중'):
            rows, source = fresh_closes(code)
            flows = fresh_flows(code)
        if rows:
            chart = pd.DataFrame(rows, columns=['date', '종가'])
            chart['date'] = pd.to_datetime(chart['date'])
            chart = chart.set_index('date')
            chart['20일 평균'] = chart['종가'].rolling(20).mean()
            chart['60일 평균'] = chart['종가'].rolling(60).mean()
            st.caption(f"{source} · 마지막 거래일 {_day(rows[-1][0])} · 종가 {rows[-1][1]:,.0f}원")
            st.line_chart(chart.tail(250))
        else:
            st.caption(FRESH_FAILED)
        if flows:
            sums, begin, end = flow_sums(flows)
            st.caption(f'최근 순매수 합계 · {_day(begin)} ~ {_day(end)} · 단위 주')
            cols = st.columns(3)
            for col, who in zip(cols, ('외국인', '기관', '개인')):
                col.metric(who, '—' if sums[who] is None else f'{sums[who]:+,.0f}')


def latest_price_check(code):
    with st.container(border=True):
        st.markdown('**지금 가격 · 방금 받아 온 자료**')
        quote = live_quote(code)
        if quote:
            rate = f" ({quote['rate']:+.2f}%)" if quote.get('rate') is not None else ''
            st.metric('현재가', f"{quote['price']:,.0f}원", f"{quote['change']:+,.0f}원{rate}")
            st.caption(f"받은 시각 {quote['at']} · 장중에는 실시간, 장 마감 뒤에는 그날 종가")
        report, problem = fresh_report(code)
        if report:
            fair = brief(report).get('fair')
            if fair:
                a, b, c = st.columns(3)
                for col, key, label in [(a, 'low', '낮은 참고가'), (b, 'base', '기본 참고가'), (c, 'high', '높은 참고가')]:
                    col.metric(label, f'{fair[key]:,.0f}원')
                st.caption('과거 결산 발표 뒤의 시가총액 ÷ 영업이익 배수를 최근 결산 이익에 적용한 참고 가격입니다.')
            elif report.get('no_price'):
                st.caption('참고 가격 보류 · 시세 자료를 받지 못해 과거 배수로 셈할 수 없습니다.')
            else:
                st.caption('참고 가격 보류 · ' + brief(report)['fair_reason'])
        elif problem and not quote:
            st.caption(problem)
        targets = broker_targets(code) or []
        if targets:
            st.dataframe([{'날짜': _day(t['date']), '증권사': t['member'], '의견': t['opinion'],
                           '목표가': f"{t['target']:,.0f}원"} for t in targets[:5]],
                         hide_index=True, width='stretch')


def link_codes(store, state, known):
    """이름이 같은 조사 결과가 있으면 임시 코드를 공식 종목코드로 바꿉니다."""
    by_name = {}
    for r in known.values():
        by_name.setdefault(r['name'].strip().casefold(), r['code'])
    fixes = {s['code']: by_name[s['name'].strip().casefold()] for s in state.get('stocks', [])
             if s['code'].startswith('pending-') and s['name'].strip().casefold() in by_name}
    if not fixes: return False
    def update(data):
        merged = {}
        for stock in data.get('stocks', []):
            stock = {**stock, 'code': fixes.get(stock['code'], stock['code'])}
            merged[stock['code']] = {**merged.get(stock['code'], {}), **stock}
        data['stocks'] = list(merged.values())
    try:
        store.change(update)
    except Exception:
        return False
    return True


# 판정 규칙을 바꾸면 캐시에 남은 옛 등급이 그대로 보입니다. 규칙 이름을 캐시
# 열쇠에 넣어, 규칙이 바뀌면 옛 값이 저절로 버려지게 합니다.
RULES = 'final-a-b-shortfall-v2'


SHOW_FILL = False      # '자료 받기' 칸을 다시 보이려면 True

RAW = "https://raw.githubusercontent.com/ppx109-crypto/stock-dash/main/"


@st.cache_data(ttl=60, show_spinner=False)
def repo_json_live(path):
    """모의투자 거래 내역처럼 자주 바뀌는 파일: 1분마다 새로 읽음."""
    return repo_json.__wrapped__(path)


@st.fragment(run_every=60)
@st.cache_data(ttl=300, show_spinner=False)
def kospi_last():
    """코스피 마지막 값. 한투에서 바로 받고(5분마다), 못 받으면 저장소에 모아 둔 일별 자료를 씁니다."""
    from datetime import datetime as _dt, timedelta as _td
    from zoneinfo import ZoneInfo
    now = _dt.now(ZoneInfo('Asia/Seoul'))
    rows, src = [], '한국투자증권'
    try:
        import broker_kis
        rows = broker_kis.market().index_daily('0001', (now - _td(days=14)).strftime('%Y%m%d'), now.strftime('%Y%m%d'))
    except Exception:
        rows = []
    if not rows:
        rows, src = ((repo_json('market-data/index_KOSPI.json') or {}).get('rows') or [])[-5:], '모아 둔 일별 자료'
    rows = [r for r in rows if r.get('종가')]
    if not rows:
        return None
    last = rows[-1]
    chg = (last['종가'] / rows[-2]['종가'] - 1) * 100 if len(rows) > 1 and rows[-2].get('종가') else None
    live = last['date'] == now.strftime('%Y%m%d') and now.strftime('%H%M') < '1530'
    return {'date': last['date'], 'close': float(last['종가']), 'change': chg, 'live': live, 'from': src}


@st.cache_data(ttl=60, show_spinner=False)
def api_lights():
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo
    from data_registry import quick_status
    return quick_status(), _dt.now(ZoneInfo('Asia/Seoul')).strftime('%H:%M')


def live_top_bar():
    """맨 위 제목 줄 + 가운데 코스피 · API 연결 불빛 + 모의투자 거래 내역. 1분마다 이 부분만 새로 그림.
    2026-10-03 최종 조합: 1일봉 50 · 15분봉 50 · 빈칸 엔진 · 코스닥 인버스(남는 돈) — 1시간봉은 모의 주문을 쉬어 칸에서 뺌."""
    lights, at = api_lights()
    st.markdown(top_bar(
        ledger_mini('1일봉 모의투자', repo_json_live('daily-live/state.json'), repo_json_live('daily-live/paper-orders.json')),
        ledger_mini('15분봉 모의투자', repo_json_live('m15-live/state.json'), repo_json_live('m15-live/paper-orders.json')),
        kospi_box(kospi_last()) + lights_box(lights, at),
        ledger_mini('빈칸 엔진 · 코스닥 인버스 모의투자', repo_json_live('idle-live/state.json'), repo_json_live('idle-live/paper-orders.json'))),
        unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner=False)
def repo_json(path):
    """GitHub Actions가 방금 올린 결과 파일을 5분마다 새로 읽습니다.

    앱 서버는 다시 배포되기 전까지 옛 파일을 들고 있어 '오늘의 결과'가 며칠 전에 멈춰 보였습니다
    (2026-10-01). 그래서 저장소의 최신 파일을 직접 받고, 못 받으면 앱 안의 파일을 씁니다.
    """
    import requests
    try:
        got = requests.get(RAW + path, timeout=8)
        if got.status_code == 200:
            return got.json()
    except (requests.RequestException, ValueError):
        pass
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def today_a_group():
    """가장 최근 마감의 일봉 조건 결과(1시간봉 규칙 · 조건 1~2개 미달). GitHub Actions가 study/a_group.json으로 남깁니다."""
    return repo_json(str(final_group.OUT))


def hourly_a():
    """1시간봉 규칙(1시간봉 규칙) 후보 · 연습 계좌 · 알림. GitHub Actions가 저녁(후보)과 장중 1시간마다 hourly-live/에 남깁니다."""
    return (repo_json("hourly-live/plan.json"), repo_json("hourly-live/state.json"),
            repo_json("hourly-live/alerts.json") or [])


def daily_live():
    """1일봉 규칙(일봉 규칙) 오늘 결과 · 연습 계좌 · 알림. GitHub Actions가 평일 15:20 ~ 15:35에 daily-live/에 남깁니다."""
    return (repo_json("daily-live/today.json"), repo_json("daily-live/state.json"),
            repo_json("daily-live/alerts.json") or [])


def m15_live():
    """15분봉 규칙 후보(1시간봉과 같은 저녁 후보 hourly-live/plan.json) · 연습 계좌 · 알림(m15-live/ · 장중 15분마다)."""
    return (repo_json("hourly-live/plan.json"), repo_json("m15-live/state.json"),
            repo_json("m15-live/alerts.json") or [])


def idle_live():
    """빈칸 엔진 · 코스닥 인버스 오늘 판단 · 들고 있는 것 · 주문 장부(idle-live/ · 평일 15:10)."""
    return (repo_json("idle-live/today.json"), repo_json_live("idle-live/state.json"),
            repo_json_live("idle-live/paper-orders.json"))


def latest_near():
    """장중에 지금 값으로 다시 센 후보 · 충족 미달 가운데 가장 늦게 판정한 것(15분봉 실행 m15-live · 1시간봉 실행 hourly-live)."""
    got = [x for x in (repo_json("m15-live/near-now.json"), repo_json("hourly-live/near-now.json")) if x]
    return max(got, key=lambda x: str(x.get("at") or "")) if got else {}


def daily_preview(today, now_near):
    """오늘 15:20 1일봉 판단이 아직 없고, 오늘 장중에 다시 센 것이 있으면 그것으로 1일봉 칸을 미리 보여 줌."""
    day = str((now_near or {}).get("date") or "")
    return bool(day) and str((today or {}).get("date") or "") < day


def near_lists():
    """두 칸 아래쪽 '충족 미달' 목록: (1시간봉, 1일봉, 1시간봉 기준 글, 1일봉 기준 글).

    두 칸이 같은 파일을 나눠 쓰면 늘 똑같이 보여서(2026-10-01 사용자 지적), 칸마다 제 규칙의 결과만 씁니다.
    - 1시간봉: 장중에는 1시간봉 실행이 매시 지금 값으로 다시 센 hourly-live/near-now.json(판정 시각 · 전날 수급까지),
      장 뒤에는 저녁 A그룹 작업이 남기는 hourly-live/plan.json의 near(오늘 종가 · 오늘 수급까지 → 다음 거래일 · 판정 시각).
      아직 없으면 빈 칸과 언제 나오는지만 적음.
    - 1일봉: 15:20 판단(daily-live/today.json)의 near(그때 값 · 어제 수급까지 · 목표가 내림 거르기 포함).
      그 전에는 일봉 A그룹(study/a_group.json, 같은 '어제 수급까지' 셈)의 목록.
    """
    plan, _, _ = hourly_a()
    today, _, _ = daily_live()
    group = today_a_group() or {}
    g_day = str(group.get("date") or "")
    # 장중에는 지금 값으로 다시 센 것(near-now.json)을 먼저 씀 — 15분봉 실행(15분마다) · 1시간봉 실행(매시) 가운데 늦게 판정한 것
    # (사용자 요청 2026-10-02 "매시간 판정 · 판정 시각" · "실시간 반영")
    now_near = latest_near()
    if now_near.get("near") is not None and str(now_near.get("date") or "") > str((plan or {}).get("base") or ""):
        hourly = now_near["near"]
        h_basis = f'{now_near.get("at")} 판정 · 그 시각 현재가 · 전날 수급까지 (장중 15분마다 다시 셈)'
    elif plan and plan.get("near") is not None:
        made = f' · {plan["made"]} 판정' if plan.get("made") else ""
        hourly, h_basis = plan["near"], f'{as_day(plan["base"])} 마감 · 그날 수급까지{made} → 다음 거래일 장중'
    else:
        hourly, h_basis = None, '첫 계산은 오늘 밤 일봉 수집이 끝난 뒤(새벽 3시쯤)에 나옵니다'
    if daily_preview(today, now_near):
        daily = now_near.get("near_daily") if now_near.get("near_daily") is not None else now_near["near"]
        d_basis = f'{now_near.get("at")} 판정 · 그 시각 현재가 · 전날 수급까지 (15:20 판단 전 미리 보기 · 15분마다 다시 셈)'
    elif today and today.get("near") is not None and str(today.get("date") or "") >= g_day:
        daily, d_basis = today["near"], f'{as_day(today["date"])} 15:20 판단 · 전날 수급까지'
    else:
        daily, d_basis = group.get("b_group") or [], (f'{as_day(g_day)} 마감 · 전날 수급까지' if g_day else "")
    return hourly, daily, h_basis, d_basis


def board_marks():
    """관심종목 판의 두 칸: 코드 → 한 줄 설명(1시간봉 규칙 · 1일봉 규칙)."""
    plan, hstate, _ = hourly_a()
    today, dstate, _ = daily_live()
    hourly, daily = {}, {}
    for c in (plan or {}).get("candidates") or []:
        hourly[c["code"]] = f'{c.get("name")}  ·  15분봉 매수 후보 · {4 if (c.get("추세문") or c.get("3일연속")) else 2}칸'
    for p in ((hstate or {}).get("positions") or {}).values():
        hourly[p["code"]] = f'{p.get("name")}  ·  1시간봉 규칙 보유 중 · {p.get("칸")}칸'
    for c in (today or {}).get("candidates") or []:
        daily[c["code"]] = f'{c.get("name")}  ·  1일봉 매수 후보 · {c.get("칸")}칸'
    now_near = latest_near()
    if daily_preview(today, now_near):       # 15:20 판단 전: 지금 값이면 1일봉 후보(15분마다 다시 셈)
        for c in now_near.get("picks_daily") or []:
            daily.setdefault(c["code"], f'{c.get("name")}  ·  1일봉 후보(지금 값이면 · {str(now_near.get("at"))[11:16]} 판정 · 15:20에 다시 판단)')
    for p in ((dstate or {}).get("positions") or {}).values():
        daily[p["code"]] = f'{p.get("name")}  ·  1일봉 규칙 보유 중 · {p.get("칸")}칸'
    return hourly, daily


def a_group_stamp():
    """관심종목 그룹 캐시 열쇠: 결과의 기준일이 바뀌면 새로 나눕니다."""
    return (today_a_group() or {}).get("date")


@st.cache_data(ttl=3600, show_spinner=False)
def graded_stocks(codes, research_key, rules=RULES, a_stamp=None):
    """관심종목의 등급. A는 최종 조건 목록으로, B·C는 EMA로 나눕니다."""
    return final_group.regroup(market.grade_all(codes, published()), today_a_group())


@st.cache_data(ttl=3600, show_spinner=False)
def market_top(top):
    """시가총액 상위 종목. 하루에 몇 번만 받아도 충분해 한 시간 동안 재사용합니다."""
    return market.top_by_market(top)


def seed_watchlist(store, state, research):
    """저장소가 비어 있으면 조사 자료가 있는 종목을 기본으로 담아 둡니다.

    Supabase를 연결하지 않으면 종목 목록은 실행 서버의 파일에 저장되는데, 앱이
    다시 시작되면 그 파일이 지워집니다(코드를 고쳐 배포하거나, 오래 쉬었다 깨어날
    때). 그때마다 목록을 손으로 다시 담게 두지 않고, 저장소에 모아 둔 조사 자료의
    종목으로 스스로 채웁니다. 저장소는 다시 시작해도 그대로이므로 목록도 돌아옵니다.

    한 번 채운 뒤에는 표시를 남겨, 직접 종목을 빼도 곧바로 되살아나지 않게 합니다.
    """
    if state.get('stocks') or state.get('journal') or state.get('seeded'):
        return False
    fresh = [{'code': code, 'name': report['name'], 'kind': '관심'}
             for code, report in sorted(research.items())]
    if not fresh:
        return False

    def apply(data):
        data['stocks'] = fresh
        data['seeded'] = True

    try:
        store.change(apply)
    except Exception:
        return False
    return True





def _pick(key):
    """어느 목록에서 눌렀든 마지막으로 고른 종목 하나만 기억합니다."""
    code = st.session_state.get(key)
    if code:
        st.session_state['px_pick'] = code


def _choose(code):
    """그룹판에서 종목을 골랐을 때."""
    st.session_state['px_pick'] = code


def group_board_ui(graded):
    """A·B·C 그룹 칸을 그리고, 종목마다 누를 수 있는 단추를 답니다.

    칩을 링크로 두면 눌렀을 때 화면을 새로 열게 되고, 그러면 Streamlit 세션이
    새로 시작돼 로그인이 풀립니다. 그래서 단추로 둡니다. 단추는 같은 화면 안에서
    처리되어 로그인도, 펼쳐 둔 칸도 그대로 남습니다.
    """
    buckets, pending = group_buckets(graded, *board_marks())
    h_near, d_near, h_basis, d_basis = near_lists()
    near = {"A": ("15분봉 매수 후보(충족 미달)", h_near, h_basis), "B": ("1일봉 매수 후보(충족 미달)", d_near, d_basis)}
    columns = st.columns(len(GROUP_TITLES))
    for column, key in zip(columns, GROUP_TITLES):
        klass = GROUP_TITLES[key][2]
        rows = buckets[key]
        with column, st.container(border=True, key=f'pxgrp-{klass}'):
            st.markdown(slot_head(key, len(rows)), unsafe_allow_html=True)
            if not rows:
                st.caption('해당 종목 없음')
            for row in rows[:SHOWN_PER_GROUP]:
                st.button(chip_label(row), key=f'pxpick-{key}-{row["code"]}',
                          on_click=_choose, args=(row['code'],), width='stretch')
            rest = rows[SHOWN_PER_GROUP:]
            if rest:
                with st.expander(f'더 보기 · {len(rest)}종목'):
                    for row in rest:
                        st.button(chip_label(row), key=f'pxpick-{key}-{row["code"]}',
                                  on_click=_choose, args=(row['code'],), width='stretch')
            if key in near:
                title, near_rows, basis = near[key]
                st.markdown('<div class="pxb">' + near_panel(title, near_rows, basis) + '</div>', unsafe_allow_html=True)
    # 관심종목 기준일 안내 줄 · '판정 보류' 칸은 매수 규칙과 무관해 뺌(사용자 요청 2026-10-01)


def fill_reports(store, stocks, limit=20):
    """확정 결산 자료가 없는 종목을 차례로 채웁니다.

    한 종목씩 저장하므로 도중에 멈춰도 거기까지는 남습니다. 한 번에 다 받으면
    DART 호출이 몰리고 화면이 오래 멈추므로 한 번에 limit개까지만 받습니다.
    """
    from datetime import datetime, timezone
    from providers import Official, DataError
    from automatic import brief

    provider = Official()
    targets = stocks[:limit]
    bar = st.progress(0.0, text='시작하는 중')
    done, failed = [], []
    for index, stock in enumerate(targets):
        bar.progress(index / len(targets), text=f'{stock["name"]} · {index + 1}/{len(targets)}')
        try:
            report = provider.automatic(stock['code'])
            saved = {**stock, 'name': report['name'], 'report': report,
                     'automatic_brief': brief(report), 'year': report['years'][-1]['year'],
                     'analyzed_at': datetime.now(timezone.utc).isoformat(), 'analysis_error': None}
            store.save_stock(saved)
            done.append(report['name'])
        except (DataError, KeyError, IndexError, TypeError, ValueError) as error:
            failed.append((stock['name'], str(error)[:70]))
        except Exception as error:
            failed.append((stock['name'], str(error)[:70]))
    bar.progress(1.0, text=f'{len(done)}종목 저장 · {len(failed)}종목 실패')
    return done, failed


def missing_reports(state):
    """자료를 받아야 하는 관심종목.

    아직 받지 않은 종목과, 예전 방식으로 받아 과거 시가총액 배수가 빠진 종목을
    함께 돌려줍니다. 배수가 없으면 적정주가 참고 범위가 계속 '산출 보류'로 남습니다.
    """
    picked = []
    for stock in state.get('stocks', []):
        if stock['code'].startswith('pending-'):
            continue
        report = stock.get('report')
        if not report or not report.get('anchors_from'):
            picked.append(stock)
    return picked


def decision_screen(state, research, graded, store=None, sample_mode=True):
    """오늘의 투자판단. 그룹판은 접힌 채로 시작하고, 종목을 누르면 여섯 칸이 열립니다."""
    stocks = [s for s in state.get('stocks', []) if not s['code'].startswith('pending-')]
    names = {s['code']: s['name'] for s in stocks}
    # 조사 전 종목은 판정 자료에 이름이 없어 코드로만 나오므로 목록의 이름을 입힙니다.
    graded = [{**g, 'name': names.get(g['code']) or g.get('name') or g['code']}
              for g in graded or []]
    # 첫 화면에서 클릭 없이 그룹과 그 안의 종목이 보여야 합니다.
    # 담은 종목이 없으면 그룹판이 통째로 비어 화면이 끊겨 보이므로, 그 자리에
    # 왜 비었고 무엇을 누르면 되는지 적습니다.
    if graded:
        board = None          # 그룹 칸은 아래에서 단추로 그립니다.
    elif stocks:
        board = ('<p class="pxb-sub" style="max-width:100%">담은 종목의 시세를 아직 받지 '
                 '못했습니다. 공공데이터포털 인증키와 종목코드를 확인하세요.</p>')
    else:
        board = ('<p class="pxb-sub" style="max-width:100%">담은 종목이 없어 판정할 것이 '
                 '없습니다. 아래 <b>＋ 조사된 종목 담기</b>로 자료가 준비된 종목을 한 번에 '
                 '담거나, <b>＋ 시가총액 상위 종목 담기</b>로 코스피·코스닥 상위 종목을 '
                 '담으면 여기에 그룹이 나옵니다.</p>')
    plan, mstate, malerts = m15_live()
    dtoday, dstate, dalerts = daily_live()
    itoday, istate, ibook = idle_live()
    live_top_bar()
    # 1시간봉 · 1일봉 매수 후보 두 칸을 제목 바로 아래에(사용자 요청 2026-10-01)
    if board is None:
        group_board_ui(graded)
    else:
        st.markdown(board, unsafe_allow_html=True)
    # 화살표를 눌러야 펼쳐짐(사용자 2026-10-03) · 1시간봉 칸은 15분봉으로(1시간봉은 모의 주문 보류) · 빈칸 엔진 칸 더함
    st.markdown(frame_open()
                + section('통합 매매 규칙', '1일봉 50% · 15분봉 50% · 남는 돈은 빈칸 엔진 · 코스닥 과열 인버스 · 한투 모의투자(사용자 2026-10-03 이름)')
                + fold('15분봉 매매 규칙', '조사 대상 507종목 전체에서 · 장중 15분마다 · 모의투자 몫 50%',
                       M15_RULES + sortie_panel(today_a_group(), plan, mstate, malerts, name='15분봉'))
                + fold('1일봉 매매 규칙', '조사 대상 507종목 전체에서 · 하루 한 번 15:20 · 모의투자 몫 50%',
                       CLOSE_RULES + close_panel(dtoday, dstate, dalerts))
                + fold('빈칸 엔진 · 코스닥 인버스 모의투자', '규칙들이 안 쓰는 돈 · 하루 한 번 15:10 · KODEX 200 · 달러 · 나스닥 · 금 · 국고채 · 코스닥 인버스',
                       IDLE_RULES + idle_panel(itoday, istate, ibook))
                + close_frame(), unsafe_allow_html=True)
    named = {g['code']: g['name'] for g in graded}
    code = st.session_state.get('px_pick')
    if code:
        grade = next((g for g in graded if g['code'] == code), None)
        report = research.get(code)
        # 확정 결산 분석은 종목을 담을 때 저장해 둔 공식 리포트에서 가져옵니다.
        official = next((s.get('report') for s in stocks if s['code'] == code), None)
        name = names.get(code) or (report or {}).get('name') or code
        price, price_note = price_now(grade, official)
        # 증권사 목표주가와 현재가는 키가 있을 때만 붙습니다. 없으면 종가로 갑니다.
        live, opinions = live_quote(code), broker_targets(code)
        note = '종목코드 ' + code
        if live and live.get('price'):
            note += (f' · 현재가 {live["price"]:,.0f}원 · {live.get("at", "")} '
                     + live_note(live.get('at')))
        elif price:
            note += f' · 주가 {price:,.0f}원 · {price_note}'
        st.markdown(frame(section(f'{name} · 투자판단', note)
                          + stock_cards(report, grade, official, opinions, live)),
                    unsafe_allow_html=True)
    # 종목을 고르기 전 '투자판단' 안내 칸은 뺌(사용자 요청 2026-10-01 · 매매 규칙과 무관).

    if stocks:
        with st.expander(f'관심종목 목록 · {len(stocks)}종목'):
            labels = {s['code']: s['name'] for s in stocks}
            st.pills('종목을 고르면 아래에 판단 카드 여섯 칸이 열립니다', list(labels),
                     format_func=lambda c: labels[c], key='px_watch',
                     on_change=_pick, args=('px_watch',))
    # 마지막으로 받은 결과는 채우기 패널 바깥에서 보여 줍니다. 전부 받고 나면
    # 채울 종목이 없어 패널 자체가 사라지고, 안에 있던 안내도 함께 사라집니다.
    outcome = st.session_state.pop('px_fill_done', None)
    if outcome:
        done, failed = outcome
        if done:
            st.success(f'{len(done)}종목 저장 · ' + ', '.join(done[:10])
                       + (f' 외 {len(done) - 10}종목' if len(done) > 10 else ''))
        for name, reason in failed:
            st.warning(f'{name} · {reason}')
        if not done and not failed:
            st.info('받을 종목이 없었습니다.')

    gaps = missing_reports(state)
    # '자료 받기'는 관심종목 자세히 보기(판단점수 · 실적)용 손 받기 단추 — 매매 규칙 · 모의투자와 무관해 화면에서 뺌(사용자 요청 2026-10-01).
    if SHOW_FILL and gaps and not sample_mode and store is not None:
        with st.expander(f'자료 받기 · {len(gaps)}종목'):
            st.caption('DART 확정 결산·공시와 공공데이터포털 시세를 종목마다 받아 저장합니다. '
                       '아직 받지 않은 종목과, 과거 시가총액 배수가 빠져 적정주가 참고 범위가 '
                       '보류된 종목을 함께 받습니다. 한 번에 20종목씩 받고, 받은 종목은 '
                       '그때그때 저장합니다.')
            st.write(', '.join(s['name'] for s in gaps[:20])
                     + (f' 외 {len(gaps) - 20}종목' if len(gaps) > 20 else ''))
            how_many = st.radio('한 번에 받을 개수', ['20종목씩', f'전부 {len(gaps)}종목'],
                                horizontal=True, key='px_fill_count')
            st.caption('전부 받기는 종목 수만큼 시간이 걸립니다. 도중에 창을 닫아도 '
                       '그때까지 받은 종목은 저장돼 있습니다.')
            # 결과는 화면을 다시 그린 뒤 위쪽에서 보여 줍니다. 저장 직후 st.rerun()을
            # 부르면 방금 띄운 안내가 함께 지워져, 몇 분을 기다린 사람이 무엇이
            # 저장됐는지 못 보고 끝납니다.
            if st.button('자료 받기', key='px_fill'):
                done, failed = fill_reports(store, gaps,
                                            limit=len(gaps) if how_many.startswith('전부') else 20)
                st.session_state['px_fill_done'] = (done, failed)
                st.rerun()


def render_research(store, state, sample_mode):
    theme()
    research = published()
    if not sample_mode and seed_watchlist(store, state, research):
        state = store.read()
        # 앱을 다시 켜면(Reboot) 실행 서버 파일이 비어 관심종목을 다시 담음. 안내 문구는 매매와 무관해 뺌(사용자 요청 2026-10-01).
    known = {**research, **{r['code']: r for r in state.get('chat_research', [])}}
    if not sample_mode and link_codes(store, state, known):
        state = store.read()
    codes = [s['code'] for s in state.get('stocks', []) if not s['code'].startswith('pending-')]
    decision_screen(state, research,
                    graded_stocks(codes, max(research, default=''), a_stamp=a_group_stamp()) if codes else [],
                    store=store, sample_mode=sample_mode)
    hero('내 투자의 현재를 한눈에', '관심 있는 기업을 담고, 판단에 필요한 변화만 확인하세요.', 'PLANX · STOCK RESEARCH')
    if sample_mode:
        st.info('임시 실습 모드입니다. 담은 종목은 이 접속에서만 남습니다. '
                '저장 공간(Supabase 또는 실행 서버 파일) 설정을 확인하세요.')
    else:
        with st.expander('＋ 종목 추가', expanded=not state.get('stocks')):
            with st.form('research_manual'):
                name = st.text_input('종목명', placeholder='예: 삼성전자')
                with st.expander('종목코드를 알고 있다면 · 선택'):
                    code = st.text_input('종목코드', max_chars=6)
                if st.form_submit_button('내 목록에 추가'):
                    import re
                    if not name.strip() or (code and not re.fullmatch(r'[0-9]{6}', code)):
                        st.error('종목명과 숫자 6자리 코드를 확인하세요. 코드는 생략할 수 있습니다.')
                    else:
                        known = next((s for s in state.get('stocks', []) if s['name'].strip().casefold() == name.strip().casefold()), {})
                        identity = known.get('code') or code or 'pending-' + hashlib.sha256(name.strip().casefold().encode()).hexdigest()[:16]
                        try:
                            store.save_stock({'code':identity, 'name':name.strip(), 'kind':known.get('kind','관심')})
                            st.rerun()
                        except Exception: st.error('목록 저장에 실패했습니다. 저장 공간 설정을 확인하세요.')
        with st.expander('＋ 시가총액 상위 종목 담기'):
            count = st.select_slider('시장별 상위 몇 종목', [10, 20, 30, 40, 50], value=10, key='rank_top')
            ranked = market_top(count)
            if ranked['error']:
                st.info(ranked['error'])
            else:
                owned = {s['code'] for s in state.get('stocks', [])}
                st.caption(f"{ranked['basis_date'][:4]}-{ranked['basis_date'][4:6]}-{ranked['basis_date'][6:]} 종가 시가총액 기준 · 공공데이터포털")
                columns = st.columns(len(market.MARKETS))
                for column, name in zip(columns, market.MARKETS):
                    with column:
                        rows = ranked['markets'][name]
                        st.markdown(f'**{name} 상위 {len(rows)}**')
                        st.dataframe(pd.DataFrame([
                            {'순위': r['rank'], '종목': r['name'], '코드': r['code'],
                             '시가총액(조원)': round(r['market_cap'] / 1_0000_0000_0000, 1)} for r in rows]),
                            hide_index=True, width='stretch')
                        fresh = [r for r in rows if r['code'] not in owned]
                        if st.button(f'{name} {len(fresh)}개 담기', disabled=not fresh,
                                     key=f'add_rank_{name}', width='stretch'):
                            try:
                                store.add_stocks([{'code': r['code'], 'name': r['name'], 'kind': '관심'} for r in fresh])
                                st.rerun()
                            except Exception: st.error('목록 저장에 실패했습니다. 저장 공간 설정을 확인하세요.')
        pool = {code: r['name'] for code, r in known.items() if code not in {s['code'] for s in state.get('stocks', [])}}
        if pool:
            with st.expander(f'＋ 조사된 종목 담기 · {len(pool)}개'):
                picks = st.multiselect('조사 자료가 있는 종목', list(pool), format_func=lambda c: f'{pool[c]} · {c}', key='add_researched')
                col_all, col_pick = st.columns(2)
                with col_all:
                    if st.button(f'전체 {len(pool)}개 담기', width='stretch'):
                        try:
                            store.add_stocks([{'code': c, 'name': n, 'kind': '관심'} for c, n in pool.items()])
                            st.rerun()
                        except Exception: st.error('목록 저장에 실패했습니다. 저장 공간 설정을 확인하세요.')
                with col_pick:
                    if st.button('선택한 종목 담기', disabled=not picks, width='stretch'):
                        try:
                            store.add_stocks([{'code': c, 'name': pool[c], 'kind': '관심'} for c in picks])
                            st.rerun()
                        except Exception: st.error('목록 저장에 실패했습니다. 저장 공간 설정을 확인하세요.')
        if state.get('stocks'):
            with st.expander('－ 종목 빼기'):
                labels = {s['code']: s['name'] + (' · 종목코드 미확인' if s['code'].startswith('pending-') else ' · ' + s['code']) for s in state['stocks']}
                drop = st.multiselect('내 목록에서 뺄 종목', list(labels), format_func=lambda c: labels[c], key='drop_stocks')
                st.caption('조사 결과는 그대로 두고 목록에서만 뺍니다.')
                if st.button('선택한 종목 빼기', disabled=not drop):
                    try:
                        store.remove_stocks(drop)
                        st.rerun()
                    except Exception: st.error('목록 저장에 실패했습니다. 저장 공간 설정을 확인하세요.')
    for r in state.get('chat_research', []):
        if r['code'] not in research or r['as_of'] >= research[r['code']]['as_of']: research[r['code']] = r
    stocks = {s['code']:s for s in state.get('stocks', [])}
    for p in st.session_state.get('account_snapshot', {}).get('positions', []):
        stocks[p['code']] = {**stocks.get(p['code'], {}), 'code':p['code'], 'name':p['name']}
    with st.expander('조사 요청 · 최신 내용으로 업데이트'):
        st.write('① 종목을 추가합니다. ② 아래 요청문을 복사해 지금 대화창에 보냅니다. ③ 조사 결과가 반영되면 이 화면을 새로고침합니다.')
        st.code(request_text(list(stocks.values())), language=None)
        st.caption('요청문에는 종목명만 포함됩니다. 이 채팅에 요청문을 보내야 조사가 시작됩니다.')
        if st.button('반영된 조사 결과 다시 읽기'): st.rerun()
        if not sample_mode:
            with st.expander('조사 파일 가져오기 · 고급'):
                upload = st.file_uploader('별도로 받은 조사 JSON 가져오기 · 선택', type=['json'])
                if upload and st.button('조사 파일 검증·저장'):
                    try:
                        reports = parse_bundle(upload.getvalue())
                        def save(data):
                            merged = {r['code']:r for r in data.get('chat_research', [])}
                            for r in reports:
                                if r['code'] not in merged or r['as_of'] >= merged[r['code']]['as_of']: merged[r['code']] = r
                            data['chat_research'] = list(merged.values())
                        store.change(save)
                        st.rerun()
                    except (ValueError, KeyError, TypeError): st.error('조사 파일의 형식·출처·기간을 확인하세요. 기존 결과는 유지했습니다.')
                    except Exception: st.error('저장에 실패했습니다. 기존 결과는 유지했습니다.')
    if not stocks:
        with st.container(border=True):
            st.subheader('첫 관심종목을 담아보세요')
            st.write('위의 종목 추가를 열고 기업 이름 하나만 입력하면 시작할 수 있습니다.')
        return
    rows, details = [], {}
    for key, stock in stocks.items():
        r = research.get(key)
        if not r and key.startswith('pending-'):
            matches = [v for v in research.values() if v['name'].strip().casefold() == stock['name'].strip().casefold()]
            if len(matches) == 1: r = matches[0]
        r = r or {}
        f, v, flow = r.get('financial') or {}, r.get('valuation') or {}, r.get('flow') or {}
        trend, frame = trends(r.get('prices'), r.get('as_of', date.today().isoformat()))
        row = {'종목':stock['name'], '코드':r.get('code', key if not key.startswith('pending-') else '확인 필요'),
               '누적 매출 성장':growth(f['revenue'], f['prior_revenue']) if f else '조사 필요',
               '누적 영업이익 성장':growth(f['operating_profit'], f['prior_operating_profit']) if f else '조사 필요',
               '외국인 / 기관':f"{flow['foreign']:+,.0f} / {flow['institution']:+,.0f} {flow['unit']}" if flow else '조사 필요',
               '적정주가 참고':f"{v['base']:,.0f}원" if v else '조사 필요',
               '일봉':trend['daily'], '주봉':trend['weekly'], '조사일':r.get('as_of','미조사')}
        rows.append(row);details[key]=(stock, r, trend, frame)
    overview(details, st.session_state.get('account_snapshot'))
    with st.expander('전체 지표 비교'):
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    st.markdown('### 기업 하나를 깊게 보기')
    selected = st.selectbox('자세히 볼 종목', list(details), format_func=lambda k:stocks[k]['name'], key='research_selected')
    stock, r, trend, frame = details[selected]
    code = r.get('code') or selected
    if not r:
        st.info('이 종목의 채팅 조사 결과가 아직 없습니다. 위 요청문을 대화창에 보내면 조사 결과를 채울 수 있습니다.')
        if stock.get('report'):
            st.write('기존 공식 결산 분석: ' + brief(stock['report'])['summary'])
        if not _is_code(code):
            return
        st.subheader(stock['name'])
    else:
        st.subheader(stock['name'])
        st.caption('조사일 ' + r['as_of'] + ' · 각 표의 자료 기간은 아래에 별도 표시합니다. 탭을 누르면 그 탭의 최신 자료를 받아 위에 보여 줍니다.')
        grade = next((g for g in (graded_stocks([selected], max(research, default='')) or [])
                      if g['code'] == selected), None)
        detail(r, grade)
        summary = r.get('summary')
        if summary:
            with st.container(border=True):
                st.markdown('**핵심 요약**')
                st.write(summary['text'])
    # on_change='rerun'이면 누른 탭만 .open이 참입니다. 그 탭의 최신 자료만 받습니다.
    tabs = st.tabs(['어떤 기업인가요?', '실적은 어떤가요?', '주가 흐름', '가격과 확인 사항'],
                   key='research_tab', on_change='rerun')
    fresh = _is_code(code)
    with tabs[0]:
        if fresh and tabs[0].open:
            latest_company(code)
        for label, key in [('주력사업과 기업 특징','business')]:
            st.subheader(label)
            entry = r.get(key)
            if entry:
                st.write(entry['text']); st.link_button('설명의 원문 근거', entry['source'], key='research_'+key)
            else: st.info('조사 필요')
    with tabs[1]:
        if fresh and tabs[1].open:
            latest_results(code)
        f = r.get('financial')
        if f:
            st.caption(f"{period_label(f['period'])} / 전년 {period_label(f['prior_period'])}"
                       f" · {f['basis']} · {f['currency']} {f['unit']}")
            st.dataframe([{'항목':'매출','이번 누적':f['revenue'],'전년 누적':f['prior_revenue'],'변화':growth(f['revenue'],f['prior_revenue'])},
                          {'항목':'영업이익','이번 누적':f['operating_profit'],'전년 누적':f['prior_operating_profit'],'변화':growth(f['operating_profit'],f['prior_operating_profit'])}], hide_index=True)
            st.link_button('실적 근거', f['source'])
        else: st.info('전년 같은 기간 누적 실적 조사 필요')
        peers = r.get('peers')
        st.subheader('경쟁사 영업이익 순위')
        if peers and peers['rows']:
            st.write(peers['selection_reason'])
            st.caption(f"비교 표본 내 순위 · {peers['period']} · {peers['basis']} · {peers['currency']} {peers['unit']}")
            peers_chart(peers)
            df = pd.DataFrame(peers['rows']);df['순위'] = df['operating_profit'].rank(method='min', ascending=False).astype(int)
            st.dataframe(df.sort_values('순위')[['순위','name','operating_profit','source']].rename(columns={'name':'기업','operating_profit':'영업이익','source':'출처'}), hide_index=True)
        else: st.info('같은 기간·회계기준의 경쟁사 실적 조사 필요')
    with tabs[2]:
        if fresh and tabs[2].open:
            latest_prices(code)
        flow = r.get('flow')
        if flow:
            st.caption(flow['start'] + ' ~ ' + flow['end'] + ' · 순매수 ' + flow['unit'])
            a,b=st.columns(2);a.metric('외국인 순매수', f"{flow['foreign']:+,.0f}");b.metric('기관 순매수', f"{flow['institution']:+,.0f}")
            st.link_button('수급 근거', flow['source'])
        else: st.info('외국인·기관 수급 조사 필요')
        a,b=st.columns(2);a.metric('일봉 추세',trend['daily']);b.metric('완료 주봉 추세',trend['weekly'])
        st.caption('수정종가 기준: 일봉 20·60일, 주봉 10·20주 평균과 장기 평균 기울기를 함께 확인합니다. 진행 중인 주는 제외합니다.')
        if frame is not None:
            st.caption('가격 자료 마지막 거래일 ' + str(frame['date'].iloc[-1]))
            st.line_chart(frame.set_index('date')['close'])
            st.link_button('가격 자료 근거', r['prices']['source'])
    with tabs[3]:
        if fresh and tabs[3].open:
            latest_price_check(code)
        v = r.get('valuation')
        if v:
            a,b,c=st.columns(3)
            for col,key,label in [(a,'low','낮은 참고가'),(b,'base','기본 참고가'),(c,'high','높은 참고가')]: col.metric(label,f"{v[key]:,.0f}원")
            st.write(v['method']);st.caption(f"비교 가격 {v['current_price']:,.0f}원 · {v['price_date']} · 기본 참고가 대비 차이 {(v['base']/v['current_price']-1)*100:+.1f}%")
            st.link_button('평가 근거', v['source'])
        else: st.info('평가 가정과 가격 근거 조사 필요')
        for gap in r.get('data_gaps', []): st.write('확인 필요 · ' + str(gap))
    if not sample_mode:
        with st.expander('투자일지 남기기'):
            with st.form('research_note'):
                note=st.text_area('투자일지 · 다음 확인할 조건')
                if st.form_submit_button('기록 저장') and note.strip():
                    try:
                        from datetime import datetime, timezone
                        store.log('journal', {'code':selected,'at':datetime.now(timezone.utc).isoformat(),'kind':'note','note':note.strip()})
                        st.success('일지를 저장했습니다.')
                    except Exception: st.error('저장 실패. 입력 내용을 보관하세요.')
