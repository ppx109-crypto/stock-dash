"""MPOS-0015 HC 진단(판정 없음): 진입 자리 합(매수 때 정한 칸 · 칸이 모자라면 줄어든 값)별 생애 손익과 계좌 몫(자리 × 손익)의 합 · 앞뒤 반."""
import json
import math
import statistics as S
from pathlib import Path

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
raw = json.load(open(SP / "z055_d1_raw.json"))
door = [x["door"] for x in json.load(open(SP / "r8/research-exchange/claude-to-gpt/MPOS-0012/diag12.json"))["매매"]]
ent = {}
for k, (c, b, e, p, s) in enumerate(raw):
    x = ent.setdefault((c, b), {"자리": 0, "몫": 0.0, "문": door[k]})
    x["자리"] += s
    x["몫"] += p * s
out = {}
for sz in (1, 2, 3, 4):
    for dr in ("정배열", "규칙"):
        sel = [(b, v) for (c, b), v in ent.items() if v["자리"] == sz and v["문"] == dr]
        if not sel:
            continue
        r = [v["몫"] / v["자리"] for _, v in sel]
        m = S.mean(r)
        t = m / (S.stdev(r) / math.sqrt(len(r))) if len(r) > 1 and S.stdev(r) > 0 else None
        out[f"{sz}칸 · {dr}"] = {"진입": len(r), "평균 %": round(m, 3), "t": round(t, 2) if t else None, "몫 합(자리 × %)": round(sum(v["몫"] for _, v in sel), 1),
                                "앞 몫 합": round(sum(v["몫"] for b, v in sel if b < "20220101"), 1), "뒤 몫 합": round(sum(v["몫"] for b, v in sel if b >= "20220101"), 1),
                                "가장 나쁜 진입 몫": round(min(v["몫"] for _, v in sel), 1), "가장 좋은 진입 몫": round(max(v["몫"] for _, v in sel), 1)}
json.dump(out, open(SP / "mpos15/hc15.json", "w"), ensure_ascii=False, indent=1)
for k, v in out.items():
    print(k, v)
