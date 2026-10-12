"""KMF-0002 — 키움 미니 코스피200 선물 기본 봇 1번: '하루 한 번 돌파 · 장 끝까지 들고 가기'(ORB-1).
사용자 2026-10-12: "한번에는 안 나올거야 · 한투처럼 1일봉 개발하고 보완할 봇 개발하고 손실 분석 후 줄일 방법 개발하고 천천히 · 리더가 알아서".
근거(KMF-0001 개발 기간 손실 분석 · 판정 밖): ORB 30분의 개발 이익은 모두 15시 장 끝 정리 거래(+713p)에서 나왔고,
범위 안으로 돌아올 때 정리 → 다시 들기를 되풀이한 거래(9 ~ 14시 정리)는 −508p · 멈춘 날 하루 7.7번 매매.
규칙(그 분 종가까지 값만): 그날 첫 N분 고가 · 저가 = 범위 → 그 뒤 종가가 범위 위면 삼 · 아래면 팖(하루 최대 max_entries번 들기)
  → 장 끝(15:30)까지 들고 감. 멈춤: 'day' = 하루 −12p 멈춤만 · 'range' = 종가가 반대쪽 범위를 넘으면 정리(+ 하루 −12p).
체결 · 비용 · −12p · 15:30 정리 · 기간 · 시험 1 · 2 잣대는 KMF-0001(research/kmf.py)과 같음.
python3 research/kmf2.py lock | run | cut | final | final2"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402  (load · simulate · stats · eligible · val_pass · 기간 · 시험 2 자료 규칙을 그대로 씀)

ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0002"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
FINAL_OK = BOX / "final_ok.json"
FINAL_OUT = BOX / "evidence/final.json"
TEST2_LOCK = BOX / "test2_lock.json"
FINAL2_OUT = BOX / "evidence/final2.json"
CODE_FILES = ["research/kmf.py", "research/kmf2.py"]


def grid():
    """고정 12칸: 범위 N분 {15 · 30 · 60} × 하루 들기 {1 · 2}번 × 멈춤 {day · range}."""
    return [{"bot": "ORB1", "or": n, "max_entries": e, "stop": s} for n in (15, 30, 60) for e in (1, 2) for s in ("day", "range")]


def signals(rows, cfg):
    """분마다 원하는 자리(+1 · −1 · 0 · None). 범위는 그날 첫 분부터 N분(늦게 연 날도 그날 첫 분 기준)."""
    n = len(rows)
    want = [None] * n
    i = 0
    while i < n:
        d = rows[i][0]
        j = i
        while j < n and rows[j][0] == d:
            j += 1
        start = rows[i][1]
        hi = lo = None
        pos, entries = 0, 0
        for k in range(i, j):
            m, h, l, c = rows[k][1], rows[k][3], rows[k][4], rows[k][5]
            if m < start + cfg["or"]:                       # 범위 만드는 중(그 분까지 값만)
                hi = h if hi is None else max(hi, h)
                lo = l if lo is None else min(lo, l)
                continue
            if hi is None:
                continue
            if pos == 0:
                if entries < cfg["max_entries"] and m <= K.ENTRY_TO:
                    if c > hi:
                        want[k], pos, entries = 1, 1, entries + 1
                    elif c < lo:
                        want[k], pos, entries = -1, -1, entries + 1
            elif cfg["stop"] == "range" and ((pos > 0 and c < lo) or (pos < 0 and c > hi)):
                want[k], pos = 0, 0                          # 반대쪽 범위를 넘으면 정리
        i = j
    return want


def name(cfg):
    return K.name(cfg)


def neighbors(cfg):
    return [g for g in grid() if g != cfg and sum(g[k] != cfg[k] for k in cfg) == 1]


def lock_body():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    body = {"root": str(ROOT)}
    body.update({f: sha(ROOT / f) for f in CODE_FILES})
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


def _pass(t):
    return t.get("days", 0) > 0 and t["total_p"] > 0 and t["worst_day_p"] >= K.DAY_STOP - 0.5


def run():
    """① 개발 12칸(06-01부터 안 읽음) → ② 1차 조건 넘은 칸 중 개발 합 1등 한 칸 → ③ 그 칸만 확인(09-01 앞까지 읽음)."""
    verify_inputs()
    rows = K._rows_before(K.VAL[0])
    res = {}
    for cfg in grid():
        key = name(cfg)
        log({"status": "STARTED", "key": key, "stage": "dev", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(rows, signals(rows, cfg))
        res[key] = {"cfg": cfg, "dev": K.stats(days, trades, *K.DEV)}
        log({"status": "DONE", "key": key, "stage": "dev", "dev_total_p": res[key]["dev"].get("total_p")})
    cands = sorted([k for k, v in res.items() if K.eligible(v["dev"])], key=lambda k: (-res[k]["dev"]["total_p"], k))
    pick = None
    if cands:
        k = cands[0]
        pick = {"name": k, "cfg": res[k]["cfg"], "dev": res[k]["dev"],
                "neighbors_dev": {name(nb): res[name(nb)]["dev"].get("total_p") for nb in neighbors(res[k]["cfg"])}}
        vrows = K._rows_before(K.TEST[0])
        log({"status": "STARTED", "key": k, "stage": "val", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(vrows, signals(vrows, pick["cfg"]))
        pick["dev_check"] = K.stats(days, trades, *K.DEV)["total_p"]
        pick["val"] = K.stats(days, trades, *K.VAL)
        pick["val_pass"] = K.val_pass(pick["dev"], pick["val"])
        log({"status": "DONE", "key": k, "stage": "val", "val_total_p": pick["val"].get("total_p")})
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/dev_rows.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    (BOX / "evidence/pick.json").write_text(json.dumps(pick, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": ("VAL_PASS" if pick and pick["val_pass"] else "NO_EDGE"), "eligible": cands,
                      "pick": pick and {"name": pick["name"], "dev_total_p": pick["dev"]["total_p"], "dev_check": pick["dev_check"],
                                        "val_total_p": pick["val"]["total_p"], "val_pass": pick["val_pass"]}}, ensure_ascii=False))


def final():
    """시험 1(09-01 ~ 10-12 · 비독립) 한 번 · 확인 통과 칸만 · 동의 파일 있을 때 · 늘 WAITING_DATA."""
    verify_inputs()
    if FINAL_OUT.exists():
        sys.exit("시험 1은 이미 한 번 돌렸음(멈춤)")
    if not FINAL_OK.exists():
        sys.exit("지피티 동의 파일이 없음(멈춤)")
    pick = json.loads((BOX / "evidence/pick.json").read_text())
    ok = json.loads(FINAL_OK.read_text())
    if not pick or not pick.get("val_pass") or ok.get("pick") != pick["name"]:
        sys.exit("확인 통과 칸이 아니거나 동의 파일과 다름(멈춤)")
    rows = K._rows_before(K.TEST2_FROM)
    days, trades = K.simulate(rows, signals(rows, pick["cfg"]))
    t = K.stats(days, trades, *K.TEST)
    FINAL_OUT.write_text(json.dumps({"ok": ok, "name": pick["name"], "cfg": pick["cfg"], "test1": t, "pass1": _pass(t)}, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": "WAITING_DATA(시험 2)", "test1_total_p": t.get("total_p"), "pass1": _pass(t)}, ensure_ascii=False))


def final2():
    """시험 2(10-13 ~ 새 자료 · 20거래일 이상 · 결정) 한 번. 거래일 수는 셈 전에 자료만 보고 확인."""
    verify_inputs()
    if FINAL2_OUT.exists():
        sys.exit("시험 2는 이미 한 번 돌렸음(멈춤)")
    if not FINAL_OUT.exists():
        sys.exit("시험 1을 먼저(멈춤)")
    if not (TEST2_LOCK.exists() and K.TEST2_FILE.exists()):
        sys.exit("시험 2 자료 · 잠금이 없음(WAITING_DATA)")
    lock2 = json.loads(TEST2_LOCK.read_text())
    if hashlib.sha256(K.TEST2_FILE.read_bytes()).hexdigest() != lock2.get("sha256") or not lock2.get("gpt_pr"):
        sys.exit("시험 2 자료가 잠금과 다르거나 지피티 동의가 없음(멈춤)")
    rows = K.load()
    n2 = len({r[0] for r in rows if r[0] >= K.TEST2_FROM})
    if n2 < K.TEST2_MIN_DAYS:                               # 셈 전에 막음(엔진 접촉 없음)
        sys.exit(f"시험 2 자료가 {n2}거래일뿐(WAITING_DATA)")
    first = json.loads(FINAL_OUT.read_text())
    days, trades = K.simulate(rows, signals(rows, first["cfg"]))
    t = K.stats(days, trades, K.TEST2_FROM, "99991231")
    p2 = _pass(t)
    FINAL2_OUT.write_text(json.dumps({"lock": lock2, "name": first["name"], "test2": t, "pass1": first["pass1"], "pass2": p2}, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": "KMF_CANDIDATE" if first["pass1"] and p2 else "NO_EDGE", "test2_total_p": t.get("total_p")}, ensure_ascii=False))


def cut():
    """자르기 시험(개발 기간 안 · 기준 판도 06-01부터 안 읽음): 자른 날 앞까지 날별 손익이 같아야 함."""
    cuts = ("20260302", "20260401", "20260504")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf2 as K2;rows=K.load();"
            "c=json.loads(os.environ['KC']);d,_=K.simulate(rows,K2.signals(rows,c));print(json.dumps(d))")
    res = []
    for cfg in (grid()[2], grid()[7], grid()[11]):
        env = dict(os.environ, KC=json.dumps(cfg), KMF_CUT=K.VAL[0])
        full = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for ct in cuts:
            env["KMF_CUT"] = ct
            part = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in part if d < ct]
            res.append({"cfg": name(cfg), "cut": ct, "days": len(ds), "diff": sum(1 for d in ds if abs(part[d] - full[d]) > 1e-9),
                        "no_future_days": all(d < ct for d in part)})
    print(json.dumps({"pass": all(r["diff"] == 0 and r["no_future_days"] for r in res), "runs": res}, ensure_ascii=False))


if __name__ == "__main__":
    {"lock": write_lock, "cut": cut, "run": run, "final": final, "final2": final2}[sys.argv[1]]()
