"""MPOS-0015 HA 예측성 진단(판정 없음 · 규칙 없음 · GPT #439 순서).
상태(결과 보기 전 고정): 진입 기회 날 d에, **d 전날까지 진입 전체가 끝난**(부분 청산 줄을 묶어 마지막 판 날 ≤ d−1) 1일봉 진입 가운데
자리 가중 손익 합 < 0인 것의 수 K(창 W거래일: 마지막 판 날이 d−W ~ d−1). W = 10(가운데) · 5 · 20(보고).
대상: IMM 장부(= 원 1일봉 장부 · 495줄 · 466진입)의 모든 진입. 결과 값: 그 진입의 생애 손익(자리 가중 % · 왕복 0.25% 뒤 · 장부 값).
월 손실 · 이익 사후 라벨은 쓰지 않음. 정배열 · 규칙 문별로도 나눔. K 구간: 0 · 1 · 2 · 3+."""
import csv
import json
import math
import statistics as S
from pathlib import Path

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
HERE = SP / "mpos15"
RAW_PATH = SP / "z055_d1_raw.json"
SP_DIAG = SP / "r8/research-exchange/claude-to-gpt/MPOS-0012/diag12.json"
raw = json.load(open(RAW_PATH))
door = [x["door"] for x in json.load(open(SP / "r8/research-exchange/claude-to-gpt/MPOS-0012/diag12.json"))["매매"]]

# GPT #440 정정 3: 입력 지문 · 장부 줄과 diag12 매매의 행별 일치(종목 · 산 날 · 판 날 · 자리)
import hashlib as _h
_d12 = json.load(open(SP_DIAG))["매매"]
assert len(raw) == len(_d12) == 495 and all((r[0], r[1], r[2], int(r[4])) == (x["c"], x["b"], x["e"], int(x["s"])) for r, x in zip(raw, _d12))
INPUTS = {"z055_d1_raw.json": _h.sha256(open(RAW_PATH, "rb").read()).hexdigest(), "diag12.json": _h.sha256(open(SP_DIAG, "rb").read()).hexdigest()}
days = [r["날"] for r in csv.DictReader(open(SP / "mpos14/base_IMM.csv"))]
ix = {d: i for i, d in enumerate(days)}

ent = {}
for k, (c, b, e, p, s) in enumerate(raw):
    x = ent.setdefault((c, b), {"자리": 0, "손익": 0.0, "끝": "", "문": door[k]})
    x["자리"] += s
    x["손익"] += p * s
    x["끝"] = max(x["끝"], e)
E = sorted(ent.items(), key=lambda kv: kv[0][1])
closed = sorted((ix[v["끝"]], v["손익"] / v["자리"]) for v in ent.values() if v["끝"] in ix)


def K(d, W):
    i = ix[d]
    return sum(1 for j, pnl in closed if i - W <= j <= i - 1 and pnl < 0)


def stat(v):
    if len(v) < 2:
        return {"건": len(v)}
    m, sd = S.mean(v), S.stdev(v)
    return {"건": len(v), "평균 %": round(m, 3), "t": round(m / (sd / math.sqrt(len(v))), 2) if sd > 0 else None,
            "승률 %": round(sum(a > 0 for a in v) / len(v) * 100, 1)}


out = {"진입 수": len(E), "정의": __doc__, "입력 지문": INPUTS,
       "빠진 진입(산 날이 바탕 달력 2017-02-01 앞)": [k for k, v in E if k[1] not in ix],
       "끝이 바탕 달력 밖이라 K에서 빠진 진입 수": sum(1 for v in ent.values() if v["끝"] not in ix),
       "주의": "바탕 달력이 2017-02-01에 시작 → 초반 진입의 K는 왼쪽이 잘림(진짜 무손실이 아닐 수 있음) · 평균은 '진입별 자리 가중 생애 수익률(Σp×s/Σs)'의 진입 간 단순 평균"}
for W in (10, 5, 20):
    rows = [(min(K(b, W), 3), v["손익"] / v["자리"], v["문"], b) for (c, b), v in E if b in ix]
    res = {}
    for kk in (0, 1, 2, 3):
        for dr in ("전체", "정배열", "규칙"):
            sel = [r for r in rows if r[0] == kk and (dr == "전체" or r[2] == dr)]
            res[f"K={kk if kk < 3 else '3+'} · {dr}"] = {**stat([r[1] for r in sel]),
                                                    "앞(~2021)": stat([r[1] for r in sel if r[3] < "20220101"]).get("평균 %"),
                                                    "뒤(2022~)": stat([r[1] for r in sel if r[3] >= "20220101"]).get("평균 %")}
    hi = [r[1] for r in rows if r[0] >= 2]
    lo = [r[1] for r in rows if r[0] <= 1]
    d = S.mean(hi) - S.mean(lo) if hi and lo else None
    se = math.sqrt(S.variance(hi) / len(hi) + S.variance(lo) / len(lo)) if len(hi) > 1 and len(lo) > 1 else None
    res["K≥2 − K≤1 평균 차 %p · t(웰치)"] = [round(d, 3) if d is not None else None, round(d / se, 2) if se else None]
    out[f"W={W}"] = res
json.dump(out, open(HERE / "ha15.json", "w"), ensure_ascii=False, indent=1)
for W in (10, 5, 20):
    print("W", W)
    for k, v in out[f"W={W}"].items():
        print("  ", k, v)
