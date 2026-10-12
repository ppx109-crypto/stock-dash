"""시험 2 자료 점검 · 잠금 준비(손익 셈 없음 · 자료 꼴만 봄).
사용자가 다른 PC에서 모은 10-13부터 키움 1분봉 CSV를 받아 kiwoom-data/mini_1min_test2.csv(첫 파일과 같은 꼴: date,minute,open,high,low,close,volume)로 바꾸고,
날마다 봉 수 · 완전한 거래일(09:00 ~ 15:30 가운데 380분 이상) 수 · sha256을 보고합니다. test2_lock.json의 바탕(gpt_pr 빈칸)도 만듭니다.
받는 꼴 둘: ① date,minute,open,high,low,close,volume ② datetime,code,open,high,low,close,volume(키움 큰 파일 꼴 · 미니 A056*만 · 그날 거래량 합 1등 계약)
python3 research/kmf_test2_data.py <받은 CSV> [<받은 CSV> ...]"""
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402

FULL_MIN_BARS = 380


def read_any(path):
    """→ {날: [(분, 시가, 고가, 저가, 종가, 거래량)]} · 10-13부터만 · 09:00 ~ 15:34."""
    out = defaultdict(dict)
    with open(path, encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        cols = set(rd.fieldnames or [])
        if {"date", "minute"} <= cols:
            for r in rd:
                d, m = r["date"], int(r["minute"])
                if d >= K.TEST2_FROM and K.FIRST_MIN <= m <= K.LAST_MIN:
                    out[d][("", m)] = (m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"])))
        elif {"datetime", "code"} <= cols:
            for r in rd:
                d = r["datetime"][:10].replace("-", "")
                if d < K.TEST2_FROM or not r["code"].startswith("A056"):
                    continue
                m = int(r["datetime"][11:13]) * 60 + int(r["datetime"][14:16])
                if K.FIRST_MIN <= m <= K.LAST_MIN:
                    out[d][(r["code"], m)] = (m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"])))
        else:
            sys.exit(f"모르는 꼴(멈춤): {sorted(cols)}")
    days = {}
    for d, rows in out.items():
        codes = {c for c, _ in rows}
        if codes == {""}:
            days[d] = sorted(rows.values())
        else:
            vol = Counter()
            for (c, _), v in rows.items():
                vol[c] += v[5]
            main = sorted(vol.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            days[d] = sorted(v for (c, _), v in rows.items() if c == main)
    return days


def check(days):
    rep, bad = {}, []
    for d in sorted(days):
        rows = days[d]
        mins = [r[0] for r in rows]
        n = sum(1 for m in mins if m <= K.FLAT_AT)
        broken = sum(1 for r in rows if not (r[3] <= min(r[1], r[4]) and r[2] >= max(r[1], r[4])))
        dup = len(mins) - len(set(mins))
        rep[d] = {"bars": len(rows), "bars_to_1530": n, "first": mins[0], "last": mins[-1], "broken": broken, "dup": dup, "full": n >= FULL_MIN_BARS}
        if broken or dup:
            bad.append(d)
    return rep, bad


def main(paths):
    days = {}
    for p in paths:
        for d, rows in read_any(p).items():
            days.setdefault(d, [])
            seen = {r[0] for r in days[d]}
            days[d] += [r for r in rows if r[0] not in seen]
    rep, bad = check(days)
    if bad:
        sys.exit("틀린 봉 · 겹침이 있는 날(멈춤): " + ", ".join(bad))
    out = K.TEST2_FILE
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "minute", "open", "high", "low", "close", "volume"])
        for d in sorted(days):
            for r in sorted(days[d]):
                w.writerow([d, r[0], r[1], r[2], r[3], r[4], r[5]])
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    full = [d for d, v in rep.items() if v["full"]]
    summary = {"file": out.name, "sha256": sha, "days": len(rep), "full_days": len(full),
               "first_day": min(rep) if rep else None, "last_day": max(rep) if rep else None, "enough": len(full) >= K.TEST2_MIN_DAYS,
               "not_full": {d: v["bars_to_1530"] for d, v in rep.items() if not v["full"]}}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


if __name__ == "__main__":
    main(sys.argv[1:])
