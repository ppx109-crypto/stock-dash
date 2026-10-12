"""KMF-0007 — 15분봉 기본 봇(KMF-0002 1분봉 기본 봇의 15분봉 쌍둥이) 한 칸 확인 · 시험 1.
사용자 2026-10-13 "1분봉은 하지말자"에 맞춰, 살아남은 유일한 봇(KMF-0002 · 아침 60분 범위 돌파 · 장 끝까지)을 15분봉 종가 판단으로 옮긴 칸
= KMF-0005의 `N60_day_e1`(그대로 · 새 설정 없음). 개발 값(+202.76p)은 이미 봄 · 확인 · 시험 1 값은 아무도 셈하지 않음.
절차(사전등록): ① 확인(06 ~ 08 · 09-01부터 안 읽음) → KMF val_pass ② 통과하면 바로 시험 1(09-01 ~ 10-12 · 10-13부터 안 읽음 · 비독립)
 · 통과 조건 합 > 0 · 가장 나쁜 날 ≥ −12.5p ③ 결정은 시험 2(10-13부터 새 자료)에서만.
python3 research/kmf7.py lock | run"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402
import kmf5 as K5  # noqa: E402

ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0007"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf5.py", "research/kmf7.py"]
CELL = "N60_day_e1"


def cfg():
    return next(c for c in K5.grid() if c["tag"] == CELL)


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
    verify_inputs()
    c = cfg()
    out = {"cell": CELL, "cfg": c}
    vb = K5.prep(K._rows_before(K.TEST[0]))
    log({"status": "STARTED", "stage": "val", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    days, trades = K.simulate(vb, K5.signals(vb, c))
    out["dev"] = K.stats(days, trades, *K.DEV)
    out["val"] = K.stats(days, trades, *K.VAL)
    out["val_pass"] = K.val_pass(out["dev"], out["val"])
    log({"status": "DONE", "stage": "val", "val_total_p": out["val"].get("total_p"), "val_pass": out["val_pass"]})
    if out["val_pass"]:
        tb = K5.prep(K._rows_before(K.TEST2_FROM))
        log({"status": "STARTED", "stage": "test1", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(tb, K5.signals(tb, c))
        out["test1"] = K.stats(days, trades, *K.TEST)
        t = out["test1"]
        out["pass1"] = t.get("days", 0) > 0 and t["total_p"] > 0 and t["worst_day_p"] >= K.DAY_STOP - 0.5
        out["val_check"] = K.stats(days, trades, *K.VAL)["total_p"]
        log({"status": "DONE", "stage": "test1", "test1_total_p": t.get("total_p"), "pass1": out["pass1"]})
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/result.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    v = ("WAITING_DATA(시험 2)" if out.get("pass1") else "NO_EDGE(시험 1)") if out["val_pass"] else "NO_EDGE(확인)"
    print(json.dumps({"verdict": v, "dev_total_p": out["dev"]["total_p"], "val_total_p": out["val"]["total_p"], "val_pass": out["val_pass"],
                      "test1_total_p": out.get("test1", {}).get("total_p"), "pass1": out.get("pass1")}, ensure_ascii=False))


if __name__ == "__main__":
    {"lock": write_lock, "run": run}[sys.argv[1]]()
