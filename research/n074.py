"""일봉 새 74회차 — 정배열 갈래를 4칸(40%)으로 키울 '모양' 조건(지금은 외국인 · 투신 3일 연속만).

표 재료(전고점 거리 · 거래량비 · 밴드 폭 · 정배열일수 · 추세 가속도)로, 같은 날 후보끼리가 아니라 그 줄 값 자체의 문턱으로 봄.
문턱은 전체 기간 나눔을 쓰지 않고 고정 숫자(뜻이 분명한 값)로만. 바뀐 매매 손익을 직접 봄.
실행: NRL_CACHE=... python3 research/n074.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule

print("== 일봉 새 74회차: 정배열 4칸 모양 조건 ==", flush=True)
base = T.once("지금 규칙(기준)")


def size_if(cond):
    return lambda r: 4 if rule.holds(r) else (4 if (nrl.steady(r) >= 3 or cond(r)) else 2)


rows = [r for rs in T.BY_DAY.values() for r in rs if not rule.holds(r)]
for key in ("250일 전고점 대비", "거래량비", "밴드 폭", "정배열일수", "추세 가속도"):
    vals = sorted(r.get(key) for r in rows if r.get(key) is not None)
    print(f"  (참고) 정배열 후보 {key} 나눔 10 · 50 · 90%:", [round(vals[int(len(vals) * q)], 3) for q in (0.1, 0.5, 0.9)], flush=True)
for tag, cond in (("250일 전고점 −2% 안(새 고점 근처)", lambda r: (r.get("250일 전고점 대비") or -99) >= -2),
                  ("250일 전고점 −5% 안", lambda r: (r.get("250일 전고점 대비") or -99) >= -5),
                  ("거래량비 1.5배 넘음", lambda r: (r.get("거래량비") or 0) >= 1.5),
                  ("거래량비 2배 넘음", lambda r: (r.get("거래량비") or 0) >= 2.0),
                  ("정배열 10일 안(막 됨)", lambda r: (r.get("정배열일수") or 999) <= 10),
                  ("정배열 60일 넘음(오래됨)", lambda r: (r.get("정배열일수") or 0) >= 60)):
    got = T.once("크기: 정배열도 " + tag + "면 4칸", size=size_if(cond))
    T.diff_check(base, got)
print("끝", flush=True)
