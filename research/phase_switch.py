"""PHASE-SWITCH-0046 — 국면에 따라 신호를 바꾸는 판을 아직 열지 않은 T(2022 ~ 2026)에서 한 번 확인(진단 · 규칙 채택 없음).
- 근거: SIG-MAP-0045(#204 NO_STABLE_SIGNAL 인정 6096894255)의 M(2006 ~ 2021) 국면별 평균.
  고르는 식(기계적): 국면마다 수급이 아닌 여섯 신호(S1 · S2 · S3 · S4 · S7 · S8) 가운데 M 국면 평균이 가장 큰 것.
  → 오름 = S8_MOM120_SKIP20(0.563) · 횡보 = S7_EMA_ALIGN(0.329) · 내림 = S2_REV5(1.345). 이 표는 `pick_from_map()`이 SIG-MAP 결과 파일에서 다시 셈.
- 잼: sig_map.spreads()를 그대로 씀(t날 값 → t+1 종가 ~ t+11 종가 · 위 20% − 아래 20% · S7은 3점 − 0점).
  날마다 그날 국면(굽기 안 069500 60일 ±5%)의 신호 값만 씀. 그 신호 값이 없는 날은 뺌.
- 판정(T): ① 평균 > 0 ② 2022 ~ 2026 다섯 해 가운데 3해 이상 + ③ 바꾸는 판 평균 > 'S7을 늘 쓰는 판' 평균(같은 날들)
  모두면 PHASE_SWITCH_IN_REUSED_T · 아니면 PHASE_SWITCH_REJECTED · independent_validation은 늘 WAITING_DATA.
python3 research/phase_switch.py --t      잠금 확인 → O_EXCL 영수증 → 고르기 → T 셈(이 한 번뿐)
python3 research/phase_switch.py --lock   잠금 파일 쓰기(성과 셈 없음)"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash/research")
import sig_map as G  # noqa: E402

ROOT = Path("/home/user/stock-dash")
BOX = ROOT / "research-exchange/claude-to-gpt/PHASE-SWITCH-0046"
MAP_RESULT = ROOT / "research-exchange/claude-to-gpt/SIG-MAP-0045/evidence/t_main.json"
LOCK = BOX / "t_lock.json"
RECEIPT = BOX / "t_receipt.json"
POOL = ("S1_MOM20", "S2_REV5", "S3_HIGH120", "S4_LOWVOL60", "S7_EMA_ALIGN", "S8_MOM120_SKIP20")
WANT = {"오름": "S8_MOM120_SKIP20", "횡보": "S7_EMA_ALIGN", "내림": "S2_REV5"}
YEARS = ("2022", "2023", "2024", "2025", "2026")


def pick_from_map(table):
    """국면마다 POOL에서 M 국면 평균이 가장 큰 신호(같으면 POOL 앞)."""
    return {p: max(POOL, key=lambda k: (table[k]["phase_pct"][p], -POOL.index(k))) for p in ("오름", "횡보", "내림")}


def combine(res, plan):
    """{날: (값, 국면, 쓴 신호)} — 그날 국면의 신호 값만."""
    out = {}
    days = set().union(*[set(v) for v in res.values()])
    for d in sorted(days):
        for k, got in res.items():
            if d in got:
                ph = got[d][1]
                break
        sig = plan[ph]
        if d in res[sig]:
            out[d] = (res[sig][d][0], ph, sig)
    return out


def judge(comb, base):
    same = [d for d in comb if d in base]
    m = G.mean([comb[d][0] for d in comb])
    ys = {y: G.mean([v for d, (v, _, _) in comb.items() if d[:4] == y]) for y in YEARS}
    pos = sum(1 for v in ys.values() if v is not None and v > 0)
    cm = G.mean([comb[d][0] for d in same])
    bm = G.mean([base[d][0] for d in same])
    c1 = m is not None and m > 0
    c2 = pos >= 3
    c3 = cm is not None and bm is not None and cm > bm
    return {"days": len(comb), "mean_pct": None if m is None else round(m * 100, 3), "years_pos": f"{pos}/5",
            "years_pct": {y: (None if v is None else round(v * 100, 3)) for y, v in ys.items()},
            "phase_pct": {p: (lambda xs: None if not xs else round(sum(xs) / len(xs) * 100, 3))([v for v, q, _ in comb.values() if q == p])
                          for p in ("오름", "횡보", "내림")},
            "phase_days": {p: sum(1 for _, q, _ in comb.values() if q == p) for p in ("오름", "횡보", "내림")},
            "same_days": len(same), "switch_mean_same_days_pct": None if cm is None else round(cm * 100, 3),
            "always_S7_mean_same_days_pct": None if bm is None else round(bm * 100, 3),
            "c1_mean_gt0": c1, "c2_years_ge_3": c2, "c3_beats_always_S7": c3,
            "verdict": "PHASE_SWITCH_IN_REUSED_T" if (c1 and c2 and c3) else "PHASE_SWITCH_REJECTED"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lock_body():
    return {"research/phase_switch.py": sha(__file__), "research/sig_map.py": sha(G.__file__), "/tmp/sig-t.pkl": sha(G.T_PART[0]),
            "SIG-MAP-0045/evidence/t_main.json": sha(MAP_RESULT)}


def run_t():
    want = json.loads(LOCK.read_text())
    have = lock_body()
    if want != have:
        sys.exit("잠금이 다름(멈춤): " + json.dumps({k: (want.get(k), v) for k, v in have.items() if want.get(k) != v}, ensure_ascii=False))
    key = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    import subprocess
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    body = {"status": "STARTED", "lock_key": key, "git_head": head, "at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}
    try:
        fd = os.open(str(RECEIPT), os.O_CREAT | os.O_EXCL | os.O_WRONLY)     # 어떤 성과 셈보다 먼저
    except FileExistsError:
        sys.exit("영수증이 이미 있음(멈춤) — 한 번만 돌림")
    with os.fdopen(fd, "w") as fh:
        fh.write(json.dumps(body, ensure_ascii=False))
        fh.flush()
        os.fsync(fh.fileno())
    plan = pick_from_map(json.loads(MAP_RESULT.read_text())["map"])
    if plan != WANT:
        sys.exit("고른 표가 사전등록과 다름(멈춤): " + json.dumps(plan, ensure_ascii=False))
    res = G.merge([G.T_PART], only=tuple(sorted(set(plan.values()))))
    comb = combine(res, plan)
    out = {"task": "PHASE-SWITCH-0046", "phase": "T", "lock_key": key, "receipt": body, "plan": plan,
           "T": judge(comb, res["S7_EMA_ALIGN"]), "independent_validation": "WAITING_DATA",
           "report_only_always": {k: {"mean_pct": round(G.mean([v for v, _ in res[k].values()]) * 100, 3), "days": len(res[k])}
                                  for k in sorted(res) if res[k]}}
    out["verdict"] = out["T"]["verdict"]
    print(json.dumps(out, ensure_ascii=False))


def main():
    if "--t" in sys.argv:
        return run_t()
    if "--lock" in sys.argv:
        BOX.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1))
        print(LOCK.read_text())
        return
    sys.exit("영수증 없는 성과 셈은 없음 — --t(한 번) · --lock만 됩니다")


if __name__ == "__main__":
    main()
