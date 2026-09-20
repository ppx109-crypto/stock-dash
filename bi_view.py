"""Portfolio BI views built only from stored reports and account snapshots."""
from collections import defaultdict
import html

import altair as alt
import pandas as pd
import streamlit as st

GOLD = '#b1883c'
TEAL = '#37867b'
INK = '#493e2f'


def theme():
    st.markdown('''<style>
    .stApp{background:#f8f6f1;color:#352e25}
    [data-testid="stSidebar"]{background:#eee7da!important}
    [data-testid="stSidebar"] *{color:#493e2f!important}
    .block-container{max-width:1400px;padding-top:2rem}
    [data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#e7e0d3!important;border-radius:16px!important;background:#fffdf9}
    [data-testid="stMetric"]{background:#fffdf9;border:1px solid #e7e0d3;border-radius:14px;padding:18px 22px}
    [data-testid="stMetricValue"]{font-family:Georgia,serif;color:#715625}
    .stButton>button[kind="primary"]{background:#9a742f;border-color:#9a742f;color:white}
    .px-eyebrow{font-size:13px;letter-spacing:2px;color:#98763a;margin:0 0 5px}
    .px-business{padding:20px 22px;border-left:3px solid #b1883c;background:#f4efe4;border-radius:0 12px 12px 0;font-size:16px;line-height:1.8}
    h1,h2,h3{color:#493e2f!important;letter-spacing:-.03em}
    </style>''', unsafe_allow_html=True)


def draw(chart):
    st.altair_chart(chart.configure(background='#fffdf9').configure_view(stroke=None)
                    .configure_axis(labelColor=INK,titleColor=INK,gridColor='#eee8dd',labelFontSize=13,titleFontSize=13)
                    .configure_legend(labelColor=INK,titleColor=INK,labelFontSize=13), width='stretch')


def overview(details, snapshot):
    reports = [r for _, r, _, _ in details.values() if r]
    positions = (snapshot or {}).get('positions', [])
    a,b,c = st.columns(3)
    if positions:
        value = sum(float(p['value']) for p in positions)
        pnl = sum(float(p['pnl']) for p in positions)
        a.metric('국내주식 평가금액', f'{value:,.0f}원')
        b.metric('평가손익', f'{pnl:+,.0f}원', f'{pnl/(value-pnl)*100:+.1f}%' if value-pnl>0 else None)
        c.metric('보유 / 관심종목', f'{len(positions)} / {len(details)}')
        st.caption('계좌 조회 시점 기준 · 예수금 제외 · ' + str(snapshot.get('fetched','')))
    else:
        a.metric('내 관심종목', f'{len(details)}개')
        b.metric('조사 자료 보유', f'{len(reports)}개')
        c.metric('추가 조사 필요', f'{len(details)-len(reports)}개')
    left,right=st.columns([1,1.5],gap='large')
    with left, st.container(border=True):
        st.subheader('어디에 투자하고 있나요?')
        if positions:
            df=pd.DataFrame([{'종목':p['name'],'평가액':p['value']} for p in positions if p['value']>0])
            if not df.empty:
                df['비중']=df['평가액']/df['평가액'].sum()
                draw(alt.Chart(df).mark_arc(innerRadius=65,outerRadius=105).encode(
                    theta='평가액:Q',color=alt.Color('종목:N',scale=alt.Scale(range=[GOLD,TEAL,'#b96b50','#71809a','#c4ae82']),legend=alt.Legend(orient='bottom')),
                    tooltip=['종목',alt.Tooltip('평가액:Q',format=',.0f'),alt.Tooltip('비중:Q',format='.1%')]).properties(height=245))
                st.caption('조회된 국내주식 평가액 기준 · 현금 제외')
        else:
            st.markdown('**계좌를 연결하면 보유 비중을 보여드립니다.**')
            st.write('관심종목만 등록해도 오른쪽에서 기업별 실적을 비교할 수 있습니다.')
            st.caption('왼쪽 메뉴 → 계좌 연결')
            st.markdown(' · '.join(html.escape(s['name']) for s,_,_,_ in details.values()))
    with right, st.container(border=True):
        st.subheader('이익이 더 빠르게 늘어나는 기업은?')
        groups=defaultdict(list)
        for r in reports:
            f=r.get('financial')
            if f:
                key=(f['period'],f['prior_period'],f['basis'],f['currency'],f['unit'])
                groups[key].append((r,f))
        if not groups:
            st.info('종목 조사 결과가 들어오면 실적 그래프가 표시됩니다.')
        else:
            keys=list(groups)
            key=st.selectbox('비교 기간·기준',keys,format_func=lambda k:f'{k[0]} 누적 / 전년 {k[1]} · {k[2]}',key='bi_period') if len(keys)>1 else keys[0]
            bars=[]; special=[]
            for r,f in groups[key]:
                prior=f['prior_operating_profit'];now=f['operating_profit']
                if prior>0:bars.append({'종목':r['name'],'증가율':(now/prior-1)*100})
                else:special.append(r['name']+' · 전년 이익이 0 이하: 상세 실적 확인')
            if bars:
                df=pd.DataFrame(bars)
                draw(alt.Chart(df).mark_bar(cornerRadiusEnd=4,color=GOLD).encode(
                    x=alt.X('증가율:Q',title='누적 영업이익 증가율 (%)'),y=alt.Y('종목:N',sort='-x',title=None),
                    tooltip=['종목',alt.Tooltip('증가율:Q',format='+.1f')]).properties(height=245))
            st.caption(f'{key[0]} / {key[1]} · {key[2]} · 같은 기간과 회계기준의 기업만 비교')
            for text in special:st.caption(text)


def trend_panel(grade):
    """추세·실적 두 축과 이동평균을 한 칸에 보여줍니다."""
    if not grade:
        st.info('이동평균 판정에는 일별 종가가 필요합니다. 공공데이터포털 인증키를 확인하세요.')
        return
    axis=grade.get('trend') or {}
    money=grade.get('earnings') or {}
    if not grade.get('group'):
        st.warning(grade.get('note') or axis.get('reason') or '판정에 필요한 거래일이 모자랍니다.')
        return
    left,right=st.columns([1,1.25])
    with left:
        st.metric(f"{grade['group']}그룹",grade.get('reason',''))
        st.caption(f"추세 {axis.get('grade')} · 실적 {money.get('grade')}"
                   f" · 조건 {grade.get('met')}/{grade.get('total')}")
    with right:
        lines=axis.get('ema') or {}
        if lines:
            frame=pd.DataFrame([{'선':k,'값':v} for k,v in lines.items()]+[{'선':'종가','값':axis.get('price')}])
            draw(alt.Chart(frame).mark_bar(size=22,cornerRadiusTopLeft=3,cornerRadiusTopRight=3).encode(
                y=alt.Y('선:N',title=None,sort=['종가','EMA5','EMA20','EMA40','EMA60']),
                x=alt.X('값:Q',title='원',scale=alt.Scale(zero=False)),
                color=alt.Color('선:N',scale=alt.Scale(range=['#9db9a4',GOLD,'#c8b184','#d8c8a7','#e6dcc6']),legend=None),
                tooltip=['선',alt.Tooltip('값:Q',format=',.0f')]).properties(height=170))
        st.caption(f"이평선 간격 {axis.get('spread')}% · 60일선 {'상승' if axis.get('slope_up') else '하락'}"
                   f" · 거래일 {axis.get('days')}개")
    missing=grade.get('missing') or []
    if missing:
        st.caption('미달 조건 · '+' / '.join(missing))
    if axis.get('price_breaks'):
        st.caption(f"가격이 하루 사이 크게 끊긴 지점 {axis['price_breaks']}곳 · "
                   '공공데이터포털 종가는 수정주가가 아니라 분할·병합 구간에서 이동평균이 왜곡될 수 있습니다.')
    if money.get('margin') is not None:
        st.caption(f"영업이익률 {money.get('prior_margin')}% → {money.get('margin')}% · {money.get('period')}")


def detail(r,grade=None):
    a,b,c=st.columns([1.15,1,1],gap='large')
    with a,st.container(border=True):
        st.subheader('주력사업과 기업 특징')
        business=r.get('business') or r.get('summary')
        if business:st.markdown('<div class="px-business">'+html.escape(business['text'])+'</div>',unsafe_allow_html=True)
        else:st.info('사업 내용 조사 필요')
    with b,st.container(border=True):
        st.subheader('영업이익 변화')
        f=r.get('financial')
        if f:
            df=pd.DataFrame([{'기간':f['prior_period'],'영업이익':f['prior_operating_profit']},{'기간':f['period'],'영업이익':f['operating_profit']}])
            draw(alt.Chart(df).mark_bar(size=45,cornerRadiusTopLeft=4,cornerRadiusTopRight=4).encode(
                x=alt.X('기간:O',title=None,axis=alt.Axis(labelAngle=0)),y=alt.Y('영업이익:Q',title=f['unit']),
                color=alt.Color('기간:N',scale=alt.Scale(range=['#d8c8a7',GOLD]),legend=None),tooltip=['기간',alt.Tooltip('영업이익:Q',format=',.1f')]).properties(height=210))
            margin=f['operating_profit']/f['revenue']*100 if f['revenue']>0 else None
            st.caption(f"{f['basis']} · {f['currency']} {f['unit']}"+(f' · 영업이익률 {margin:.1f}%' if margin is not None else ''))
        else:st.info('같은 기간의 전년·당년 실적이 필요합니다.')
    with c,st.container(border=True):
        st.subheader('가격과 가치의 거리')
        v=r.get('valuation')
        if v:
            df=pd.DataFrame([{'구분':label,'가격':v[k]} for k,label in [('low','낮은 참고가'),('base','기본 참고가'),('high','높은 참고가'),('current_price','비교 주가')]])
            draw(alt.Chart(df).mark_point(filled=True,size=130).encode(x=alt.X('가격:Q',title='원',scale=alt.Scale(zero=False)),y=alt.Y('구분:N',title=None),color=alt.value(TEAL),tooltip=['구분','가격']).properties(height=160))
            st.metric('기본 참고가',f"{v['base']:,.0f}원")
            st.caption(f"가격 기준일 {v['price_date']} · 평가 가정은 상세 탭에서 확인")
        else:
            st.write('**평가 근거를 기다리고 있습니다.**')
            st.caption('현재 주가와 실적 전망, 적용 배수의 근거가 모이면 참고가 범위를 표시합니다.')
    with st.container(border=True):
        st.subheader('이동평균과 그룹 판정')
        trend_panel(grade)


def peers_chart(peers):
    df=pd.DataFrame(peers['rows']).rename(columns={'name':'기업','operating_profit':'영업이익'})
    draw(alt.Chart(df).mark_bar(color=TEAL,cornerRadiusEnd=4).encode(x=alt.X('영업이익:Q',title=peers['unit']),y=alt.Y('기업:N',sort='-x',title=None),tooltip=['기업',alt.Tooltip('영업이익:Q',format=',.1f')]).properties(height=max(150,min(400,len(df)*45))))
