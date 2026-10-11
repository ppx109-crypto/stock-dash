"""SAFE-LEV-0069 합성 · 재현 시험(성과 셈은 이미 공개된 L0.4 · n 24 · persist 3 하나만)."""
import json
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import safelev as S  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


g = S.grid()
chk("1 격자 60칸(몫 4 × n 5 × persist 3)", len(g) == 60 and len({x[0] for x in g}) == 60)
c = next(x for x in g if x[1] == 0.4 and x[2] == 24 and x[3] == 3)[4]
chk("2 L0.4 · n 24 · persist 3 = 지금 판 설정", c == dict(S.FINAL))
r = S.E.both(c)
chk("3 지금 판 재현(34.113% · 달 −14.043%)", r["full"]["annual_pct"] == 34.113 and r["full"]["worst_full_month_pct"] == -14.043)
mk = lambda lv, w: {"up_lev": lv, "full": {"within": w}}
rows = [mk(lv, True) for lv in S.UP_LEV for _ in range(15)]
chk("4 모두 견디면 가장 큰 몫", S.pick(rows)[0] == 0.40)
rows[-1] = mk(0.40, False)
chk("5 하나라도 밖이면 그 몫은 탈락", S.pick(rows)[0] == 0.35)
rows = [mk(lv, lv <= 0.30) for lv in S.UP_LEV for _ in range(15)]
chk("6 0.30까지만 견딤", S.pick(rows)[0] == 0.30)
chk("7 모두 밖이면 None", S.pick([mk(lv, False) for lv in S.UP_LEV for _ in range(15)])[0] is None)
chk("8 칸 수 모자라면 견딤 아님", S.pick([mk(0.25, True)] * 14)[0] is None)
chk("9 잠금 통과", bool(S.verify_inputs()))
bad = json.loads(S.LOCK.read_text()); bad["research/safelev.py"] = "0" * 64
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
    json.dump(bad, fh)
try:
    S.verify_inputs(fh.name); chk("10 잠금 다르면 멈춤", False)
except SystemExit:
    chk("10 잠금 다르면 멈춤", True)
print(f"모두 통과 {ok}개")
