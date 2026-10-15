"""z100gd.py 만들기(MPOS-0013 진단 · 매매 성과 안 바꿈): MPOS-0012의 z100g.py에 1일봉 매매별 기록만 더함.
- 산 돈(−) · 판 돈(비용 뒤 +)을 (장부 줄 번호, 달)로 모음 · 날마다 1일봉 보유 평가액을 남김 → 매매별 달 손익 = 달 끝 평가 − 달 초 평가 + 흐름.
- 다른 줄은 그대로라 바탕 csv는 z100g와 바이트까지 같아야 함(영수증으로 확인)."""
import hashlib
import sys
from pathlib import Path

SRC = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/r8/research-exchange/claude-to-gpt/MPOS-0012/z100g.py")
SRC_SHA = "8f98f97a"
PATCH = [
    ('''    pl = _dd(float)
    attr_rows = []
''', '''    pl = _dd(float)
    attr_rows = []
    TF, VAL = _dd(float), {}                                   # z100gd: 1일봉 매매별 흐름 · 날마다 평가액
'''),
    ('''        cash += amt - c
        costs += c
        pl[lane(p)] -= c
''', '''        cash += amt - c
        costs += c
        pl[lane(p)] -= c
        if p["bot"] == "1d":
            TF[f"{key[1]}|{d[:6]}"] += amt - c                  # z100gd
'''),
    ('''        pos[key] = dict(bot=bot, code=code, val=money - c, px=px, day=d, **kw)
''', '''        pos[key] = dict(bot=bot, code=code, val=money - c, px=px, day=d, **kw)
        if bot == "1d":
            TF[f"{key[1]}|{d[:6]}"] -= money                    # z100gd
'''),
    ('''        by = {b: sum(p["val"] for p in pos.values() if p["bot"] == b) for b in ("1d", "15m", "basket", "engine")}
''', '''        VAL[d] = {str(k[1]): p["val"] for k, p in pos.items() if p["bot"] == "1d"}   # z100gd
        by = {b: sum(p["val"] for p in pos.values() if p["bot"] == b) for b in ("1d", "15m", "basket", "engine")}
'''),
    ('''    if os.getenv("Z_ATTR"):
''', '''    if os.getenv("Z_TRADE_OUT"):                               # z100gd
        json.dump({"흐름": TF, "값": VAL}, open(os.getenv("Z_TRADE_OUT"), "w"))
    if os.getenv("Z_ATTR"):
'''),
]


def make(out):
    s = SRC.read_text(encoding="utf-8")
    assert hashlib.sha256(s.encode()).hexdigest().startswith(SRC_SHA)
    for a, b in PATCH:
        assert s.count(a) == 1, a[:60]
        s = s.replace(a, b)
    Path(out).write_text(s, encoding="utf-8")


if __name__ == "__main__":
    make(sys.argv[1])
