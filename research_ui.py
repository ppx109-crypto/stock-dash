import hashlib
import json
from datetime import date

import pandas as pd
import streamlit as st

from ui_v2 import hero, card
from automatic import brief
from bi_view import theme, overview, detail, peers_chart
from chat_research import published, parse_bundle, trends, growth, request_text
from dashboard_ui import (GROUP_TITLES, RULE_TEXT, close_frame, frame, group_board,
                          header, price_now, rank_rows, section, stock_cards)
import market


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
RULES = 'ema-5-20-40-60-abc'


@st.cache_data(ttl=3600, show_spinner=False)
def graded_stocks(codes, research_key, rules=RULES):
    """관심종목의 EMA 등급. 하루 한 번 갱신되는 자료라 한 시간 재사용합니다."""
    return market.grade_all(codes, published())


@st.cache_data(ttl=3600, show_spinner=False)
def market_top(top):
    """시가총액 상위 종목. 하루에 몇 번만 받아도 충분해 한 시간 동안 재사용합니다."""
    return market.top_by_market(top)


PENDING = '보류'


def _pick(key):
    """어느 목록에서 눌렀든 마지막으로 고른 종목 하나만 기억합니다."""
    code = st.session_state.get(key)
    if code:
        st.session_state['px_pick'] = code


def _buckets(graded):
    """그룹별 종목 묶음. 판정에 필요한 거래일이 모자란 종목은 따로 모읍니다."""
    groups = {key: [] for key in GROUP_TITLES}
    groups[PENDING] = []
    for row in graded:
        groups[row['group'] if row.get('group') in GROUP_TITLES else PENDING].append(row)
    groups = {key: rank_rows(rows) for key, rows in groups.items()}
    # A·B·C는 비어 있어도 남겨 둡니다. 눌렀을 때 "없음"을 보는 편이,
    # 버튼이 사라져 어느 그룹을 봤는지 모르게 되는 것보다 낫습니다.
    if not groups[PENDING]:
        del groups[PENDING]
    return groups


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
    """확정 결산 자료가 아직 없는 관심종목."""
    return [s for s in state.get('stocks', [])
            if not s.get('report') and not s['code'].startswith('pending-')]


def decision_screen(state, research, graded, store=None, sample_mode=True):
    """오늘의 투자판단. 그룹판은 접힌 채로 시작하고, 종목을 누르면 여섯 칸이 열립니다."""
    stocks = [s for s in state.get('stocks', []) if not s['code'].startswith('pending-')]
    names = {s['code']: s['name'] for s in stocks}
    # 조사 전 종목은 판정 자료에 이름이 없어 코드로만 나오므로 목록의 이름을 입힙니다.
    graded = [{**g, 'name': names.get(g['code']) or g.get('name') or g['code']}
              for g in graded or []]
    # 첫 화면에서 클릭 없이 그룹과 그 안의 종목이 보여야 합니다.
    st.markdown(header() + section('그룹 판정', RULE_TEXT) + group_board(graded)
                + close_frame(), unsafe_allow_html=True)
    named = {g['code']: g['name'] for g in graded}
    if graded:
        buckets = _buckets(graded)
        titles = {PENDING: '판정 보류'}
        titles.update({key: GROUP_TITLES[key][0] for key in GROUP_TITLES})
        # 비어 있는 그룹을 처음부터 보여 주면 "종목 없음"만 읽고 끝납니다.
        # 종목이 들어 있는 첫 그룹을 기본으로 펼칩니다.
        first = next((key for key, rows in buckets.items() if rows), next(iter(buckets)))
        st.pills('그룹을 고르면 그 그룹의 종목이 모두 나옵니다', list(buckets),
                 format_func=lambda k: f'{titles[k]} · {len(buckets[k])}종목',
                 key='px_group', default=first)
        picked = st.session_state.get('px_group') or first
        rows = buckets.get(picked) or []
        if rows:
            st.pills(f'{titles[picked]} · 영업이익이 좋은 순서 · 누르면 판단 카드가 열립니다',
                     [r['code'] for r in rows], format_func=lambda c: named.get(c, c),
                     key='px_group_pick', on_change=_pick, args=('px_group_pick',))
        else:
            st.caption(f'{titles[picked]}에 해당하는 종목이 없습니다.')
    if stocks:
        with st.expander(f'관심종목 목록 · {len(stocks)}종목'):
            labels = {s['code']: s['name'] for s in stocks}
            st.pills('종목을 고르면 아래에 판단 카드 여섯 칸이 열립니다', list(labels),
                     format_func=lambda c: labels[c], key='px_watch',
                     on_change=_pick, args=('px_watch',))
    gaps = missing_reports(state)
    if gaps and not sample_mode and store is not None:
        with st.expander(f'자료 없는 종목 채우기 · {len(gaps)}종목'):
            st.caption('DART 확정 결산·공시와 공공데이터포털 시세를 종목마다 받아 저장합니다. '
                       '한 번에 20종목씩 받고, 받은 종목은 그때그때 저장합니다.')
            st.write(', '.join(s['name'] for s in gaps[:20])
                     + (f' 외 {len(gaps) - 20}종목' if len(gaps) > 20 else ''))
            how_many = st.radio('한 번에 받을 개수', ['20종목씩', f'전부 {len(gaps)}종목'],
                                horizontal=True, key='px_fill_count')
            st.caption('전부 받기는 종목 수만큼 시간이 걸립니다. 도중에 창을 닫아도 '
                       '그때까지 받은 종목은 저장돼 있습니다.')
            if st.button('자료 받기', key='px_fill'):
                done, failed = fill_reports(store, gaps,
                                            limit=len(gaps) if how_many.startswith('전부') else 20)
                if done:
                    st.success(f'{len(done)}종목 저장 · ' + ', '.join(done[:10]))
                for name, reason in failed:
                    st.warning(f'{name} · {reason}')
                if done:
                    st.rerun()

    code = st.session_state.get('px_pick')
    if code:
        grade = next((g for g in graded if g['code'] == code), None)
        report = research.get(code)
        # 확정 결산 분석은 종목을 담을 때 저장해 둔 공식 리포트에서 가져옵니다.
        official = next((s.get('report') for s in stocks if s['code'] == code), None)
        name = names.get(code) or (report or {}).get('name') or code
        price, price_note = price_now(grade, official)
        note = '종목코드 ' + code
        if price:
            note += f' · 주가 {price:,.0f}원 · {price_note}'
        st.markdown(frame(section(f'{name} · 투자판단', note)
                          + stock_cards(report, grade, official)), unsafe_allow_html=True)
    elif stocks:
        st.markdown(frame(section('투자판단', '위 목록에서 종목을 고르면 판단점수·실적·흐름이 열립니다')),
                    unsafe_allow_html=True)


def render_research(store, state, sample_mode):
    theme()
    research = published()
    known = {**research, **{r['code']: r for r in state.get('chat_research', [])}}
    if not sample_mode and link_codes(store, state, known):
        state = store.read()
    codes = [s['code'] for s in state.get('stocks', []) if not s['code'].startswith('pending-')]
    decision_screen(state, research,
                    graded_stocks(codes, max(research, default='')) if codes else [],
                    store=store, sample_mode=sample_mode)
    hero('내 투자의 현재를 한눈에', '관심 있는 기업을 담고, 판단에 필요한 변화만 확인하세요.', 'PLANX · STOCK RESEARCH')
    if sample_mode:
        st.info('둘러보기 중입니다. 개인 목록을 저장하려면 먼저 대시보드 비밀번호를 설정하세요.')
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
        st.write('① 종목을 추가하거나 포트폴리오에서 계좌를 불러옵니다. ② 아래 요청문을 복사해 지금 대화창에 보냅니다. ③ 조사 결과가 반영되면 이 화면을 새로고침합니다.')
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
            st.caption('계좌가 있다면 왼쪽 계좌 연결에서 보유종목을 가져올 수도 있습니다.')
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
    if not r:
        st.info('이 종목의 채팅 조사 결과가 아직 없습니다. 위 요청문을 대화창에 보내면 조사 결과를 채울 수 있습니다.')
        if stock.get('report'):
            st.write('기존 공식 결산 분석: ' + brief(stock['report'])['summary'])
        return
    st.subheader(stock['name'])
    st.caption('조사일 ' + r['as_of'] + ' · 각 표의 자료 기간은 아래에 별도 표시합니다. 실시간 분석이 아닙니다.')
    grade = next((g for g in (graded_stocks([selected], max(research, default='')) or [])
                  if g['code'] == selected), None)
    detail(r, grade)
    summary = r.get('summary')
    if summary:
        with st.container(border=True):
            st.markdown('**핵심 요약**')
            st.write(summary['text'])
    tabs = st.tabs(['어떤 기업인가요?', '실적은 어떤가요?', '주가 흐름', '가격과 확인 사항'])
    with tabs[0]:
        for label, key in [('주력사업과 기업 특징','business')]:
            st.subheader(label)
            entry = r.get(key)
            if entry:
                st.write(entry['text']); st.link_button('설명의 원문 근거', entry['source'], key='research_'+key)
            else: st.info('조사 필요')
    with tabs[1]:
        f = r.get('financial')
        if f:
            st.caption(f"누적 {f['period']} / 전년 {f['prior_period']} · {f['basis']} · {f['currency']} {f['unit']}")
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
