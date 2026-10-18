"""정직 NRL 캐시(RECOUNT.md 2절): 정직 캐시 next 판을 nrl.py 캐시 모양 (prices, lanes, shape, BR, inside, _calm, CALM_MONTH)으로 씀.
prices = study.load_prices(고정 나무 · 정직 캐시와 같은 가격판) · lanes = lab.lanes(prices) · inside = SINCE 뒤 행(날 · 종목 순) ·
_calm = None(전체 문턱을 쓰는 곳이 있으면 추세 문이 닫힘 — 장부는 정직 달 문턱으로 바꿔 끼움) · CALM_MONTH = None.
EX_FULL = 정직 캐시 next pkl · EX_OUT = 새 캐시 경로 · EX_OLD = 옛 캐시(가격 같음 여부만 비교). cwd = 고정 나무 · tree_run."""
import hashlib
import json
import os
import pickle
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402

H = pickle.load(open(os.environ["EX_FULL"], "rb"))
assert H["실측"]["주식수"] == os.environ.get("EX_SHARES", "next"), "판 라벨(주식수)이 EX_SHARES와 다름"   # MPOS-0027: same 판도 같은 함수로
P = study.load_prices()
lanes = lab.lanes(P)
inside = [H["inside"][k] for k in sorted(H["inside"], key=lambda k: (k[1], k[0])) if k[1] >= rule.SINCE]
with open(os.environ["EX_OUT"], "wb") as fh:
    pickle.dump((P, lanes, H["shape"], H["BR"], inside, None, None), fh, protocol=pickle.HIGHEST_PROTOCOL)
old = pickle.load(open(os.environ["EX_OLD"], "rb"))
op = old[0]
sh = lambda d: hashlib.sha256(json.dumps({c: d[c]["rows"] for c in sorted(d)}).encode()).hexdigest()  # noqa: E731
diff = sorted(c for c in set(P) | set(op) if c not in P or c not in op or P[c]["rows"] != op[c]["rows"])
print(json.dumps({"주식수 판": H["실측"]["주식수"], "inside 행": len(inside), "BR 날": len(H["BR"]), "shape 종목": len(H["shape"]), "가격 종목 새 · 옛": [len(P), len(op)],
                  "가격 지문 새 · 옛": [sh(P), sh(op)], "가격 다른 종목 수": len(diff), "다른 종목 앞 10": diff[:10]}, ensure_ascii=False))
