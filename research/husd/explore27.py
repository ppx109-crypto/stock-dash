"""H-USD 1단계(GPT #454 MPOS-0024): 이미 본 ETF 달 수익 탐색을 그대로 다시 셈(공개용 · 판정 아님 · 규칙 없음).
2026-10-17 #454 첫 댓글 표의 원래 셈(채팅 안 한 줄 셈)을 파일로 옮김. 입력:
- 계좌 달 수익: acc_month_base.json(MPOS-0021 BASE = REPRO_G · 114달 · 손실 달 40)
- 정배열 갈래 달 손익: ../attr_mix54/tier_month.json
- ETF 종가: 고정 나무 커밋 9743cb802의 etf-data/*.json(git show로 읽음 · 지금 작업 나무 값 아님) — 29개 중 달 ≥ 100인 27개만 표에 나옴.
  종가는 한투 수정주가(FID_ORG_ADJ_PRC=0)라 분배락에서 앞 값이 깎여 분배금이 반영됨(dist_check.py 참고).
달 수익 = 그달 마지막 종가 ÷ 전달 마지막 종가 − 1. 출력: explore27_out.json(표 · 입력 지문)."""
import glob
import hashlib
import json
import math
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = "9743cb802"
acc = json.load(open(HERE / "acc_month_base.json"))["달"]
tm = json.load(open(HERE.parent / "attr_mix54" / "tier_month.json"))
months = sorted(tm)
al = {m: tm[m]["정배열"] for m in months}
bad = [m for m in months if acc[m] < 0]
files = subprocess.run(["git", "ls-tree", "--name-only", TREE, "etf-data/"], capture_output=True, text=True, check=True).stdout.split()
fp = {}


def mret(path):
    raw = subprocess.run(["git", "show", f"{TREE}:{path}"], capture_output=True, check=True).stdout
    fp[path] = hashlib.sha256(raw).hexdigest()
    last = {}
    for dt, x in json.loads(raw)["closes"]:
        if x:
            last[dt[:6]] = float(x)
    ks = sorted(last)
    return {ks[i]: last[ks[i]] / last[ks[i - 1]] - 1 for i in range(1, len(ks))}


def corr(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    t = sum((a - mx) * (b - my) for a, b in zip(x, y))
    w = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return t / w if w else 0


rows, skipped = [], []
for f in sorted(files):
    code = Path(f).stem
    r = mret(f)
    ms = [m for m in months if m in r]
    if len(ms) < 100:
        skipped.append([code, len(ms)])
        continue
    bm = [r[m] for m in bad if m in r]
    om = [r[m] for m in ms if m not in bad]
    rows.append({"코드": code, "달 수": len(ms), "정배열과 상관": round(corr([r[m] for m in ms], [al[m] for m in ms]), 2),
                 "계좌와 상관": round(corr([r[m] for m in ms], [acc[m] for m in ms]), 2),
                 "계좌 손실 달 평균%": round(sum(bm) / len(bm) * 100, 2), "나머지 달 평균%": round(sum(om) / len(om) * 100, 2),
                 "손실 달에 +": f"{sum(1 for x in bm if x > 0)}/{len(bm)}"})
rows.sort(key=lambda r: r["계좌와 상관"])
out = {"고정 나무": TREE, "표": rows, "빠짐(달 < 100)": skipped, "본 ETF 수": len(files), "계좌 손실 달": len(bad),
       "입력 지문": {"acc_month_base.json": hashlib.sha256((HERE / "acc_month_base.json").read_bytes()).hexdigest(),
                 "tier_month.json": hashlib.sha256((HERE.parent / "attr_mix54" / "tier_month.json").read_bytes()).hexdigest(), **fp}}
json.dump(out, open(HERE / "explore27_out.json", "w"), ensure_ascii=False, indent=1)
for r in rows:
    print(*r.values())
print("빠짐", skipped)
