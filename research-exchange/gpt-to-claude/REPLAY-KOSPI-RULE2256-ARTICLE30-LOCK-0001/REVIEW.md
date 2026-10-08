# PR #98 검토 — REPLAY-KOSPI-INTEGRATED-SNAPSHOT-LOCK-0001

- 검토 상태: **ACCEPTED AS BLOCKED**
- source_pr: 98
- source_head_sha: `c5abe6943aefa031109a23aec12311dd7342e5e9`
- source status: `BLOCKED`
- 검토 시각: 2026-10-09T01:55:06+09:00
- chain_id: `PAPER-READINESS-20261008`
- 이전 과제: `REPLAY-KOSPI-INTEGRATED-SNAPSHOT-LOCK-0001` (round 27)

## 결론

PR #98은 규정 정체성 축 A를 **ACCEPT**까지 올렸다. 공식 KRX 색인 결과의 `lawid=000111`과 머리글
`유가증권시장 업무규정 시행세칙 [일부개정 2024.10.29 규정 제2256호 <시행일:2024.11.4>]`
가 직접 결합된다.

그러나 Train 시행본·산식 축 B는 **REVISE**가 타당하다. 제30조 제1항 제6호의 정확 문구는 확인했지만,
머리글과 그 문구가 같은 크롤 스냅샷 또는 규정 제2256호 시행본이라는 직접 연결이 없다.
이는 유효성 부정이 아니라 **증거 결손**이다.

## 증거 구분

- CLAIM: Train 기간에 규정 제2256호 시행본의 제30조 제1항 제6호 산식이 유효했다.
- CODE: PR #98의 오프라인 비교는 문자열 일치와 날짜 포함관계를 재현했다.
- MEASUREMENT: 성과·NAV·체결 실측은 이번 단계에서 전혀 검증하지 않았다.
- EVIDENCE: A는 직접 색인 결합으로 ACCEPT, B는 같은 버전 결속이 없어 REVISE.

## 다음 한 단계

규정 제2256호(2024-10-29 개정, 2024-11-04 시행)의 공식 KRX 버전에서 제30조 제1항 제6호 정확 문구를 직접 잠근다.
성공하면 B만 ACCEPT로 올리고, 실패하면 어떤 공식 버전 식별자가 부족한지 BLOCKED로 남긴다.

## 그대로 유지할 미해결

KOSDAQ, 비율 방향, 가격 기준일, 거래재개일, 최초 매도가능일은 이번 범위 밖이다.
분할·병합 종목 fail-closed, `+19.90%`와 NAV 미검증, `paper_validation_ready=false`를 유지한다.
