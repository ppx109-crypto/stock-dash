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

# 11 ~ 14: 평가 상한 · 이어 하기(GPT #262) — 가짜 셈으로(성과 셈 없음) · 임시 기록 칸
import io, contextlib  # noqa: E402
real_both, real_evals, real_out = S.E.both, S.EVALS, S.OUT
tmp = Path(tempfile.mkdtemp())
S.EVALS, S.OUT = tmp / "evals.jsonl", tmp / "out"
calls = [0]


def fake(fail_at=None):
    def f(cfg):
        calls[0] += 1
        if fail_at and calls[0] == fail_at:
            raise RuntimeError("일부러 실패")
        w = {"within": cfg["up_lev"] <= 0.30, "annual_pct": 1.0, "worst_full_month_pct": -1.0, "worst_day_pct": -1.0}
        return {"full": w, "dev": dict(w)}
    return f


def cnt():
    rs = [json.loads(x) for x in S.EVALS.read_text().splitlines()]
    return sum(r["status"] == "STARTED" for r in rs), len({r["key"] for r in rs if r["status"] == "DONE"}), sum(r["status"] == "FAILED" for r in rs)


S.E.both = fake(fail_at=10)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        S.run()
    chk("11 10번째에서 실패", False)
except RuntimeError:
    chk("11 10번째에서 실패 → STARTED 10 · DONE 9 · FAILED 1", cnt() == (10, 9, 1))
calls[0] = 0
S.E.both = fake()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    S.run()
out = json.loads(buf.getvalue())
chk("12 다시 돌리면 끝난 9개는 다시 안 셈(새 셈 51 · STARTED 61 ≤ 66 · 고유 60)", calls[0] == 51 and cnt() == (61, 60, 1)
    and out["attempts"] == {"started": 61, "done_unique": 60, "failed": 1, "unique_settings": 60, "cap": 66} and out["verdict"] == "SAFE_SIZE_L0.3")
calls[0] = 0
with contextlib.redirect_stdout(io.StringIO()):
    S.run()
chk("13 모두 끝난 뒤 또 돌려도 새 STARTED 0", calls[0] == 0 and cnt() == (61, 60, 1))
S.EVALS.write_text("".join(json.dumps({"status": "STARTED", "key": f"x{i}"}) + "\n" for i in range(7)))
try:
    S.run(); chk("14 상한 넘으면 첫 STARTED 전에 멈춤", False)
except SystemExit:
    chk("14 상한 넘으면 첫 STARTED 전에 멈춤(앞선 7 + 남은 60 > 66 · 새 기록 0)", cnt() == (7, 0, 0) and calls[0] == 0)
S.E.both, S.EVALS, S.OUT = real_both, real_evals, real_out
print(f"모두 통과 {ok}개")
