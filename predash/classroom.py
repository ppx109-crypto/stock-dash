"""Classroom credentials are held only in the current Streamlit session."""
import streamlit as st
from predash.kis import KIS, BrokerError


CLASSROOM_KEYS = {'snapshot','reports','report_errors','home_price','home_price_reason','market_lamps','health_upper','health_lower','decision_pick'}
CLASSROOM_PREFIXES = ('classroom_','class_','_kis_client','demo_','paper_','watch_','decision_','habit_','holding_evidence_',
                      'holding_relative_','industry_note_','relative_index_')


def is_classroom_key(key):
    """교실 화면이 세션에 넣는 이름인지(연결 해제 때 이것만 지움)."""
    key = str(key)
    return key in CLASSROOM_KEYS or key.startswith(CLASSROOM_PREFIXES)


def account_settings(mode=None):
    settings = st.session_state.get('classroom_credentials', {})
    selected = mode or settings.get('mode', 'demo')
    if selected != settings.get('mode'):
        return dict(mode=selected, key='', secret='', cano='', product='')
    return dict(mode=selected, **{k: settings.get(k, '') for k in ('key','secret','cano','product')})


def connection_form():
    if st.session_state.pop('classroom_clear_inputs', False):
        for key in ('class_key','class_secret','class_cano','class_product'):
            st.session_state.pop(key, None)
    st.subheader('내 증권사 계좌 연결')
    st.caption('각자 Fork한 앱에서 본인 키를 입력하세요. 현재 접속 세션에서만 사용합니다.')
    if st.session_state.get('classroom_credentials'):
        st.success('계좌 연결됨 · ' + ('모의투자' if account_settings()['mode']=='demo' else '실전 조회'))
        if st.button('계좌 연결 해제'):
            # PlanX 안에서는 PlanX 세션(로그인 · 메뉴 등)은 두고 교실 키 · 잔고 · 실습 기록만 지웁니다.
            for key in [k for k in st.session_state if is_classroom_key(k)]:
                del st.session_state[key]
            st.rerun()
        return
    with st.form('classroom_connection'):
        mode = st.radio('투자 환경', ['모의투자','실전 조회'], horizontal=True)
        key = st.text_input('App Key', type='password', key='class_key')
        secret = st.text_input('App Secret', type='password', key='class_secret')
        cano = st.text_input('계좌번호 앞 8자리', type='password', max_chars=8, key='class_cano')
        product = st.text_input('계좌번호 뒤 2자리', max_chars=2, key='class_product')
        submitted = st.form_submit_button('연결 확인', type='primary', use_container_width=True)
    if submitted:
        settings = dict(mode='demo' if mode=='모의투자' else 'real',key=key.strip(),secret=secret.strip(),cano=cano.strip(),product=product.strip())
        try:
            client = KIS(settings=settings)
            with st.spinner('잔고 조회 권한을 확인합니다…'):
                client.balance()
            st.session_state.classroom_credentials = settings
            st.session_state['_kis_client_demo' if settings['mode']=='demo' else '_kis_client'] = client
            st.session_state.classroom_clear_inputs = True
            st.rerun()
        except BrokerError as error:
            st.error(str(error))
    st.info('연결 해제와 로그아웃은 키·잔고·접속 중 실습 기록을 지웁니다. 필요한 기록은 먼저 백업하세요.')
