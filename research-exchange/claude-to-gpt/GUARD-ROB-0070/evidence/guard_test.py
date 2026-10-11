"""GUARD-ROB-0070 합성 · 재현 시험(성과 셈은 이미 공개된 n 24 · persist 3 세 칸만)."""
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import guard_robust as R  # noqa: E402
D, M = R.D, R.M
D.BASE_CSV = M.BASES / f"{M.name(R.G.BASE)}.csv"
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


g = R.grid()
chk("1 격자 60칸(지킴이 4 × n 5 × persist 3)", len(g) == 60 and len({R.key_of(*x[1:]) for x in g}) == 60)
a, b, c = R.calc("none", 24, 3), R.calc("A2_k4", 24, 3), R.calc("A0_k6", 24, 3)
chk("2 지금 판 재현(34.113% · 달 −14.043%)", a["annual_pct"] == 34.113 and a["worst_full_month_pct"] == -14.043)
chk("3 MONTH-POS-0055 재현(A2 −4%: 32.179% · −7.064% / A0 −6%: 32.425% · −9.309%)",
    b["annual_pct"] == 32.179 and b["worst_full_month_pct"] == -7.064 and c["annual_pct"] == 32.425 and c["worst_full_month_pct"] == -9.309)
mk = lambda gn, n, p, ann, w: {"guard_name": gn, "n": n, "persist": p, "annual_raw": ann, "within": w}
rows = [mk(gn, n, p, 0.30, True) for gn in R.GUARDS for n in R.N_SET for p in R.P_SET]
best, per = R.pick(rows)
chk("4 모두 같으면 이름 순 첫 지킴이", best == "A0_k4" and all(v["pass"] for v in per.values()))
rows = [mk(gn, n, p, 0.30 if gn != "A0_k4" else 0.33, not (gn == "A0_k4" and n == 32 and p == 4)) for gn in R.GUARDS for n in R.N_SET for p in R.P_SET]
chk("5 하나라도 밖이면 탈락", R.pick(rows)[0] == "A0_k6")
rows = [mk(gn, n, p, 0.30 - (0.0201 if gn == "A0_k4" else 0.0), True) for gn in R.GUARDS for n in R.N_SET for p in R.P_SET]
chk("6 15개 평균 연 −2%p 넘게 잃으면 탈락", R.pick(rows)[0] == "A0_k6")
rows = [mk(gn, n, p, 0.30 - (0.0201 if (gn == "A0_k6" and n == 24 and p == 3) else 0.0), True) for gn in R.GUARDS for n in R.N_SET for p in R.P_SET]
chk("7 지금 숫자 연 −2%p 넘게 잃으면 탈락(평균은 통과)", not R.pick(rows)[1]["A0_k6"]["pass"] and R.pick(rows)[1]["A0_k6"]["mean_ok"])
chk("8 모두 밖이면 None", R.pick([mk(gn, n, p, 0.3, gn == "none") for gn in R.GUARDS for n in R.N_SET for p in R.P_SET])[0] is None)
chk("9 잠금 통과", bool(R.verify_inputs()))
bad = json.loads(R.LOCK.read_text()); bad["research/guard_robust.py"] = "0" * 64
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
    json.dump(bad, fh)
try:
    R.verify_inputs(fh.name); chk("10 잠금 다르면 멈춤", False)
except SystemExit:
    chk("10 잠금 다르면 멈춤", True)
# 11 ~ 14 평가 상한 · 이어 하기(가짜 셈 · 임시 기록 칸)
real_calc, real_evals, real_out = R.calc, R.EVALS, R.OUT
tmp = Path(tempfile.mkdtemp())
R.EVALS, R.OUT = tmp / "evals.jsonl", tmp / "out"
calls = [0]


def fake(fail_at=None):
    def f(gn, n, p):
        calls[0] += 1
        if fail_at and calls[0] == fail_at:
            raise RuntimeError("일부러 실패")
        return {"annual_raw": 0.3, "annual_pct": 30.0, "worst_day_pct": -1.0, "worst_full_month_pct": -1.0, "mdd_report_pct": -1.0,
                "loss_months": 1, "within": True, "guard_days": 0, "min_cash_slack": 0.0}
    return f


def cnt():
    rs = [json.loads(x) for x in R.EVALS.read_text().splitlines()]
    return sum(r["status"] == "STARTED" for r in rs), len({r["key"] for r in rs if r["status"] == "DONE"}), sum(r["status"] == "FAILED" for r in rs)


R.calc = fake(fail_at=10)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        R.run()
    chk("11 10번째에서 실패", False)
except RuntimeError:
    chk("11 10번째에서 실패 → STARTED 10 · DONE 9 · FAILED 1", cnt() == (10, 9, 1))
calls[0] = 0
R.calc = fake()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    R.run()
out = json.loads(buf.getvalue())
chk("12 다시 돌리면 끝난 9개는 다시 안 셈(새 셈 51 · STARTED 61 · 고유 60)", calls[0] == 51 and cnt() == (61, 60, 1)
    and out["attempts"] == {"started": 61, "done_unique": 60, "failed": 1, "unique_settings": 60, "cap": 66})
calls[0] = 0
with contextlib.redirect_stdout(io.StringIO()):
    R.run()
chk("13 모두 끝난 뒤 또 돌려도 새 STARTED 0", calls[0] == 0 and cnt() == (61, 60, 1))
R.EVALS.write_text("".join(json.dumps({"status": "STARTED", "key": f"x{i}"}) + "\n" for i in range(7)))
try:
    R.run(); chk("14 상한 넘으면 첫 STARTED 전에 멈춤", False)
except SystemExit:
    chk("14 상한 넘으면 첫 STARTED 전에 멈춤(앞선 7 + 남은 60 > 66 · 새 기록 0)", cnt() == (7, 0, 0) and calls[0] == 0)
R.calc, R.EVALS, R.OUT = real_calc, real_evals, real_out
print(f"모두 통과 {ok}개")
