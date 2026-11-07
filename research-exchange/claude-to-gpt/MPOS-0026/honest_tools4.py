"""정직 캐시 도구 시험 ⑫(SHARES_NEXT.md 4절 · 합성 · 손익 없음 · honest_cache.py 원문 exec).
가짜 공시 줄(caps.timeline을 바꿔 끼움): 금 20200103 접수(첫 보고) · 토 20200104 접수 · 금 20200110 같은 날 두 보고(300 · 400).
next: 첫 보고 당일 모름 · 주말 접수는 월요일부터 · 같은 날 두 보고는 다음 거래일부터 가장 큰 수(지금 규칙) · 공시 자르기(접수일 < 그날) 반영.
same(지금 caps.known_by와 같음): 접수 당일에 씀(누수 쪽) — 두 규칙이 갈리는 것을 확인.
cwd = 고정 나무 · tree_run. 출력: 인자 1(json)."""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
_HC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "honest_cache.py")
_ns = {"__name__": "honest_cache", "__file__": _HC}
exec(compile(open(_HC, encoding="utf-8").read(), _HC, "exec"), _ns)
caps = _ns["caps"]
FAKE = {"Z1": (("20200103", 100), ("20200104", 200), ("20200110", 300), ("20200110", 400))}
real = caps.timeline
caps.timeline = lambda code: FAKE.get(code, ())
try:
    nx, sm = _ns["make_known"]("next"), _ns["make_known"]("same")
    cut = _ns["make_known"]("next", filings_upto="20200110", filings_strict=True)
    got = {
        "next 금 0103(첫 보고 당일) = 모름": nx("Z1", "20200103") is None,
        "same 금 0103 = 100(당일 사용)": sm("Z1", "20200103") == 100,
        "next 월 0106 = 200(토 접수 → 월부터)": nx("Z1", "20200106") == 200,
        "next 금 0110 = 200(당일 두 보고 아직 안 씀)": nx("Z1", "20200110") == 200,
        "same 금 0110 = 400(당일 · 가장 큰 수)": sm("Z1", "20200110") == 400,
        "next 월 0113 = 400(다음 거래일 · 가장 큰 수)": nx("Z1", "20200113") == 400,
        "공시 자름(접수일 < 0110) 뒤 월 0113 = 200": cut("Z1", "20200113") == 200,
        "공시 없는 종목 = 모름": nx("Z9", "20200113") is None,
        "same은 caps.known_by와 같음": all(sm("Z1", d) == caps.known_by("Z1", d) for d in ("20200102", "20200103", "20200106", "20200110", "20200113")),
    }
finally:
    caps.timeline = real
res = {"⑫ known_next 합성": got, "모두 통과": all(got.values())}
json.dump(res, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
sys.exit(0 if res["모두 통과"] else 3)
