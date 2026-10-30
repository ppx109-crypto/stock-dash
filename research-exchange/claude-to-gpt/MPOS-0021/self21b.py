"""MPOS-0021 합성 시험 B(GPT #450 2): 고정 나무의 진짜 lab.run으로 진입 기록(parts21.Entries)의 요청 칸 · 배정 칸과
보유 칸 관찰(parts21.HeldAudit)을 확인 — 자리 부족 · 같은 날 여러 진입 · 끝까지 안 판 보유 · 결정 안 바뀜.
cwd = 고정 나무 · tree_run으로 실행. 출력: EX_OUT(json 영수증)."""
import hashlib
import json
import os
import sys
import types

sys.path.insert(0, os.getcwd())
import lab  # noqa: E402

_SRC = open(os.environ["EX_PARTS"], "rb").read()
P = types.SimpleNamespace()
exec(compile(_SRC, os.environ["EX_PARTS"], "exec"), P.__dict__)
out = {"부품 지문": hashlib.sha256(_SRC).hexdigest(), "행": []}


def check(name, ok, **info):
    out["행"].append({"시험": name, "판정": "PASS" if ok else "FAIL", **info})


DAYS = ["20200102", "20200103", "20200106", "20200107", "20200108"]
px = {c: {"rows": [(d, 100.0) for d in DAYS]} for c in ("A", "B", "C")}
rows = [{"date": "20200102", "code": c, "i": 0, "중기 이격밴드": k} for k, c in enumerate(("A", "B", "C"))]
rows.append({"date": DAYS[-1], "code": "끝", "i": 0})
want = {"A": 2, "B": 2, "C": 1}


def run(size_fn, sell_on=None):
    lab._lanes_for = lab._days_for = None
    ex = P.HeldAudit(lambda ln, s, p, st, pk, row=None: bool(sell_on and ln["code"] == sell_on and st >= 1), DAYS[-1])
    ent = P.Entries(size_fn)
    g = lab.run(rows, px, lambda r: r["code"] != "끝", ex, slots=3, detail=True, size=ent)
    return ent, ex, g


# 자리 3 · 같은 날 A(2) · B(2) · C(1) 요청 → A 2 · B 1(자리 부족) · C는 자리 없어 안 삼
ent, ex, g = run(lambda r: want[r["code"]])
got = [tuple(e) for e in ent.rows]
check("같은 날 여러 진입 · 자리 부족: 요청 칸과 배정 칸이 다르게 기록", got == [("A", "20200102", 2, 2), ("B", "20200102", 2, 1)], 얻음=got)
held = {k[0]: v for k, v in ex.held.items()}
check("다음 날 보유 칸 관찰 = 배정 칸(A 2 · B 1)", held == {"A": 2, "B": 1}, 얻음=held)
check("끝까지 안 판 보유도 진입 기록에 남음(장부 줄 없음)", not (g or {}).get("매매목록") and len(ent.rows) == 2)
# 결정 안 바뀜: 덮개 없이 돈 판과 보유 칸이 같음
lab._lanes_for = lab._days_for = None
seen = {}


def plain_exit(ln, s, p, st, pk, row=None):
    spot = sys._getframe(1).f_locals["spot"]
    seen.setdefault(ln["code"], spot["자리"])
    return False


lab.run(rows, px, lambda r: r["code"] != "끝", plain_exit, slots=3, detail=True, size=lambda r: want[r["code"]])
check("덮개 없는 판과 보유 칸 같음(결정 안 바뀜)", seen == held, 덮개없음=seen)
# 큰 요청: 자리 3에 요청 4 → 배정 3
ent, ex, g = run(lambda r: 4)
check("자리 3 · 요청 4 → 배정 3", [tuple(e) for e in ent.rows][:1] == [("A", "20200102", 4, 3)], 얻음=ent.rows[:1])
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1)
print(sum(r["판정"] == "PASS" for r in out["행"]), "/", len(out["행"]))
sys.exit(0 if all(r["판정"] == "PASS" for r in out["행"]) else 3)
