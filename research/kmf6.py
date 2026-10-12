"""KMF-0006 — 걷기 시험 고르기 봇(walk-forward selector) · '고르는 규칙 자체'가 시기 바뀜에도 살아남는지(사용자 2026-10-13 "변화에도 살아남을수있게").
후보(고정 · 이미 정해 둔 15 · 30분봉 규칙 · 1분봉 신호 없음): KMF-0004 14칸(RNA 눌림) + KMF-0005 12칸(15분봉 범위 돌파 · 일봉 RNA) = 26 + 쉼.
고르기(그달 첫날 앞까지 끝난 달만 봄): 매달 M(2026-03 ~ 10)마다 지난 L달(L 1 · 2 · 3) 합이 가장 큰 후보를 그달 내내 씀 ·
  가장 큰 합이 0 이하면 그달 쉼 · 같으면 이름 순.
판정(사전등록): 걷기 3 ~ 10월(10월은 12일까지) 합 > 0 · 여덟 달 가운데 다섯 이상 + · 가장 나쁜 날 ≥ −12.5p · 그리고 L 셋 가운데 둘 이상이 합 > 0
  → WF_CANDIDATE(절차 후보 · 시험 2에서 절차 그대로 결정) · 아니면 NO_EDGE.
python3 research/kmf6.py lock | run"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402
import kmf4 as K4  # noqa: E402
import kmf5 as K5  # noqa: E402

ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0006"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf5.py", "research/kmf6.py"]
MONTHS = ["202603", "202604", "202605", "202606", "202607", "202608", "202609", "202610"]
LOOKBACKS = (1, 2, 3)


def pool():
    return [("K4", c) for c in K4.grid()] + [("K5", c) for c in K5.grid()]


def pname(src, cfg):
    return f"{src}:{cfg['tag']}"


def daily_pnl(raw):
    """후보마다 {날: 손익} — 각 후보의 신호는 그 분(봉)까지 값만(KMF-0004 · 0005 미래 참조 검사 통과) · 날별 손익은 그날 안에서 끝남."""
    out = {}
    b5 = K5.prep(raw)
    for src, cfg in pool():
        b = K4.prep(raw, cfg) if src == "K4" else b5
        sig = K4.signals if src == "K4" else K5.signals
        days, _ = K.simulate(b, sig(b, cfg))
        out[pname(src, cfg)] = days
    return out


def month_sum(days, months):
    return sum(v for d, v in days.items() if d[:6] in months)


def prev_months(m, n):
    y, mo = int(m[:4]), int(m[4:])
    out = []
    for _ in range(n):
        mo -= 1
        if mo == 0:
            y, mo = y - 1, 12
        out.append(f"{y}{mo:02d}")
    return out


def choose(pnl, m, L):
    """달 M에 쓸 후보: 지난 L달(M 앞에 끝난 달만) 합 1등 · 0 이하면 None(쉼)."""
    past = prev_months(m, L)
    assert all(p < m for p in past)
    scores = sorted(((month_sum(days, past), name) for name, days in pnl.items()), key=lambda t: (-t[0], t[1]))
    best, name = scores[0]
    return (name if best > 0 else None), round(best, 2)


def walk(pnl, L):
    days_all = sorted({d for days in pnl.values() for d in days})
    rec, daily = [], {}
    for m in MONTHS:
        pick, score = choose(pnl, m, L)
        md = [d for d in days_all if d[:6] == m]
        for d in md:
            daily[d] = pnl[pick].get(d, 0.0) if pick else 0.0
        rec.append({"month": m, "pick": pick, "score_p": score, "month_p": round(sum(daily[d] for d in md), 2), "days": len(md)})
    vals = list(daily.values())
    return {"L": L, "months": rec, "total_p": round(sum(vals), 2), "pos_months": sum(1 for r in rec if r["month_p"] > 0),
            "worst_day_p": round(min(vals), 2), "best_day_p": round(max(vals), 2), "stop_days": sum(1 for v in vals if v <= K.DAY_STOP + 1e-9),
            "rest_months": sum(1 for r in rec if r["pick"] is None), "per_day_ci95_p": K.boot_ci(vals), "won_total": round(sum(vals) * K.MULT)}


def verdict(ws):
    def ok(w):
        return w["total_p"] > 0 and w["pos_months"] >= 5 and w["worst_day_p"] >= K.DAY_STOP - 0.5
    positive = sum(1 for w in ws if w["total_p"] > 0)
    return [w["L"] for w in ws if ok(w)], positive >= 2


def lock_body():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    body = {f: sha(ROOT / f) for f in CODE_FILES}
    body.update({f"kiwoom-data/{p.name}": sha(p) for p in (K.MINI, K.FUT)})
    return body


def verify_inputs(path=None):
    want = json.loads(Path(path or LOCK).read_text())
    have = lock_body()
    bad = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k))
    if bad:
        sys.exit("입력 잠금이 다름(멈춤): " + json.dumps(bad, ensure_ascii=False))
    return want


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1)); print(LOCK.read_text())


def log(rec):
    BOX.mkdir(parents=True, exist_ok=True)
    with open(EVALS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush(); os.fsync(fh.fileno())


def run():
    """후보 26 날별 손익(10-13부터 안 읽음) → L 1 · 2 · 3 걷기 → 판정. 같은 '쉼 없는 기준'으로 후보 평균도 보고."""
    verify_inputs()
    raw = K._rows_before(K.TEST2_FROM)
    log({"status": "STARTED", "stage": "pool", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    pnl = daily_pnl(raw)
    log({"status": "DONE", "stage": "pool", "n": len(pnl)})
    ws = [walk(pnl, L) for L in LOOKBACKS]
    passed, majority = verdict(ws)
    v = "WF_CANDIDATE " + ",".join(f"L{x}" for x in passed) if passed and majority else "NO_EDGE"
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/walk.json").write_text(json.dumps(ws, ensure_ascii=False, indent=1))
    (BOX / "evidence/pool_months.json").write_text(json.dumps({n: {m: round(month_sum(d, [m]), 2) for m in ["202601", "202602"] + MONTHS}
                                                               for n, d in pnl.items()}, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": v, "majority_positive": majority,
                      "walk": [{"L": w["L"], "total_p": w["total_p"], "pos_months": w["pos_months"], "worst_day_p": w["worst_day_p"],
                                "rest_months": w["rest_months"]} for w in ws]}, ensure_ascii=False))


if __name__ == "__main__":
    {"lock": write_lock, "run": run}[sys.argv[1]]()
