"""두 실행기 결과를 test-result.json 하나로 합침. python merge_results.py tr-contract.json tr-asis.json test-result.json"""
import json
import sys
a, b = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
fails = [c["name"] for s in (a, b) for c in s["cases"] if not c["pass"]]
out = {"code_baseline": "00b98ab1655c84806357f44f2de6f1509ef1447f", "network": "blocked(socket 막음) · 키 환경변수 지움 · 임시 폴더에서 실행",
       "suites": {"contract(합성 계약)": a, "as-is(운영 순수 함수 · 합성 입력)": b},
       "summary": {"total": a["summary"]["total"] + b["summary"]["total"], "pass": a["summary"]["pass"] + b["summary"]["pass"],
                   "fail": a["summary"]["fail"] + b["summary"]["fail"], "fail_names": fails,
                   "fail_meaning": "실패는 모두 as-is 시험의 '규칙 글 vs 코드 출력' 차이(경계 부동소수점 9 · 의도 미확인 1) — 시험 장치 오류 아님"}}
json.dump(out, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(out["summary"]["total"], out["summary"]["pass"], out["summary"]["fail"])
