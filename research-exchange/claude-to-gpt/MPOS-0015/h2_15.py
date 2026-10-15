"""MPOS-0015 H2 진단(판정 없음 · GPT #438 · #439 H2): 같은 정배열 구간의 첫 진입 vs 반복 진입.
구간(진입 날 b까지 자료만): 그 종목의 단순이평 정배열(nrl.shape '정배열' · 정배열 문과 같은 모양)이 b까지 끊김 없이 이어진 날들의 시작 날.
첫 진입 = 그 구간 안에서 앞선 IMM 진입이 없음 · 반복 = 같은 구간 안 앞선 IMM 진입이 있음(앞선 진입의 결과는 안 씀 · 있었다는 사실만).
대상: IMM 장부 정배열 문 진입(규칙 문은 보고만). 결과 값: 진입 생애 손익(자리 가중 % · 장부 값). 반복은 앞선 진입이 끝났는지(b 전날까지)로도 나눔."""
import json
import math
import os
import statistics as S
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
RAW_PATH = SP + "z055_d1_raw.json"
SP_DIAG = SP + "r8/research-exchange/claude-to-gpt/MPOS-0012/diag12.json"
raw = json.load(open(RAW_PATH))
door = [x["door"] for x in json.load(open(SP + "r8/research-exchange/claude-to-gpt/MPOS-0012/diag12.json"))["매매"]]

# GPT #440 정정 3: 입력 지문 · 장부 줄과 diag12 매매의 행별 일치(종목 · 산 날 · 판 날 · 자리)
import hashlib as _h
_d12 = json.load(open(SP_DIAG))["매매"]
assert len(raw) == len(_d12) == 495 and all((r[0], r[1], r[2], int(r[4])) == (x["c"], x["b"], x["e"], int(x["s"])) for r, x in zip(raw, _d12))
INPUTS = {"z055_d1_raw.json": _h.sha256(open(RAW_PATH, "rb").read()).hexdigest(), "diag12.json": _h.sha256(open(SP_DIAG, "rb").read()).hexdigest()}
L = lab.lanes(nrl.prices)
ent = {}
for k, (c, b, e, p, s) in enumerate(raw):
    x = ent.setdefault((c, b), {"자리": 0, "손익": 0.0, "끝": "", "문": door[k]})
    x["자리"] += s
    x["손익"] += p * s
    x["끝"] = max(x["끝"], e)


def run_start(code, b):
    d = L[code]["날"]
    i = d.index(b)
    al = nrl.shape[code]["정배열"]
    if not al[i]:
        return None
    j = i
    while j - 1 >= 0 and al[j - 1]:
        j -= 1
    return d[j]


rows = []
for (c, b), v in sorted(ent.items(), key=lambda kv: kv[0][1]):
    st = run_start(c, b)
    prev = [(bb, w) for (cc, bb), w in ent.items() if cc == c and bb < b and st is not None and bb >= st]
    if st is None:
        kind = "구간 밖"
    elif not prev:
        kind = "첫"
    else:
        last = max(w["끝"] for _, w in prev)        # GPT #440: 앞 진입 마지막 판 날 < b · = b(같은 날 팔고 다시 삼) · > b(겹쳐 들고 있음)
        kind = "반복 · 앞 끝 < 산 날" if last < b else ("반복 · 앞 끝 = 산 날" if last == b else "반복 · 앞 끝 > 산 날")
    rows.append((kind, v["문"], v["손익"] / v["자리"], b))


def stat(vals):
    if len(vals) < 2:
        return {"건": len(vals)}
    m, sd = S.mean(vals), S.stdev(vals)
    return {"건": len(vals), "평균 %": round(m, 3), "t": round(m / (sd / math.sqrt(len(vals))), 2) if sd > 0 else None,
            "승률 %": round(sum(a > 0 for a in vals) / len(vals) * 100, 1)}


out = {}
for dr in ("정배열", "규칙"):
    for kind in ("첫", "반복 · 앞 끝 < 산 날", "반복 · 앞 끝 = 산 날", "반복 · 앞 끝 > 산 날", "구간 밖"):
        sel = [r for r in rows if r[0] == kind and r[1] == dr]
        out[f"{dr} · {kind}"] = {**stat([r[2] for r in sel]), "앞(~2021)": stat([r[2] for r in sel if r[3] < "20220101"]).get("평균 %"),
                                 "뒤(2022~)": stat([r[2] for r in sel if r[3] >= "20220101"]).get("평균 %")}
out["입력 지문"] = {**INPUTS, "NRL_CACHE": _h.sha256(open(os.environ["NRL_CACHE"], "rb").read()).hexdigest()}
json.dump(out, open(os.environ["OUT"], "w"), ensure_ascii=False, indent=1)
for k, v in out.items():
    print(k, v)
