"""MPOS-0018 H2 자료 감사(수익률 안 봄 · GPT #443): credit-data(날짜 · 잔고율 · 잔고주수 · 공여율 · 신규주수 · 상환주수)에서
잔고 변화 = 신규 − 상환인지(오차 1% 또는 1주 안) · 연속 날짜 · 액면분할 같은 주수 단위 끊김(하루 잔고 5배 이상 뜀) · 종목별 마지막 날."""
import collections
import json
from pathlib import Path

ROOT = Path("/home/user/stock-dash/credit-data")
tot = ok = 0
jumps, lastd, years = 0, collections.Counter(), collections.Counter()
bad_by_year = collections.Counter()
for f in sorted(ROOT.glob("*.json")):
    d = json.load(open(f))
    rows = sorted(d.get("rows") or [], key=lambda r: r[0])
    if rows:
        lastd[rows[-1][0]] += 1
    for a, b in zip(rows, rows[1:]):
        if None in (a[2], b[2], b[4], b[5]):
            continue
        tot += 1
        years[b[0][:4]] += 1
        dlt, flow = b[2] - a[2], b[4] - b[5]
        if abs(dlt - flow) <= max(1.0, 0.01 * max(abs(a[2]), 1.0)):
            ok += 1
        else:
            bad_by_year[b[0][:4]] += 1
        if a[2] > 0 and (b[2] / a[2] > 5 or b[2] / a[2] < 0.2):
            jumps += 1
out = {"종목": len(list(ROOT.glob('*.json'))), "이어진 날 쌍": tot, "잔고 변화 = 신규 − 상환(1% 안)": ok, "맞는 몫 %": round(ok / tot * 100, 2) if tot else None,
       "안 맞는 쌍 연도별": dict(sorted(bad_by_year.items())), "하루 잔고 5배 넘게 뜀(단위 끊김 후보)": jumps,
       "종목별 마지막 날 분포 상위": lastd.most_common(5)}
json.dump(out, open(Path(__file__).with_suffix(".json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
