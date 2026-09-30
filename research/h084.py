"""1시간봉 84회차 — 자료 점검에서 찾은 빈틈 ②: 희석 공시 날짜. dart-events(DART 주요사항보고서 API)는 고친 보고서 날만 남는 때가 있음
(예: 고려아연 유상증자 첫 발표 2024-10-30 → dart-events엔 2024-11-14). event-data(공시 목록, 193종목)엔 첫 발표 · 정정이 모두 있음.
① 희석 날 = dart-events ∪ event-data(본 회사의 유상증자결정 · 전환사채 · 신주인수권부사채 · 교환사채 발행결정 — 종속 · 자회사 것은 뺌)로 희석 거르기(20 · 40일).
② event-data의 다른 공시가 좋은/나쁜 신호인가: 공급계약 · 최대주주변경 · 실적공시(20일 안) — 막아 보고 막힌 매매 손익을 봄(193종목만이라 참고).
공시는 접수 다음 날부터(사는 봉에 붙은 전 거래일 재료의 날까지 접수된 것)."""
import sys, json, bisect, re
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
DIL = ("유상증자", "전환사채", "신주인수권부사채", "교환사채")
DAYS, DS5, EVD, OTH = {}, {}, {}, {}
own = re.compile(r"주요사항보고서\((유상증자결정|전환사채권발행결정|신주인수권부사채권발행결정|교환사채권발행결정)\)")
for c in data:
    p = Path(f"price-data/{c}.json")
    DAYS[c] = [x[0] for x in json.loads(p.read_text(encoding="utf-8"))["closes"]] if p.exists() else []
    e = H._events(c); DS5[c] = sorted(x for k in DIL for x in e.get(k, ()))
    q = Path(f"event-data/{c}.json"); EVD[c] = []; OTH[c] = {}
    if q.exists():
        for x in json.loads(q.read_text(encoding="utf-8"))["rows"]:
            t = x.get("title", ""); d = x.get("date", "")
            if own.search(t) and "종속" not in t and "자회사" not in t: EVD[c].append(d)
            OTH[c].setdefault(x.get("kind"), []).append(d)
        EVD[c].sort()
        for k in OTH[c]: OTH[c][k].sort()
def had(dates, c, day, n):
    d = DAYS[c]; i = bisect.bisect_right(d, day) - 1
    if i < 0: return False
    lo = d[max(0, i - n)]; j = bisect.bisect_right(dates, lo)
    return j < len(dates) and dates[j] <= day
def entry_of(fn):
    cache = {}
    for c, b in data.items():
        m = sigs[c].copy(); n = len(b["t"])
        for k in np.flatnonzero(m):
            x = ATT[c][k + 1] if k + 1 < n else ATT[c][k]
            if x and fn(c, x["날"]): m[k] = False
        cache[c] = m
    return lambda c, b: cache[c]
def trim(e):
    sg = {c: np.asarray(e(c, b), bool) for c, b in data.items()}; got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sg, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
print("== 1시간봉 84회차 (공시 날짜 바로잡기 · 공시 목록의 다른 재료) ==", flush=True)
print(f"  event-data 있는 종목 {sum(1 for c in data if OTH[c])}/{len(data)} · 본 회사 희석 첫 발표 날 {sum(len(v) for v in EVD.values())}개 · dart-events 희석 날 {sum(len(v) for v in DS5.values())}개", flush=True)
early = [(c, d) for c in data for d in EVD[c] if not any(abs(int(d) - int(x)) < 100 and x <= d for x in DS5[c])]
print(f"  event-data에만 있거나 dart-events보다 이른 희석 날(대강) {len(early)}개 · 예: {early[:6]}", flush=True)
base = None
cases = [("지금(거르기 없음)", lambda c, b: sigs[c]),
         ("희석 20일 · dart-events만(72회차)", entry_of(lambda c, day: had(DS5[c], c, day, 20))),
         ("희석 20일 · 첫 발표 날 더함", entry_of(lambda c, day: had(sorted(DS5[c] + EVD[c]), c, day, 20))),
         ("희석 40일 · 첫 발표 날 더함", entry_of(lambda c, day: had(sorted(DS5[c] + EVD[c]), c, day, 40)))]
for kind in ("공급계약", "최대주주변경", "실적공시"):
    cases.append((f"{kind} 20일 안이면 막음(참고)", entry_of(lambda c, day, kind=kind: had(OTH[c].get(kind, []), c, day, 20))))
for tag, e in cases:
    res = H.simulate(data, e, EX, size, rank=rank, stale_of=stale90, seeds=16)
    tr = trim(e)
    nb = sum(int((sigs[c] & ~np.asarray(e(c, b), bool)).sum()) for c, b in data.items())
    msg = ""
    if base is None: base = res
    else:
        for s in ("앞", "뒤"):
            k1 = {(t["code"], t["산 때"]) for t in res[s]["목록"]}
            gone = [t for t in base[s]["목록"] if (t["code"], t["산 때"]) not in k1]
            msg += f" · {s} 빠진 매매 {len(gone)}건 평균 {np.mean([t['손익'] for t in gone]) if gone else 0:+.2f}%"
    print(f"  {tag:30s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']} · 막힌 신호 {nb}{msg}", flush=True)
print("끝", flush=True)
