> **부록 — 하위 에이전트가 기준 커밋 00b98ab1을 읽기만 해서 쓴 추출(코드 실행 · 호출 없음).** 본문 판정은 RULES-LOCK.md · DATA-AVAILABILITY.md가 우선.
> 본 세션 재확인: collect_investor_history.py:149-150('어제까지만 물음') · final_group.py:41(investor-data) · 기준점 자료 마지막 날(price-data 20261007 · investor-data 20261006 279종목) · daily-prices.yml:94-111 순서.

# 한투 · 다트 API 연결표와 자료가 '언제 알 수 있는 값'인지 (점검 2026-10-08 한국 시각)

- 기준 코드: 커밋 00b98ab1(2026-10-08 05:43 한국 시각) 따로 꺼낸 작업 폴더. **읽기만 함**(코드 실행 · 증권사 · 다트 호출 없음 · 비밀값 안 봄).
- 표의 "확인" 칸: **코드에서 확인** = 이 저장소 코드에 그렇게 적혀 있음. **공식 문서 미확인** = 저장소 안에 한투 · 다트 공식 명세 발췌가 없어 공식 문서로는 못 맞춰 봄.
  저장소에 있는 근거는 공식 명세가 아니라 **찔러보기(probe) 결과를 적은 글**뿐임: docs/DATA-CATALOG.md(probe_catalog.py · probe_minute.py 결과), docs/DATA-INCIDENT-20261002.md(research/probe_m15_close.py 결과). 이런 것은 "찔러보기 기록 있음"으로 따로 적음.
  공식 문서 이름이 코드에 적힌 것은 한 곳뿐: broker_kis.py:185 "국내주식 종목투자의견(국내주식-188)".
- 시각은 모두 한국 시각. GitHub 예약(cron)은 UTC라 +9시간으로 바꿈. GitHub 예약은 10~20분 늦거나 빠질 수 있음(intraday_runner.py 머리말).

---

## 1. 한투(KIS) API 연결표 — 코드가 실제로 부르는 것

공통: 모두 `broker_kis.KIS.request()`(broker_kis.py:80) → `_once()`(:93)로 감. 시세 조회는 작업마다 `KIS_ENV: real`(실전 서버 주소 · 조회만), 주문은 paper_trade.py의 모의 서버만.
머리글: `authorization: Bearer …`, `appkey`, `appsecret`, `tr_id`, `custtype: P`, 이어받기는 `tr_cont`(응답 머리 `tr_cont` F/M이면 다음 쪽).
**시장 구분 코드**: 종목 시세는 모두 `FID_COND_MRKT_DIV_CODE=J`(거래소 KRX)만 씀. NX(넥스트레이드) · UN(통합)은 research/probe_m15_close.py:69~82 찔러보기에서만 씀. 지수 · 시장 수급은 `U`(업종).

### 1-1. 토큰

| 파일:함수:줄 | 방식 · 경로 | TR | 요청 | 쓰는 응답 | 확인 |
|---|---|---|---|---|---|
| broker_kis.py:KIS.authorize:164 · 175 | POST /oauth2/tokenP | — | grant_type=client_credentials, appkey, appsecret | access_token, expires_in(120초 일찍 끝난 것으로 봄) | 코드에서 확인 · 공식 문서 미확인. 1분 안 재발급 거절 EGW00133 → 61초 쉬고 보관 파일 다시 봄(:168~177) |

### 1-2. 시세 · 수급 · 기타 조회 (주문 아님)

| # | 파일:함수:줄 | 방식 · 경로(/uapi/domestic-stock/v1/…) | TR | 주요 요청값 | 쓰는 응답 칸 | 채우는 곳 · 쓰는 곳 | 역할 | 확인 |
|---|---|---|---|---|---|---|---|---|
| K1 | broker_kis.py:KIS.daily:306~311 (history:337 · 140일씩 거슬러) | GET quotations/inquire-daily-itemchartprice | FHKST03010100 | MRKT=J, ISCD, DATE_1~DATE_2, PERIOD=D, **FID_ORG_ADJ_PRC=0(수정주가)** | output2: stck_bsop_date, stck_clpr, (detail) stck_oprc · stck_hgpr · stck_lwpr · acml_vol · acml_tr_pbmn | price-data(collect_prices.py), volume-data(collect_volumes.py), kosdaq-data(collect_kosdaq.py), etf-data(collect_prices.py · PRICE_OUT), fix_recent_days.py(아침 바로잡기), reconcile --recheck | 신호 입력(추세 · 정배열 · 시장 폭 · 거래량비) · **라벨(연구 손익은 이 종가로 셈)** · **사후 정정**(07:05 최근 5줄) | 코드에서 확인 · 공식 문서 미확인. **J인데도 그날 밤 정리 전엔 '오늘' 줄에 넥스트레이드 값이 옴** — 찔러보기 기록 있음(DATA-INCIDENT-20261002.md) |
| K2 | broker_kis.py:KIS.quote:245~249 | GET quotations/inquire-price | FHKST01010100 | MRKT=J, ISCD | output: stck_prpr, prdy_vrss(+prdy_vrss_sign), prdy_ctrt, hts_avls(억원 시총), acml_vol, stck_oprc, hts_kor_isnm | 저장 안 함. daily_live(15:20 판단 · 15:32 장부 종가), idle_live(15:10 · 시장 폭), basket_live(15:10), hourly_a(near-now), m15_live.market_now(시가 대비), pick_universe(시총 hts_avls), live_check | 신호 입력(장중 '오늘 종가' 대용) · **라벨(1일봉 연습 장부의 체결 종가 = 15:32 현재가)** | 코드에서 확인 · 공식 문서 미확인. 15:20 · 15:32의 J 현재가가 거래소 값만인지 공식 확인 없음 |
| K3 | collect_kis_hourly.py:broker_kis_rows:107~110 (m15 · 1시간봉 · 장중 봇 모두 이 함수) · collect_kis_intraday.py:market_open_today:77 · research/probe_m15_close.py:21 | GET quotations/inquire-time-dailychartprice | FHKST03010230 | MRKT=J, ISCD, **FID_INPUT_HOUR_1=153000·133000·113000·093000(한 번 120분)**, DATE_1=그날, FID_PW_DATA_INCU_YN=N, FID_FAKE_TICK_INCU_YN='' | output2: stck_bsop_date, stck_cntg_hour(그 분이 끝난 시각), stck_oprc · stck_hgpr · stck_lwpr · stck_prpr, cntg_vol | m15-kis/{코드}/{해}.csv(collect_kis_m15.py), hourly-kis(collect_kis_hourly.py · 정기 실행 꺼짐), etf-m15. 장중: m15_live.today_bars:233, hourly_a.today_bars:353 | 신호 입력(15분 · 1시간 EMA · 장중 재료) · 라벨(15분봉 연구 손익) · **결측 처리(장 열린 날 판정: 삼성전자 그날 1분봉이 있나)** | 코드에서 확인 · 공식 문서 미확인. "약 1년(2025-09-17~)까지만 줌"은 찔러보기 기록 있음(DATA-CATALOG.md) |
| K4 | broker_kis.py:KIS.flows:397~401 | GET quotations/inquire-investor | FHKST01010900 | MRKT=J, ISCD | output: stck_bsop_date, prsn_ntby_qty, frgn_ntby_qty, orgn_ntby_qty, stck_clpr | flow-data(collect_flows.py · 최근 며칠만 줌 · 같은 날은 새 값으로 덮음) | 운영 규칙은 안 씀(연구 · 앱 참고) | 코드에서 확인 · 공식 문서 미확인 |
| K5 | broker_kis.py:KIS.investor_daily:447~452 | GET quotations/investor-trade-by-stock-daily | FHPTJ04160001 | MRKT=J, ISCD, DATE_1(그날까지 30거래일), FID_ORG_ADJ_PRC='', FID_ETC_CLS_CODE='' | output2: stck_bsop_date, prsn_ntby_qty, frgn_ntby_qty, orgn_ntby_qty, ivtr_ntby_qty, fund_ntby_qty, pe_fund_ntby_vol, stck_clpr (full이면 frgn_reg/nreg, scrt, bank, insu, mrbn, etc_orgt, etc_corp, etc 더함) | investor-data(collect_investor_history.py · 매일 저녁), investor-full(손으로만) | **신호 입력: 공통 수급 5일 · 3일 연속(1일봉 · 1시간봉 · 15분봉 후보)** · 종가 칸은 fix_recent_days가 사후 정정 | 코드에서 확인 · 공식 문서 미확인. 칸 이름은 "2026-10-02 찔러보기로 확인"(broker_kis.py:433) |
| K6 | broker_kis.py:KIS.opinions_between:204~210 (opinions:181) | GET quotations/invest-opinion | FHKST663300C0 | MRKT=J, FID_COND_SCR_DIV_CODE=16633, ISCD, DATE_1~DATE_2(한 번 100줄까지) | output: stck_bsop_date, hts_goal_prc, invt_opnn, rgbf_invt_opnn, mbcr_name | opinion-data(collect_opinions.py 매일 365일 창 · collect_opinion_history.py 손으로) | **신호 입력: 1일봉 '45일 새 목표가 내림이면 안 삼'** | 코드에서 확인 · 공식 문서 이름만 코드 주석에 있음(국내주식-188) · 명세 발췌 없음 |
| K7 | broker_kis.py:KIS.short_daily:661 | GET quotations/daily-short-sale | FHPST04830000 | MRKT=J, ISCD, DATE_1~DATE_2 | output2(없으면 output): stck_bsop_date, ssts_cntg_qty, ssts_vol_rlim, acml_vol, stck_clpr | short-data(collect_short_credit.py · 손으로만 · 마지막 줄 2026-09-28) | 연구용(운영 규칙 안 씀 · 일봉 6 · 7 · 32 · 33회차 실패) | 코드에서 확인 · 공식 문서 미확인 |
| K8 | broker_kis.py:KIS.credit_daily:677 | GET quotations/daily-credit-balance | FHPST04760000 | fid_cond_mrkt_div_code=J, fid_cond_scr_div_code=20476, fid_input_iscd, fid_input_date_1(결제일) | deal_date(매매일), whol_loan_rmnd_rate, whol_loan_rmnd_stcn, whol_loan_gvrt, whol_loan_new_stcn, whol_loan_rdmp_stcn | credit-data(손으로만 · 마지막 줄 2026-09-21) | 연구용 | 코드에서 확인 · 공식 문서 미확인 |
| K9 | broker_kis.py:KIS.program_daily:537 | GET quotations/program-trade-by-stock-daily | FHPPG04650201 | MRKT=J, ISCD, DATE_1 | output: stck_bsop_date, whol_smtn_ntby_qty, whol_smtn_ntby_tr_pbmn, whol_smtn_shnu_vol, whol_smtn_seln_vol, acml_vol, stck_clpr | program-data(collect_kis_extra.py program · 손으로만) | 연구용(일봉 55~57 실패) | 코드에서 확인 · 공식 문서 미확인 · 기간은 찔러보기 기록 있음 |
| K10 | broker_kis.py:KIS.loan_daily:548 | GET quotations/daily-loan-trans | HHPST074500C0 | MRKT_DIV_CLS_CODE=3, MKSC_SHRN_ISCD, START_DATE, END_DATE, CTS='' | output1: bsop_date, new_stcn, rdmp_stcn, rmnd_stcn, rmnd_amt, acml_vol, **stck_prpr(원주가 종가)** | loan-data(손으로만) · **caps.py:_raw_closes(연구용 CAPS_ADJ=1 시총 고침)** | 연구용 · 결측 처리(원주가 ÷ 수정주가 배수) | 코드에서 확인 · 공식 문서 미확인 |
| K11 | broker_kis.py:KIS.trade_side_daily:558 | GET quotations/inquire-daily-trade-volume | FHKST03010800 | MRKT=J, ISCD, PERIOD=D, DATE_1~DATE_2 | output2: stck_bsop_date, total_shnu_qty, total_seln_qty | side-data(손으로만) | 연구용(일봉 62 실패) | 코드에서 확인 · 공식 문서 미확인 |
| K12 | broker_kis.py:KIS.index_now:570~574 | GET quotations/inquire-index-price | FHPUP02100000 | MRKT=U, ISCD=0001/1001 | output: bstp_nmix_prpr, bstp_nmix_prdy_vrss, bstp_nmix_prdy_ctrt, prdy_vrss_sign | 저장 안 함(앱 화면) | 참고 | 코드에서 확인 · 공식 문서 미확인 |
| K13 | broker_kis.py:KIS.index_daily:599 | GET quotations/inquire-daily-indexchartprice | FHKUP03500100 | MRKT=U, ISCD=0001/1001, DATE_1~DATE_2, PERIOD=D | output2: stck_bsop_date, bstp_nmix_oprc/hgpr/lwpr/prpr, acml_vol, acml_tr_pbmn | market-data/index_*.json(kis-extra-history 평일 18:40) · **data_guard.prev_trading_day:19(어제 거래일 알기)** | **결측 처리(자료가 어제 거래일까지 들어왔나 · 바구니 t0)** · 연구 국면 | 코드에서 확인 · 공식 문서 미확인 |
| K14 | broker_kis.py:KIS.market_investor_daily:610 | GET quotations/inquire-investor-daily-by-market | FHPTJ04040000 | MRKT=U, ISCD=0001/1001, DATE_1=DATE_2=그날, ISCD_1=KSP/KSQ, ISCD_2 | output: stck_bsop_date, prsn/frgn/orgn/ivtr/fund/pe_fund/scrt/insu/bank_ntby_tr_pbmn, bstp_nmix_prpr | market-data/investor_KSP · KSQ | 연구용(일봉 42 · 52 · 53 실패) | 코드에서 확인 · 공식 문서 미확인 |
| K15 | broker_kis.py:KIS.market_program_daily:625 | GET quotations/comp-program-trade-daily | FHPPG04600001 | MRKT=J, FID_MRKT_CLS_CODE=K/Q, DATE_1~DATE_2 | output: stck_bsop_date, arbt/nabt/whol_smtn_ntby_tr_pbmn | market-data/program_K · Q | 연구용 | 코드에서 확인 · 공식 문서 미확인 |
| K16 | broker_kis.py:KIS.market_funds:635 | GET quotations/mktfunds | FHKST649100C0 | FID_INPUT_DATE_1 | output: bsop_date, cust_dpmn_amt, crdt_loan_rmnd, uncl_amt, secu_lend_amt, futs_tfam_amt, mmf_amt, bstp_nmix_prpr | market-data/funds.json | 연구용 | 코드에서 확인 · 공식 문서 미확인 |
| K17 | broker_kis.py:KIS.financial_ratio:644 | GET finance/financial-ratio | FHKST66430300 | FID_DIV_CLS_CODE=0(연)/1(분기), fid_cond_mrkt_div_code=J, fid_input_iscd | output: stac_yymm, grs, bsop_prfi_inrt, ntin_inrt, roe_val, eps, sps, bps, rsrv_rate, lblt_rate | ratio-data(손으로만 · **통째로 덮어씀** · 발표일 칸 없음) | 연구용(일봉 66 효과 없음) · dguard | 코드에서 확인 · 공식 문서 미확인 |
| K18 | collect_kis_intraday.py:main:123 | GET quotations/investor-trend-estimate | HHPTJ04160200 | MKSC_SHRN_ISCD | output2: bsop_hour_gb(1~5), frgn_fake_ntby_qty, orgn_fake_ntby_qty, sum_fake_ntby_qty | intraday-data/estimate/{날}.json(평일 16:15) | 쌓는 중(운영 안 씀) | 코드에서 확인 · 공식 문서 미확인 · "과거 안 줌"은 찔러보기 기록 있음 |
| K19 | collect_kis_intraday.py:program_day:87 | GET quotations/comp-program-trade-today | FHPPG04600101 | MRKT=J, FID_MRKT_CLS_CODE=K/Q, 나머지 빈칸, tr_cont 이어받기 | output: bsop_hour, arbt/nabt/whol_smtn_ntby_tr_pbmn, bstp_nmix_prpr | intraday-data/program/{날}.json(마지막 30줄 15:29~15:58만 옴) | 쌓는 중(운영 안 씀) | 코드에서 확인 · 공식 문서 미확인 · 30줄만 오는 것은 찔러보기 기록 있음 |
| K20 | broker_kis.py:KIS.balance:695~699 (paper_check.py:23 같은 것) | GET trading/inquire-balance | 실전 TTTC8434R / 모의 **VTTC8434R** | CANO, ACNT_PRDT_CD, AFHR_FLPR_YN=N, INQR_DVSN=02, UNPR_DVSN=01, PRCS_DVSN=00, CTX_AREA_FK100/NK100 | output1: pdno, prdt_name, hldg_qty, pchs_avg_pric, prpr, evlu_amt, evlu_pfls_amt · output2: dnca_tot_amt, **prvs_rcdl_excc_amt(D+2 예수금)**, tot_evlu_amt | 모의 장부 몫 셈(paper_trade · idle_live · basket_live) · 'fetched' 시각 남김 | 주문 전 결측 처리(살 돈 셈) · 계좌 조회 | 코드에서 확인 · 공식 문서 미확인 |

예비 · 찔러보기 전용(운영 경로 아님, 손으로 돌리는 작업): probe_catalog.py:104~165(estimate-perform HHKST668300C0 · invest-opbysec FHKST663400C0 · inquire-daily-overtimeprice FHPST02320000 · ksdinfo HHKDB669110C0/669100C0/669101C0/669102C0), probe_minute.py(분봉 · 장중 시간별 여러 TR), probe_investor_daily.py · probe_short_credit.py · probe_opinion_history.py · research/probe_m15_close.py(J/NX/UN 일봉 견줌) · research/probe_flows.py(수급에 넥스트레이드 섞였나 · **결과가 문서에 없음**).
앱 화면 전용(predash/kis.py:106~245): tokenP, inquire-balance, inquire-investor, **inquire-daily-ccld(TTTC0081R/VTTC0081R · 체결 조회, 조회만)**, inquire-investor-daily-by-market, inquire-daily-itemchartprice, inquire-daily-indexchartprice. quotes.py는 키움 REST(api.kiwoom.com · ka10001)로 한투가 아님.

### 1-3. 주문을 넣는 것 — 따로 표시(이번 점검에서 부르지 않음)

| 파일:함수:줄 | 방식 · 경로 | TR | 요청 | 응답 | 막는 장치 |
|---|---|---|---|---|---|
| paper_trade.py:PaperBroker.order:167~171 | **POST /uapi/domestic-stock/v1/trading/order-cash** | 매수 **VTTC0012U** · 매도 **VTTC0011U**(환경변수로 바꿀 수 있음 :41~42) | CANO, ACNT_PRDT_CD, PDNO, ORD_DVSN=01(시장가), ORD_QTY, ORD_UNPR=0 | output.ODNO(주문번호) | PAPER_BASE=openapivts(모의) 고정 :22 · 주문 직전 base · mode=demo 다시 확인 :154 |
| paper_trade.py:134~138 | GET trading/inquire-psbl-order(매수 가능 조회 · 주문 아님이나 주문 수량 정함) | VTTC8908R | CANO, ACNT_PRDT_CD, PDNO, ORD_UNPR='', ORD_DVSN=01, CMA_EVLU_AMT_ICLD_YN=N, OVRS_ICLD_YN=N | output.nrcvb_buy_qty / max_buy_qty | 모의 서버만 |

broker_kis.py 머리말은 "No order endpoints"이고 실제로 주문 경로가 없음(코드에서 확인). 실전 TR(TTTC…U 주문)은 저장소 어디에도 없음.

---

## 2. 다트(DART) API 연결표

공통: `providers.Official.dart()`(providers.py:181~190) 또는 `collect_dart_extra.Dart.ask()`(:67~89)로 `https://opendart.fss.or.kr/api/{엔드포인트}`에 GET, `crtfc_key`는 환경변수 DART_CRTFC_KEY만. status 013 = 자료 없음 · 020 = 한도 · 010/011/012/901 = 키 거절. 기업코드는 corpCode.xml(zip) → stock_code ↔ corp_code(providers.py:193~205).

| # | 파일:함수:줄 | 엔드포인트 | 주요 요청값 | 쓰는 응답 칸 | 채우는 곳 | 역할 | 확인 |
|---|---|---|---|---|---|---|---|
| D1 | collect_events.py:gather:91 (종목마다 · 토 12:30 전체) · recent:117 (시장 전체 · 평일 19:20 최근 5일) | list.json | corp_code(종목별일 때), bgn_de, end_de, page_no, page_count=100, sort=date, sort_mth=asc | **rcept_dt**, report_nm, stock_code (rcept_no는 저장 안 함) | event-data/{코드}.json: rows [{date=rcept_dt, kind, title(60자)}], fetched, recent | **신호 입력: 사건 바구니 C(자사주취득 · 무상증자)** · caps.py 무상증자 날(연구 고침) | 코드에서 확인 · 공식 문서 미확인 |
| D2 | collect_daily.py:market_list:80 · collect_public_dart.py:collect:73 · providers.py:483 · 508 | list.json | (시장 전체) bgn_de, end_de(89일 창), page_count=100, page_no / (종목) corp_code, 90일, page_count=20~30 | report_nm, rcept_dt, rcept_no, stock_code | public-data/{코드}.json의 disclosures(최근 90일 30건) · '정기보고서 새로 나옴' 판정 | 앱 화면 · 결측 처리(다시 받을 종목 고르기) | 코드에서 확인 · 공식 문서 미확인 |
| D3 | providers.py:Official.annual:281 · collect_public_dart.py:half:15 · collect_dart_extra.py:cashflow:218 | fnlttSinglAcntAll.json | corp_code, bsns_year, reprt_code=11011(사업)/11012(반기)/11013/11014, fs_div=CFS/OFS | sj_div, account_id, account_nm, thstrm_amount, thstrm_add_amount, frmtrm_amount, rcept_no, thstrm_nm | public-data(years · halves: receipt=rcept_no), cash-data | 연구 · 앱(일봉 7 · 36회차 실패) | 코드에서 확인 · 공식 문서 미확인 |
| D4 | collect_dart_extra.py:quarter:161 | fnlttSinglAcnt.json | corp_code, bsns_year, reprt_code(1분기 11013 · 반기 11012 · 3분기 11014 · 사업 11011) | fs_div, rcept_no(=접수번호 → 앞 8자리 발표일), thstrm_dt/nm, account_nm, thstrm_amount, frmtrm_amount | quarter-data/{코드}.json rows{"해-보고서": {...}} | 연구(일봉 65 효과 없음) · dguard 검사 | 코드에서 확인 · 공식 문서 미확인 |
| D5 | collect_dart_extra.py:events:112 | 주요사항보고서 23종(tsstkAqDecsn · tsstkDpDecsn · tsstkAqTrctrCnsDecsn · tsstkAqTrctrCcDecsn · piicDecsn · fricDecsn · pifricDecsn · cvbdIsDecsn · bdwtIsDecsn · exbdIsDecsn · crDecsn · otcprStkInvscrInh/TrfDecsn · bsnInh/TrfDecsn · tgastInh/TrfDecsn · cmpMgDecsn · cmpDvDecsn · dfOcr · bsnSp · ctrcvsBgrq · lwstLg) | corp_code, bgn_de=받은날(처음 20170101), end_de=오늘 | 줄 전체(corp_name · corp_code 뺌) · **rcept_no로 겹침 없앰 · 앞 8자리를 날로 씀** | dart-events/{코드}.json rows{갈래: [...]}, 받은날{갈래: 날} | 연구(hlab 희석20 · 자사주20, 일봉 54 효과 없음) | 코드에서 확인 · 공식 문서 미확인 · 기간(2017~)은 찔러보기 기록 있음 |
| D6 | collect_dart_extra.py:holders:128 | elestock.json · majorstock.json | corp_code | rcept_no, rcept_dt, repror, 지분 칸들 | holder-data(통째로 덮어씀 · 최근 약 2년뿐) | 앱 참고(과거 검증 못 함) | 코드에서 확인 · '2년뿐'은 찔러보기 기록 있음 |
| D7 | collect_shares.py:gather:66 | stockTotqySttus.json | corp_code, bsns_year, reprt_code(11011→11012→11013→11014 차례, **한 해에 처음 답한 하나만**) | se(보통주), istc_totqy, distb_stock_co(유통주식 우선), **rcept_no 앞 8자리 가장 이른 것** | share-data/{코드}.json 날[[접수일, 주식수]] | **신호 입력: 시총 순위(100 · 150 · 200위 안)** = 주식수 × 종가(caps.py) | 코드에서 확인 · 공식 문서 미확인 |
| D8 | providers.py:company.json(:410 · 440 · 478) · check_dart.py:13 · data_registry.py:113 · 155 | company.json | corp_code | corp_name, stock_name, induty_code, hm_url, est_dt, acc_mt | public-data company · 연결 확인 | 앱 · 연결 확인 | 코드에서 확인 |
| D9 | providers.py:business_excerpt:308 | document.xml | rcept_no | 원문 zip | public-data business_excerpt | 앱 화면 | 코드에서 확인 |
| D10 | providers.py:193 · final_group.py:82(_dart_names) | corpCode.xml | — | stock_code, corp_code, corp_name | 이름표(study/names.json) · 기업코드 | 결측 처리(종목 이름) | 코드에서 확인 |

**공시 갈래(kind) 나누기**: collect_events.py:27~64 `kind_of(title)` — 제목의 빈칸을 모두 지운 뒤, 정해 둔 말이 **들어 있는지** 위에서부터 차례로 봐서 처음 맞는 갈래 하나만 붙임(유상증자 → 무상증자 → 전환사채(CB · BW · EB 묶음) → 자사주취득('자기주식취득') → 자사주처분(처분 · 소각) → 최대주주변경 → 공급계약('공급계약' · '수주') → 잠정실적 → 실적공시 → 배당 → 감자 → 소송 → 관리종목 → 주식소각 → 기업설명회 → 대량보유 → 임원소유 → 최대주주지분변동 → 조회공시 → 시설투자 → 생산중단 · 재개 → 경영전망 → 주식매수선택권). 어디에도 안 맞으면 버림.
- 빈틈: **'[기재정정]' · '[첨부정정]' 같은 정정 공시도 제목에 같은 말이 있어 같은 갈래의 새 사건으로 잡힘**(정정 여부 칸 없음 · rcept_no 안 남김). 바구니는 같은 종목 · 같은 갈래 20거래일 안 다시 안 셈(basket_live.py:96~99)이라 일부만 걸러짐. '자기주식취득신탁계약체결'처럼 신탁도 '자기주식취득' 글자를 품으면 자사주취득으로 잡힘(갈래 순서 탓 · 코드에서 확인, 실제 제목 꼴은 공식 문서 미확인).
- dart-events(D5)는 갈래를 다트 API 종류로 나눔(제목 아님).

---

## 3. 자료가 언제 들어오고, 언제 '확정'되고, 무엇이 먼저 쓰나

### 3-1. 작업 시각표(한국 시각 · 평일 기준)

| 시각 | 작업(파일) | 하는 일 |
|---|---|---|
| 07:05 | Daily close check(daily-close-check.yml · cron 5 22 * * 0-4) | fix_recent_days.py: price · volume · kosdaq · investor(종가 칸) 최근 5줄을 확정 값으로 덮음 → 바뀌면 **08:30 전일 때만** A그룹 · 1시간봉 후보(plan) 다시 셈 → reconcile --recheck |
| 08:20 · 11:41 | Intraday runner(intraday.yml) | 15분봉 봇 09:03~15:48 (:03 · :18 · :33 · :48), 1시간봉 봇 09:03~14:03 · 15:33 |
| 09:03~15:48 | M15 live(m15-live.yml) · Hourly A group live(09:01 · 10~14:01 · 15:31) | 예비 예약(상주 실행기가 돌면 건너뜀) |
| 14:40(15:00 예비) | Daily rule live(daily-live.yml) | idle_live.py **15:10 판단**(빈칸 엔진 · 인버스 · 바구니 C) → daily_live.py **15:20 판단 · 15:28 주문 마감 · 15:32 장부 종가** |
| 16:15 | KIS intraday after close | intraday-data(투자자 추정 · 프로그램 분별) |
| 17:20 · 20:20 · 23:20 · 02:20 · 05:20(매일) | KIS 15-minute bars(kis-m15.yml) | m15-kis 이어 받기(**price-data에 그날이 있어야 그날을 받음** — collect_kis_hourly.py:95~97 · 119) |
| 17:20 | Hourly history | hourly-data(야후 1시간봉 · 16시 전이면 오늘 버림) |
| 17:50 · 17:55 | ETF daily prices · ETF 15-minute bars | etf-data · etf-m15 |
| 18:00 | Daily DART refresh(collect_daily.py · 최대 350분) | public-data(공시 목록 · 실적) |
| DART 끝난 뒤 | **Daily price history**(workflow_run) | collect_prices(price-data) → collect_opinions → collect_flows → **collect_investor_history(어제까지)**. 실제 10-07: 일봉 커밋 18:44~18:47, 의견 · 수급 커밋 19:01 |
| 그 뒤 | A group(final_group.py + hourly_a.py plan) · Daily volume history(volume-data) | 다음 거래일 후보 · 1시간봉 plan |
| 그 뒤 | Reconcile(A group · 15분봉 뒤) | 검산(확정된 날까지만 · fix-recent/checked.json) |
| 18:40 | KIS extra history(예약은 market만) | market-data |
| 19:20 | Disclosure events(최근 5일 시장 전체) | event-data |
| 19:30 | DART extra history(events · holders) · 토 10:30 quarter | dart-events · holder-data · quarter-data |
| 01:40(매일) | DART cash flow | cash-data |
| 2 · 5 · 8 · 11월 6일 04:20 | Share counts(cron 20 19 5 2,5,8,11 *) | share-data(주식수) |
| 손으로만 | investor-full · short-credit · opinion-history · kosdaq-data · caps · universe · kis-hourly · krx-daily-history · public-daily · public-dart · market-ranking | — (cap-data · krx-data · public-daily 폴더는 **비어 있음**) |

**넥스트레이드(NXT) 시간과 겹침**: 일봉 수집(18:44 무렵)은 넥스트레이드 저녁장(20:00까지) 한가운데라, 한투 일봉(J)의 '오늘' 줄이 넥스트레이드 값일 수 있음(DATA-INCIDENT-20261002.md: 10-02 356/424종목). 확정은 **그날 밤 한투 정리 뒤**(연휴면 다음 거래일 밤) → 저장소에는 **다음 날 07:05**에 확정 값이 들어감(fix-recent/checked.json: 2026-10-07 07:22에 "20261006까지 확정"). 그 사이(저녁 ~ 다음 날 07:05) 만든 A그룹 · 1시간봉 · 15분봉 후보는 **임시 종가**로 셈한 것이고, 07:05 고침이 08:30을 넘기면 후보를 다시 세지 않음(daily-close-check.yml:62~66).

### 3-2. 자료마다 정리

| 자료(폴더) | 언제 받나(received_at) | 언제 확정 값인가 | 고칠 때 옛 값 덮나 · 고친 시각 남나 | 시각 기록 칸 | 가장 먼저 쓰는 판단 |
|---|---|---|---|---|---|
| 일봉 종가(price-data) | 평일 저녁 DART 뒤(실제 18:4x, DART가 길면 자정 넘음) | **다음 날 07:05 바로잡기 뒤**(그날 밤 한투 정리 전엔 넥스트레이드 값 가능) | **덮음.** 이어받을 때 겹친 날이 0.1% 안이면 새 값으로 조용히 덮고(collect_prices.py:118~130), 넘으면 처음부터 통째로 다시 받음(수정주가). fix_recent_days도 덮음. **corrected_at 없음** · fix-recent/last.json은 마지막 고침 한 번만(다음 고침이 덮음) · git 커밋 시각이 유일한 이력 | `fetched`(날짜만 YYYY-MM-DD · 시각 없음) | 그날 저녁 A그룹 · 1시간봉 plan(임시 값) → 다음 날 09:03 15분봉 · 1시간봉 · 15:10 엔진 · 15:20 1일봉(전날 줄까지) |
| 거래량 · 거래대금 · 고가 · 저가(volume-data) | Daily price history 끝난 뒤 | 위와 같음(07:05 fix_volume) | 덮음(같음). 이어받기는 겹친 날 **거래량이 하나라도 다르면 통째로 다시**(collect_volumes.py:89~94) | `fetched`(날짜만) | 15:20 1일봉 거래량비(앞 20일 가운데값, < 오늘) · 1시간봉 수급 세기 |
| 코스닥(kosdaq-data) | 손으로만 | fix_recent_days 대상 | 마지막 날 뒤를 history로 다시 받아 **그 날들을 덮음 · 수정주가 바뀜 검사 없음**(collect_kosdaq.py:73~87 → 앞뒤 기준이 섞일 수 있음) | `fetched` | 연구만 |
| 투자자별 순매수(investor-data) | Daily price history 안, **'어제'까지만 물음**(collect_investor_history.py:149~150) → **D일 줄은 D+1 저녁(~19:00)에 처음 들어옴**(커밋 자료로도 확인: 10-08 05:43 커밋에서 price 마지막 20261007 · investor 마지막 20261006) | D일 밤 정리 뒤 값이라 보통 확정(연휴 낀 10-02는 예외 · 수급 칸 넥스트레이드 섞임 여부는 probe_flows 결과가 문서에 없음 = 미확인) | **이미 있는 날은 다시 안 씀**(:94 · 106 '없는 날만') → 첫 값 고정 · 정정 없음. 종가 칸만 fix_recent_days가 덮음 | 없음(파일에 시각 칸 없음) | 15:20 1일봉 공통 수급 5일 · 3일 연속, 저녁 A그룹 · 1시간봉 · 15분봉 후보 |
| 투자자 순매수 최근(flow-data) | Daily price history 안(19:0x) · 오늘 줄 포함 | 저녁 값(넥스트레이드 섞임 미확인) | 같은 날은 새 값으로 덮음(collect_flows.py:40~46) | `fetched`(날짜만) | 운영 안 씀 |
| 공매도(short-data) · 신용(credit-data) | 손으로만(어제 끝) · 마지막 09-28 · 09-21 | — | 있는 날 안 덮음 | 없음 | 운영 안 씀 |
| 목표가 · 의견(opinion-data) | Daily price history 안(19:0x) · 365일 창 | 날짜(stck_bsop_date)만 · **발표 시각 없음** | (날, 증권사) 같으면 새 줄이 옛 줄을 덮음 → 같은 증권사가 같은 날 두 번 내면 하나만 남음 | `fetched`(날짜 · 바뀔 때만 씀) | 15:20 1일봉 '45일 목표가 내림'(**그날 앞 날짜만**) |
| 공시 목록(event-data) | 평일 19:20(최근 5일 시장 전체) · 토 12:30 종목마다 처음부터 | **rcept_dt 날짜만 · 접수 시각 없음** → 같은 날 장중 반응이 공시 뒤인지 가릴 수 없음 | 겹치지 않게 더함(평일) · 토요일은 통째로 다시 씀 | `fetched`(토 전체 날), `recent`(평일 끝날) | 사건 바구니 C: **t0(어제) 공시 → t0+1 15:10** |
| 주요사항보고서(dart-events) | 평일 19:30 | rcept_no 앞 8자리 날짜만 | rcept_no로 겹침 없앰 · 같은 rcept_no면 새 줄로 덮음 | `받은날`(갈래마다 날짜) | 운영 안 씀(연구 hlab) |
| 분기 실적(quarter-data) | 토 10:30 | 접수번호 = 발표일(날짜만) | **한 번 채운 칸은 다시 안 물음** → 정정 공시 안 들어옴. 처음 과거를 받을 때 다트가 정정본을 주면 그 접수번호(늦은 날)와 고친 숫자가 들어옴(공식 문서 미확인) | 없음 | 운영 안 씀(dguard는 접수일 < 그날만 씀 :206) |
| 연간 · 반기 실적(public-data) | 평일 18:00 | 접수번호(receipt) | 정기보고서가 새로 나오면 그 종목을 처음부터 다시 받아 **덮음** | `fetched`(날짜) | 운영 안 씀 |
| 재무비율(ratio-data) | 손으로만 | **발표일 칸 없음** | 통째로 덮음(지난 분기 값이 바뀌어도 모름) | `fetched`(받은 '어제' 날짜) | 운영 안 씀(연구는 분기 끝 + 60 · 90일로 늦춤) |
| 주식수(share-data) | 2 · 5 · 8 · 11월 6일 04:20 | 접수일(rcept_no 앞 8자리) | 같으면 안 씀 · 다르면 통째로 | `fetched`(날짜) | **15:10 · 15:20 시총 순위**, 저녁 A그룹 |
| 시장 폭 | 따로 저장 안 함(그때그때 셈) | price-data(시총 100위 안 50일선 > 200일선 몫) | — | — | 저녁 A그룹 · 15:10 엔진(현재가) · 15:20 1일봉(현재가) |
| ETF 일봉(etf-data) | 평일 17:50 | 넥스트레이드 거래 없어 그날 값 = 확정(DATA-INCIDENT 문서) · fix_recent_days 대상 아님 | 이어받기(덮음 같은 방식) | `fetched` | 15:10 빈칸 엔진 · 인버스(**어제까지** + 오늘 15:10 현재가) |
| 1분봉 → 15분봉(m15-kis) | 17:20~05:20 다섯 번(그날 price-data가 들어온 뒤라 실제는 20:20 무렵) | 한투 1분봉 15:30 봉 = 거래소 마감 단일가(DATA-INCIDENT 표) | **한 번 받은 날은 다시 안 물음**(have_days) · 고치려면 손으로 지움(10-02 실제로 지우고 다시 받음) · 빈 날은 empty.txt | CSV에 받은 시각 없음 | 다음 날 09:03부터 15분봉 · 1시간봉 봇(EMA) |
| 오늘 1분봉(저장 안 함) | 장중 봇이 그때 물음(:03 · :18 …) | 닫힌 봉만 씀(closed_bars) | — | — | 15분봉 · 1시간봉 판단 |
| 야후 1시간봉(hourly-data) | 17:20 | 16시 전이면 오늘 봉 버림 · 마감 동시호가 빠짐(0.4~0.5% 차이 · DATA-CATALOG) · 가장 최근 날은 나중에 합쳐져 그날을 통째로 바꿔 넣음 | 덮음 | 없음 | 1시간봉 EMA(한투 봉 없는 종목) |
| 장중 투자자 추정 · 프로그램(intraday-data) | 16:15 | 그날 것만 줌(과거 없음) | 날마다 새 파일 | 파일 이름 = 날 | 운영 안 씀 |

### 3-3. 1일봉 · 1시간봉 · 15분봉 판단이 기대는 수급 날짜 — **연구와 운영이 하루 어긋남(새로 찾음)**

- 1일봉 연구(final_group.compute 기본) 뜻: T일 판단 = **T−1까지 5거래일** 수급(final_group.py:13 · 192 · 230~232 `date < day`).
- 그런데 운영 T일 15:20에 investor-data에 있는 마지막 줄은 **T−2**(T−1 줄은 T일 저녁 19시에야 들어옴). flow_before는 '모자라면 그 앞 날'을 그냥 씀(FLOW_STALE 10일 안이면 통과) → **운영은 T−6 ~ T−2 다섯 날**, 연구는 T−5 ~ T−1 다섯 날. 3일 연속(daily_live.py:195~198)도 같음.
- 1시간봉 · 15분봉 후보(hourly_a.make_plan:296 · 310 `flow_day="next"`, `_flow_features(code, day)` `<= day`)는 "오늘(D) 수급까지"를 뜻하나, D 저녁 plan 때 investor-data는 **D−1까지**뿐 → 연구(hlab.py:262~265 · D 포함)보다 하루 늦음. 07:05 다시 세기 때도 investor-data는 안 늘어남.
- 미래 참조 쪽으로는 **안전한 쪽**(더 늦은 자료)이지만, 연구 성적이 운영에 그대로 나오지 않을 까닭임. 코드에서 확인 + 저장소 자료(마지막 줄 날짜)로 확인.

### 3-4. Universe(t) · 시총 순위의 빈틈

- 대상 종목 = universe.json(pick_universe.py · **고른 때의 현재 시총**, hts_avls) + flow_universe · hourly-data/universe.json. **상장폐지 종목 없음**(한투가 상폐 종목 일봉을 안 줌 · probe_delisted 기록). krx-data · public-daily(상폐 포함 자료) 수집기는 있으나 폴더가 **비어 있음**(손으로만 · 아직 안 돎). caps.py 머리말도 이 치우침을 적어 둠.
- 그날 시총 = **DART 주식수(그날까지 접수된 것) × 그날 종가**(caps.py:136~165 tag). 순위는 **모아 둔 약 507종목 안에서만** 셈(시장 전체 순위 아님).
- 주식수 빈틈: (1) 한 해에 보고서 **하나만**(처음 답한 것) → 1년에 점 하나 꼴(삼성전자 11점) · 유상증자 · 소각 · 분할 뒤 몇 달 늦게 반영. (2) 수집이 석 달에 한 번. (3) **price-data는 수정주가인데 주식수는 그때 값**이라 분할 앞 시총이 작게 나옴(CAPS_ADJ=1 고침은 연구용 · 운영은 기본 0, caps.py:28). (4) `known_by`는 접수일이 **그날과 같아도** 씀(caps.py:140 `when > day`에서만 멈춤) — 장 끝난 뒤 접수된 보고서의 주식수를 그날 순위에 쓸 수 있음(영향은 작음 · CLAUDE.md '다음 거래일부터' 원칙과 어긋남).
- 운영 15:10 · 15:20: 어제 종가로 시총 150위까지 고른 뒤 현재가로 다시 줄 세움(daily_live.py:336~343, idle_live.py:224~245).

### 3-5. 다트 공시 시각

- list.json은 접수 **날짜(rcept_dt)만** 주고 시각이 없음(DATA-CATALOG.md · DATA-AUDIT-15M.md에도 적힘). 그래서 **같은 날 반응이 공시 뒤인지 확인할 수 없음** → 코드는 '접수 다음 거래일부터' 씀.
- 사건 바구니의 'T0 반응'(t0−1 → t0 종가, basket_live.py:47~62)은 **공시가 장중 · 장 뒤 어느 때였는지 모른 채** 그날 하루 수익을 '반응'으로 봄. 사는 날이 t0+1이라 미래 참조는 아니지만, '공시에 대한 반응'이라는 해석은 확인 불가.
- 수집이 t0 19:20이라 그 뒤(밤)에 접수된 t0 공시는 t0+1 15:10에 없음 → 다음 날 들어와도 t0가 이미 지나 운영은 그 사건을 놓침. 토요일 전체 다시 받기로 연구 자료에는 들어감 → **연구엔 있고 운영엔 없는 사건**이 생길 수 있음(코드에서 확인 · 다트 접수 마감 시각은 공식 문서 미확인).
- 주말 · 휴일 접수는 다음 거래일 t0 사건으로 묶음(basket_live.py:65~67).

### 3-6. 코드에 적힌 '늦춰 쓰기' 목록(파일:줄)

| 자료 | 어디서 | 어떻게 |
|---|---|---|
| 수급 5일 합 | final_group.py:230~241 | `date < day`(그날 앞 5거래일) · 10일 넘게 낡으면 None |
| 수급 3일 연속 | daily_live.py:195~198 | `date < day` |
| 수급 (1시간봉 plan) | final_group.py:178~192(`flow_day="next"`) · hourly_a.py:274~280 | 다음 날의 '전날까지' = 오늘 포함(실제 자료는 하루 더 늦음 · 3-3) |
| 거래량비 | daily_live.py:201~213 | 앞 20거래일 `< day` 가운데값 ÷ 15:20 거래량 |
| 목표가 내림 | daily_live.py:215~233 · study.py:56~84 | bisect_left → 그날 앞 날짜만 · 3개월 안 의견만 |
| 투자자 수집 | collect_investor_history.py:149~150 · collect_short_credit.py:146 · collect_kis_extra.py:179 | 물을 때부터 '어제'까지 |
| 1분봉 수집 | collect_kis_hourly.py:116~119 | 오늘은 16시 뒤에만 |
| 야후 1시간봉 | collect_hourly.py:7 | 16시 전이면 오늘 봉 버림 |
| 장중 자료 | collect_kis_intraday.py:106 | 15:40 뒤에만 |
| ETF 지난 종가 | idle_live.py:218~221 · 58~66(inv_take) | `< day` · 오늘은 15:10 현재가만 |
| 15분봉 지난 봉 | m15_live.py:221~230 · 302~305 | `< day` · 정배열 깨짐은 전날 종가로 |
| 공시(바구니) | basket_live.py:65~67 · 169~175 | t0 = 어제 거래일(data_guard.prev_trading_day) 까지 |
| 공시(1시간봉 연구) | hlab.py:296~299 · attach | 접수일 ≤ 그날 재료를 다음 날 봉에 붙임 |
| 분기 실적 검사 | dguard.py:204~206 · 382~395 | 접수일 < 그날 · 재무비율은 분기 끝 + 60/90일 |
| 시총 주식수 | caps.py:136~143 | **접수일 ≤ 그날(같은 날 포함 · 늦춤 없음)** |

---

## 4. 찾은 빈틈 · 위험(중요한 차례)

1. **수급이 연구보다 하루 늦게 쓰임**(3-3) — 1일봉 · 1시간봉 · 15분봉 모두. 연구의 '전날까지 5일'과 운영의 실제 다섯 날이 다름.
2. **임시 종가(넥스트레이드)로 저녁 후보를 셈** — 07:05 고침이 08:30을 넘기면 그날 후보는 임시 값 그대로. investor-data 수급 칸의 넥스트레이드 섞임 여부는 확인 결과가 없음(probe_flows 결과 미기록).
3. **고친 기록이 남지 않음** — 모든 자료에 받은 시각은 `fetched` **날짜**뿐(시각 없음) · 확정 시각 · 고친 시각(corrected_at) 칸 없음. 이력은 git 커밋 시각뿐, fix-recent/last.json은 마지막 한 번만.
4. **volume-data '오늘 이미 받음' 판정이 날짜만 봄**(collect_volumes.py:99~104 · main 114) — price-data는 10-02에 '오늘 종가까지 있을 때만 건너뜀'으로 고쳤으나(collect_prices.py:142~156) 거래량은 그대로 → 전날 작업이 자정을 넘기면 그날 거래량을 건너뛸 수 있음(코드에서 확인 · 실제 일어났는지는 미확인).
5. **kosdaq-data 이어받기에 수정주가 바뀜 검사 없음**(collect_kosdaq.py:73~87) — 분할 뒤 앞뒤 기준이 섞일 수 있음(연구만 씀).
6. **주식수가 1년에 한 점 · 같은 날 접수 사용 · 수정주가와 기준 다름**(3-4).
7. **정정 공시가 새 사건으로 잡힘 · event-data에 rcept_no 없음**(2절).
8. 1일봉 장부 종가 = 15:32 현재가(J). 이것이 거래소 종가와 같은지는 공식 문서 미확인(저녁 검산 reconcile이 사후로 견줌).
9. m15_live.market_now는 봉이 닫히고 몇 분 뒤(실행 때) 현재가로 셈 — 연구의 '같은 시각 15분봉 종가 평균'과 몇 분 어긋남(운영 안의 차이 · 미래 참조는 아님 · 확인 필요).

## 다음 방향
- investor-data를 '그날 저녁에 그날 줄까지' 받도록 할지(또는 연구를 '이틀 전까지'로 맞춰 다시 잴지) 정하고, research/probe_flows.py 결과를 문서에 남겨 수급 칸의 넥스트레이드 섞임을 확정하기.
- 모든 자료 파일에 받은 시각 · 확정 여부 · 고친 시각(예: `received_at`, `final`, `corrected_at`)을 남기고, volume-data '오늘 받음' 판정을 price-data처럼 고치기.
