# F20 원자료 출처 영수증(FLOW-GATE-0059 round 2)

- 파일: market-data/investor_KSP.json · sha256 7798a6023eff8a3b6e7ed57f278d384caed471682d7fe37cf6aaf548bcc280ad
- 줄 2393 · 20170102 ~ 20261008 · 칸: 날짜 · 투자자별 순매수 대금(외국인 · 기관 · …) · 지수
- 원출처: 한국투자증권 Open API 조회 전용 '시장별 투자자매매동향(일별)' FHPTJ04040000(코스피 0001/KSP) · broker_kis.market_investor_daily · 수집기 collect_kis_extra.py market
- 수집 커밋(git log · UTC):
  - ce605b2a6 2026-10-09 09:54:20 +0000 Collect KIS extra history (market)
  - d22d8085e 2026-10-08 10:02:24 +0000 Collect KIS extra history (market)
  - a8d14c189 2026-10-07 13:43:39 +0000 Collect KIS extra history (market)
  - b2ca522df 2026-09-29 15:04:54 +0000 Collect KIS extra history (market)
  - ddd918a94 2026-09-29 13:14:33 +0000 Collect KIS extra history (market)
- 정정/재수집 정책(코드 collect_kis_extra.fill_market): 이미 받은 날짜 줄은 다시 받지 않고 새 날짜만 붙임(첫 수신 값 고정).
- 매일 이어 받기: .github/workflows/kis-extra-history.yml cron '40 9 * * 1-5' = 평일 18:40 KST(2026-10-07부터).
