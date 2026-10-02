"""Classroom credentials are held only in the current Streamlit session."""
import os

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
        # 실전 키로 연결돼 있어도 앱 Secrets에 모의 키(KIS_DEMO_*)가 따로 있으면 모의투자 화면은 그것을 씀
        other = st.session_state.get('classroom_demo_credentials', {})
        if selected == 'demo' and other.get('mode') == 'demo':
            return dict(mode='demo', **{k: other.get(k, '') for k in ('key','secret','cano','product')})
        return dict(mode=selected, key='', secret='', cano='', product='')
    return dict(mode=selected, **{k: settings.get(k, '') for k in ('key','secret','cano','product')})


def saved_secret_sets():
    """앱 Secrets(환경 변수)에 있는 한투 키 묶음: KIS_*(KIS_ENV가 real이면 실전 조회, 아니면 모의) · KIS_DEMO_*(모의).
    네 값이 다 있는 묶음만 돌려줍니다. 값은 화면에 쓰지 않습니다."""
    found = []
    for prefix, mode in (('KIS_', 'real' if os.getenv('KIS_ENV', 'demo').strip() == 'real' else 'demo'), ('KIS_DEMO_', 'demo')):
        settings = dict(mode=mode, key=os.getenv(prefix+'APP_KEY', '').strip(), secret=os.getenv(prefix+'APP_SECRET', '').strip(),
                        cano=os.getenv(prefix+'CANO', '').strip(), product=os.getenv(prefix+'ACNT_PRDT_CD', '').strip())
        if all(settings[k] for k in ('key', 'secret', 'cano', 'product')) and all(f['mode'] != mode for f in found):
            found.append(settings)
    return found


def auto_connect():
    """앱 Secrets에 한투 키가 있으면 교실을 열 때 바로 연결해 둡니다(사용자 요청 2026-10-02 · 버튼 없이 새로고침이 켜지게).
    잔고 조회는 새로고침 때 함. 사용자가 '계좌 연결 해제'를 누른 접속에서는 다시 붙이지 않음."""
    if st.session_state.get('classroom_credentials') or st.session_state.get('predash_auto_off'):
        return False
    sets = saved_secret_sets()
    if not sets:
        return False
    st.session_state.classroom_credentials = sets[0]
    st.session_state.classroom_from_secrets = True
    demo = [x for x in sets[1:] if x['mode'] == 'demo']
    if sets[0]['mode'] == 'real' and demo:
        st.session_state.classroom_demo_credentials = demo[0]
    return True


def connect(settings):
    """잔고 조회로 확인한 뒤 이 접속 세션에만 연결 정보를 둡니다."""
    try:
        client = KIS(settings=settings)
        with st.spinner('잔고 조회 권한을 확인합니다…'):
            client.balance()
        st.session_state.classroom_credentials = settings
        st.session_state.pop('predash_auto_off', None)
        st.session_state['_kis_client_demo' if settings['mode']=='demo' else '_kis_client'] = client
        st.session_state.classroom_clear_inputs = True
        st.rerun()
    except BrokerError as error:
        st.error(str(error))


def connection_form():
    if st.session_state.pop('classroom_clear_inputs', False):
        for key in ('class_key','class_secret','class_cano','class_product'):
            st.session_state.pop(key, None)
    st.subheader('내 증권사 계좌 연결')
    st.caption('각자 Fork한 앱에서 본인 키를 입력하세요. 현재 접속 세션에서만 사용합니다.')
    if st.session_state.get('classroom_credentials'):
        st.success('계좌 연결됨 · ' + ('모의투자' if account_settings()['mode']=='demo' else '실전 조회')
                   + (' · 앱 Secrets 키로 자동 연결' if st.session_state.get('classroom_from_secrets') else ''))
        if st.button('계좌 연결 해제'):
            # PlanX 안에서는 PlanX 세션(로그인 · 메뉴 등)은 두고 교실 키 · 잔고 · 실습 기록만 지웁니다.
            for key in [k for k in st.session_state if is_classroom_key(k)]:
                del st.session_state[key]
            st.session_state.predash_auto_off = True
            st.rerun()
        return
    secret_sets = saved_secret_sets()
    if secret_sets:
        st.caption('앱 Secrets에 저장된 한국투자증권 키로 바로 연결합니다. 키와 계좌번호 원문은 화면에 표시하지 않습니다.')
        cols = st.columns(len(secret_sets))
        for col, settings in zip(cols, secret_sets):
            label = 'Secrets 키로 연결 · ' + ('실전 조회' if settings['mode']=='real' else '모의투자')
            if col.button(label, type='primary', use_container_width=True, key='classroom_secret_'+settings['mode']):
                connect(settings)
        st.caption('또는 아래에 직접 입력하세요.')
    with st.form('classroom_connection'):
        mode = st.radio('투자 환경', ['모의투자','실전 조회'], horizontal=True)
        key = st.text_input('App Key', type='password', key='class_key')
        secret = st.text_input('App Secret', type='password', key='class_secret')
        cano = st.text_input('계좌번호 앞 8자리', type='password', max_chars=8, key='class_cano')
        product = st.text_input('계좌번호 뒤 2자리', max_chars=2, key='class_product')
        submitted = st.form_submit_button('연결 확인', type='primary', use_container_width=True)
    if submitted:
        connect(dict(mode='demo' if mode=='모의투자' else 'real',key=key.strip(),secret=secret.strip(),cano=cano.strip(),product=product.strip()))
    st.info('연결 해제와 로그아웃은 키·잔고·접속 중 실습 기록을 지웁니다. 필요한 기록은 먼저 백업하세요.')
