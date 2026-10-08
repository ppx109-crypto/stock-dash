"""REPLAY-RAW-PRICE-CONTRACT-0001 · 수집기 인터페이스(요청 계획 · 캐시 경계만) — 이번 TASK에서는 호출하지 않음(네트워크 막음).
python3 -E -P collector_interface.py <로컬 대상(targets148 로컬 출력).json> <공개 계획 출력.json>
다음 실제 실행(별도 TASK)이 지킬 것:
- 자격 이름: KIS_APP_KEY · KIS_APP_SECRET(시세 조회만 · 주문/잔고/계좌 TR 금지) · DART_CRTFC_KEY. 값 · 길이 · 일부 글자는 읽지도 찍지도 않음.
- KIS: POST /oauth2/tokenP 1회 → GET /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice(tr_id FHKST03010100)
  FID_COND_MRKT_DIV_CODE=J · FID_INPUT_ISCD · FID_INPUT_DATE_1/2 · FID_PERIOD_DIV_CODE=D · FID_ORG_ADJ_PRC='1'(원) 과 '0'(수정) 각각. 한 번에 최대 100거래일.
- DART: corpCode.xml 1회 → list.json(corp_code · bgn_de · end_de · pblntf_ty=B) → 사건 종류별 주요사항 API(piicDecsn · fricDecsn · pifricDecsn · crDecsn · cmpMgDecsn · cmpDvDecsn · cmpDvmgDecsn).
- 응답은 로컬 캐시(파일 sha256 · 요청 파라미터 sha256 · 조회 시각 KST)만 남기고 커밋하지 않음. 공개는 schema 검증 결과 · 비식별 파생 칸만.
- 상한: KIS 500(인증 포함) · DART 250 · 요청마다 429/5xx 재시도 2 · 같은 요청 캐시."""
import json, math, socket, sys
from collections import defaultdict
from pathlib import Path
socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
LOC, OUT = sys.argv[1:3]
rows = json.load(open(LOC))
span = defaultdict(list)
for r in rows:
    span[r["code"]].append(r["date"])
WARM = 5                                                      # 기업행동 효력일 앞뒤 · 평가 앞날을 위해 앞쪽 5거래일 여유(실제 거래일 수는 실행 때 달력으로)
kis = 1
per_code = []
for c, ds in span.items():
    n_days = 127                                              # 보수적 상한: Train 전체 127거래일
    calls = math.ceil((n_days + WARM) / 100) * 2               # 원 · 수정 두 번
    kis += calls
    per_code.append(calls)
dart = 1 + len(span) * (1 + 6)                                 # corpCode 1 + 종목마다 list 1 + 상세 최대 6
plan = {"codes": len(span), "kis_calls_upper": kis, "kis_cap": 500, "dart_calls_upper": dart, "dart_cap": 250,
        "within_caps": kis <= 500 and dart <= 250, "retry_per_request": 2,
        "credential_names": ["KIS_APP_KEY", "KIS_APP_SECRET", "DART_CRTFC_KEY"],
        "forbidden_endpoints": ["주문(order-cash 등)", "잔고(inquire-balance · TTTC8434R)", "주문가능금액", "계좌 조회 전부"],
        "cache_policy": "응답 원문 · 실제 종목 · 날짜는 로컬 캐시에만 · 커밋 금지 · 파일 sha256 · 요청 sha256 · fetched_at_kst만 공개",
        "network_calls_this_task": 0}
Path(OUT).write_text(json.dumps(plan, ensure_ascii=False, indent=1))
print(json.dumps(plan, ensure_ascii=False))
