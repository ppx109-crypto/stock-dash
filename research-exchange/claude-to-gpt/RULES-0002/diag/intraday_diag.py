"""RULES-0002 15분봉 · 1시간봉 진단 재생 — 연구 재생기(research/x004.py의 m15 · h1k 갈래와 같은 호출)로 한 판씩.
python intraday_diag.py <경로 바꾼 기준점 복사본(b3)> <m15|h1k> <ASIS|FLOAT-V1|FLOW-LAG2|FLOW-LAG3> <결과 폴더>"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as K  # noqa: E402

BASE, PART, VAR, OUT = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
import os  # noqa: E402
for k in ("Q_BARS", "Q_SCALE", "Q_SPAN", "HLAB_ST_CACHE", "CAPS_ADJ"):
    os.environ.pop(k, None)
if PART == "h1k":
    os.environ["Q_BARS"] = "1h"
BASE = K.lock_base(BASE)
t0 = time.time()
SHIFT = {"FLOW-LAG2": 1, "FLOW-LAG3": 2}.get(VAR, 0)
import numpy as np  # noqa: E402
import hlab  # noqa: E402

# F2: hlab.daily_context의 수급 끝을 SHIFT줄 앞으로(원본 글에서 한 줄만 바꿔 같은 모듈에 다시 정의)
src = Path(hlab.__file__).read_text(encoding="utf-8")
a, b = src.index("def daily_context("), src.index("\ndef _events(")
fn = src[a:b]
OLD = "k = bisect.bisect_right(fdays, day)"
assert fn.count(OLD) == 1
if SHIFT:
    exec(compile(fn.replace(OLD, OLD + " - _FLOW_SHIFT"), "hlab.daily_context(수급 끝 당김)", "exec"), hlab.__dict__)
hlab._FLOW_SHIFT = SHIFT

G = {"__name__": "rules0002"}
RAW_OLD = "f = bisect.bisect_left(fd, day) - 1"
if PART == "m15":
    code = K.read_patched(Path(BASE) / "research/q023.py", BASE).split('\npart = os.environ')[0]
    exec(compile(code, "q023(앞부분)", "exec"), G)
    if SHIFT:      # q_rule.raw(같은 봉 순서의 수급)도 같은 만큼 당김 — tiers가 부를 때 G의 raw를 씀
        qsrc = Path(BASE, "research/q_rule.py").read_text(encoding="utf-8")
        a, b = qsrc.index("def raw("), qsrc.index("\ndef tiers(")
        assert qsrc[a:b].count(RAW_OLD) == 1
        exec(compile(qsrc[a:b].replace(RAW_OLD, RAW_OLD + " - _FLOW_SHIFT"), "q_rule.raw(수급 끝 당김)", "exec"), G)
    G["_FLOW_SHIFT"] = SHIFT
    sig_fn = G["entry3"](al_mkt=-0.01)
    data = G["data"]
    SG = {c: np.asarray(sig_fn(c, b), bool) for c, b in data.items()}
    RANK = G["rank_plus"](G["tiers"](SG))
else:
    qsrc = Path(BASE, "research/q_rule.py").read_text(encoding="utf-8")
    assert qsrc.count(RAW_OLD) == 1
    if SHIFT:
        qsrc = qsrc.replace(RAW_OLD, RAW_OLD + " - _FLOW_SHIFT")
    G["_FLOW_SHIFT"] = SHIFT
    exec(compile(qsrc, "q_rule(1h)", "exec"), G)
    data = G["data"]
    SG = {c: np.asarray(G["SIGS"][c], bool) for c in data}
    RANK = G["RANK"]

ATT, door, SCALE = G["ATT"], G["door"], G["SCALE"]
orig_exit, orig_stale = G["exit_rule"], G["stale90"]
LOG, EVAL = [], {"trend": 0, "aligned": 0, "stale": 0}


def note(rule, c, p, k, close, f, x):
    if f != x:
        LOG.append({"rule": rule, "code": c, "entry_bar": data[c]["t"][p["i"]], "bar": data[c]["t"][k], "held": int(k - p["i"]),
                    "price": float(p["price"]), "close": float(close), "float": bool(f), "exact": bool(x)})


asis = VAR != "FLOAT-V1"


def exit_rule(c, b, p, k):
    close, price = b["c"][k], p["price"]
    now = (close / price - 1) * 100
    kind = door(ATT[c][p["i"]]) or "정배열"
    held = k - p["i"]
    if kind == "추세":
        EVAL["trend"] += 1
        f_t, x_t = now >= 13, K.ge(close, price, 13)
        f_s, x_s = now <= -5, K.le(close, price, -5)
        note("trend_tp13", c, p, k, close, f_t, x_t)
        note("trend_sl5", c, p, k, close, f_s, x_s)
        if ((f_t or f_s) if asis else (x_t or x_s)) or held >= 60 * SCALE:
            return "all"
        before = b["c"][p["i"]:k].max() if k > p["i"] else -1
        same = p["칸"] == p["처음칸"]
        f_h = now >= 5 and (before / price - 1) * 100 < 5 and same
        x_h = K.ge(close, price, 5) and K.lt(before, price, 5) and same
        note("trend_half5_first", c, p, k, close, f_h, x_h)
        if f_h if asis else x_h:
            return max(1, p["처음칸"] // 2)
        return 0
    EVAL["aligned"] += 1
    f_s, x_s = now <= -10, K.le(close, price, -10)
    note("aligned_sl10", c, p, k, close, f_s, x_s)
    if f_s if asis else x_s:
        return "all"
    f_p = (p["peak"] / price - 1) * 100 >= 8 and now <= 1
    x_p = K.ge(p["peak"], price, 8) and K.le(close, price, 1)
    note("aligned_peak8_now1", c, p, k, close, f_p, x_p)
    if f_p if asis else x_p:
        return "all"
    if k + 1 < len(b["t"]):
        nx = ATT[c][k + 1]
        if nx is not None and not nx["정배열"]:
            return "all"
    return 0


def stale90(p):
    EVAL["stale"] += 1
    if not (p["now"] - p["i"] >= 7 * SCALE):
        return False
    close = data[p["code"]]["c"][p["now"]]
    f, x = (close / p["price"] - 1) * 100 < 4, K.lt(close, p["price"], 4)
    if f != x:
        LOG.append({"rule": "stale_lt4", "code": p["code"], "entry_bar": data[p["code"]]["t"][p["i"]], "bar": data[p["code"]]["t"][p["now"]],
                    "held": int(p["now"] - p["i"]), "price": float(p["price"]), "close": float(close), "float": bool(f), "exact": bool(x)})
    if not (f if asis else x):
        return False
    xx = ATT[p["code"]][p["now"]]
    return (xx["시장폭"] if xx and xx["시장폭"] is not None else 100) < 90


# 원본과 옮긴 판이 ASIS에서 같은 답을 내는지(옮김 오류 막기)는 ASIS 결과를 원본 함수 판과 견줘 확인
res = G["M"].simulate(data, lambda c, b: SG[c], exit_rule, G["size"], rank=RANK, stale_of=stale90, seeds=1)
check = None
if VAR == "ASIS":
    res0 = G["M"].simulate(data, lambda c, b: SG[c], orig_exit, G["size"], rank=RANK, stale_of=orig_stale, seeds=1)
    L = lambda r: [(t["code"], t["산 때"], t["판 때"], t["손익"], t["칸"]) for s in ("앞", "뒤") for t in r[s]["목록"]]
    check = {"same_as_original_functions": L(res) == L(res0), "n": len(L(res))}
ledger = [(t["code"], t["산 때"], t["판 때"].lstrip("끝"), float(t["손익"]), int(t["칸"])) for s in ("앞", "뒤") for t in res[s]["목록"]]
summ = {s: {k: v for k, v in res[s].items() if k != "목록" and not isinstance(v, (list, dict))} for s in ("앞", "뒤")}
cand = sorted({(c, data[c]["t"][k][:8]) for c, m in SG.items() for k in np.flatnonzero(m)})
att_flags = {}
for c, rows in ATT.items():
    seen = {}
    for t, x in zip(data[c]["t"], rows):
        if x is not None and t[:8] not in seen:
            seen[t[:8]] = [x.get("가르침"), x.get("3일연속"), x.get("수급끝")]
    att_flags[c] = seen
out = {"part": PART, "variant": VAR, "shift": SHIFT, "scale": SCALE, "codes": len(data), "summary": summ, "ledger": ledger,
       "signal_days": [list(x) for x in cand], "att_flags": att_flags, "evaluations": EVAL, "mismatch": LOG,
       "asis_transcription_check": check, "module_origin_violations": K.module_origins(BASE), "seconds": round(time.time() - t0)}
(OUT / f"{PART}_{VAR}.json").write_text(json.dumps(out, ensure_ascii=False, default=str), encoding="utf-8")
print(PART, VAR, "끝", out["seconds"], "초 · 매매", len(ledger), "· 다른 판단", len(LOG), "· 옮김 확인", check, "· 출처 위반", len(out["module_origin_violations"]), flush=True)
