"""E 2회차 — 증권사 적정주가(목표가)와 분기 실적 발표 사이의 연결(사용자 질문 2026-10-02):
"1분기 실적 발표 → 적정주가 10만원이 나오면 2분기 실적 발표 전까지 유지되는 것 같다."

자료: opinion-data(증권사별 목표가 · 2017~) · price-data(수정 종가) · quarter-data(실적 보고서 접수일).
목표가는 그날 값 그대로라 액면분할 앞뒤가 안 맞음 → 분기마다 '목표가 ÷ 수정 종가' 가운데 값이 1.6배 넘게 뛰면 그 앞을 그만큼 나눠 맞춤.

[A] 목표가가 바뀌는 때: 실적 보고서 접수일 기준 몇 주 앞뒤에 몰리나(올림 · 내림 · 그대로)
[B] 한 증권사가 정한 목표가는 얼마나 가나: 다음에 바꿀 때까지 날수 · 다음 실적 철 전에 바꾸는 몫
[C] 실적 사이(한 '철') 안에서 주가와 목표가: 철 첫날 목표가 대비 여유(목표가 ÷ 주가 − 1)별로
    · 다음 실적 전까지 주가가 목표가에 닿는 몫 · 그 사이 수익 · 철 안의 이른 · 중간 · 늦은 때 여유별 앞으로 20일 수익
[D] 실적 뒤 목표가 고침(접수 40일 앞 → 20일 뒤 가운데 값 바뀜)과 그 뒤 20 · 60일 수익(그 철 표본 평균 대비)
두 반: 2017~2020 / 2021~."""
import bisect
import glob
import json
import os
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

MID = "20210101"
D = lambda s: date(int(s[:4]), int(s[4:6]), int(s[6:8]))
S = lambda d: d.strftime("%Y%m%d")


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def filings(code):
    """실적 보고서 접수일 목록(1분기 · 반기 · 3분기 · 사업)."""
    body = load(f"quarter-data/{code}.json") or {}
    got = sorted({str(v["접수번호"])[:8] for v in (body.get("rows") or {}).values()
                  if v and str(v.get("접수번호", ""))[:8].isdigit()})
    return [d for d in got if d >= "20160101"]


def fix_split(rows, close_at):
    """분기마다 log(목표가 ÷ 종가) 가운데 값을 보고, 1.6배 넘게 뛴 곳 앞쪽 목표가를 나눠 맞춤(뒤 → 앞으로)."""
    by_q = defaultdict(list)
    for r in rows:
        c = close_at(r["date"])
        if c:
            by_q[r["date"][:4] + str((int(r["date"][4:6]) - 1) // 3)].append(np.log(r["target"] / c))
    qs = sorted(by_q)
    med = {q: float(np.median(by_q[q])) for q in qs}
    scale, factor = {}, 0.0
    for a, b in zip(reversed(qs[:-1]), reversed(qs[1:])):
        jump = med[a] - med[b]
        if abs(jump) > np.log(1.6):
            factor += jump
        scale[a] = factor
    out = []
    for r in rows:
        q = r["date"][:4] + str((int(r["date"][4:6]) - 1) // 3)
        out.append({**r, "target": r["target"] / np.exp(scale.get(q, 0.0))})
    return out


DATA = {}
for p in sorted(glob.glob("opinion-data/*.json")):
    code = os.path.basename(p)[:-5]
    px = load(f"price-data/{code}.json")
    body = load(p)
    if not px or not body:
        continue
    cl = [(d, c) for d, c in px["closes"] if d >= "20160101" and c]
    if len(cl) < 300:
        continue
    pdays = [d for d, _ in cl]
    pc = np.array([c for _, c in cl], float)

    def close_at(d, pdays=pdays, pc=pc):
        k = bisect.bisect_right(pdays, d) - 1
        return pc[k] if k >= 0 and pdays[k] >= S(D(d) - timedelta(days=7)) else None
    rows = sorted([r for r in body["rows"] if r.get("target") and r["target"] > 0 and r.get("member")], key=lambda r: r["date"])
    if len(rows) < 20:
        continue
    DATA[code] = {"days": pdays, "c": pc, "ops": fix_split(rows, close_at), "f": filings(code)}
print(f"== E 2회차: 목표가와 실적 발표 · 종목 {len(DATA)}(실적 접수일 있는 {sum(1 for v in DATA.values() if v['f'])}) ==", flush=True)

# ── [A] 바뀌는 때 ──
print("\n[A] 증권사별 목표가가 '바뀐' 날이 가장 가까운 실적 접수일 기준 어디에 있나(주 단위)", flush=True)
weeks = {"올림": Counter(), "내림": Counter(), "그대로(다시 냄)": Counter()}
total = Counter()
for code, v in DATA.items():
    if not v["f"]:
        continue
    fd = v["f"]
    last = {}
    for r in v["ops"]:
        m = r["member"]
        prev = last.get(m)
        last[m] = r
        if not prev:
            continue
        ch = r["target"] / prev["target"] - 1
        kind = "올림" if ch > 0.01 else "내림" if ch < -0.01 else "그대로(다시 냄)"
        k = bisect.bisect_left(fd, r["date"])
        cands = [fd[j] for j in (k - 1, k) if 0 <= j < len(fd)]
        if not cands:
            continue
        near = min(cands, key=lambda x: abs((D(r["date"]) - D(x)).days))
        w = (D(r["date"]) - D(near)).days // 7
        w = max(-7, min(6, w))
        weeks[kind][w] += 1
        total[kind] += 1
print("  주(접수일=0) | " + " ".join(f"{w:>5d}" for w in range(-7, 7)), flush=True)
for kind, cnt in weeks.items():
    print(f"  {kind:10s} | " + " ".join(f"{cnt[w] / max(1, total[kind]) * 100:5.1f}" for w in range(-7, 7)) + f"  (모두 {total[kind]}건, %)", flush=True)

# ── [B] 얼마나 가나 ──
print("\n[B] 한 증권사의 목표가가 다음에 바뀔 때까지(같은 값 다시 내는 것은 이어짐으로 봄)", flush=True)
spans, before_next = [], Counter()
for code, v in DATA.items():
    fd = v["f"]
    by_m = defaultdict(list)
    for r in v["ops"]:
        by_m[r["member"]].append(r)
    for m, rs in by_m.items():
        cur = rs[0]
        for r in rs[1:]:
            if abs(r["target"] / cur["target"] - 1) > 0.01:
                days = (D(r["date"]) - D(cur["date"])).days
                if days <= 400:
                    spans.append(days)
                    if fd:
                        k = bisect.bisect_right(fd, cur["date"])       # cur 뒤 첫 접수일
                        if k < len(fd):
                            nxt = fd[k]
                            gap = (D(r["date"]) - D(nxt)).days
                            before_next["다음 실적 30일 넘게 앞에 바꿈" if gap < -30 else
                                        "다음 실적 앞 30일 안" if gap < 0 else
                                        "다음 실적 뒤 30일 안" if gap <= 30 else "그 뒤(한 철 넘게 둠)"] += 1
                cur = r
a = np.array(spans)
print(f"  바뀐 {len(a)}번 · 가운데 {np.median(a):.0f}일 · 30일 안 {np.mean(a <= 30) * 100:.0f}% · 31~100일 {np.mean((a > 30) & (a <= 100)) * 100:.0f}% · "
      f"100일 넘게 {np.mean(a > 100) * 100:.0f}%", flush=True)
n = sum(before_next.values())
print("  다음 실적 접수일 기준 언제 바꿨나: " + " · ".join(f"{k} {c / n * 100:.0f}%" for k, c in before_next.most_common()), flush=True)


# ── 날마다 가운데 목표가(180일 안에 낸 증권사의 마지막 값들) ──
def consensus(v, day):
    last = {}
    lo = S(D(day) - timedelta(days=180))
    for r in v["ops"]:
        if r["date"] >= day:
            break
        if r["date"] >= lo:
            last[r["member"]] = r["target"]
    return float(np.median(list(last.values()))) if len(last) >= 2 else None


def px_idx(v, day):
    """day 다음 거래일 자리(그날 장 뒤 알고 다음 날 종가에 삼)."""
    return bisect.bisect_right(v["days"], day)


# ── [C] 실적 사이 한 철 ──
print("\n[C] 실적 접수일 사이 한 철 — 철 첫날(접수 5일 뒤) 가운데 목표가 대비 여유별", flush=True)
cyc = []
for code, v in DATA.items():
    fd = v["f"]
    for a_, b_ in zip(fd, fd[1:]):
        if (D(b_) - D(a_)).days < 40:
            continue
        start = S(D(a_) + timedelta(days=5))
        t = consensus(v, start)
        i = px_idx(v, start)
        j = bisect.bisect_left(v["days"], b_)               # 다음 접수일 전날까지
        if t is None or i >= len(v["days"]) or j - i < 20:
            continue
        c0 = v["c"][i]
        path = v["c"][i:j]
        gap = t / c0 - 1
        reach = bool(np.max(path) >= t) if gap > 0 else bool(np.min(path) <= t)
        cyc.append({"code": code, "day": v["days"][i], "gap": gap, "reach": reach, "ret": path[-1] / c0 - 1,
                    "len": j - i, "t": t, "v": v, "i": i, "j": j})
mean_by = defaultdict(list)
for x in cyc:
    mean_by[x["day"][:6]].append(x["ret"])
mean_by = {k: float(np.mean(v)) for k, v in mean_by.items()}
TIERS = ((-1, 0, "목표가가 주가 아래"), (0, 0.15, "여유 0~15%"), (0.15, 0.3, "여유 15~30%"), (0.3, 0.5, "여유 30~50%"), (0.5, 9, "여유 50%↑"))
for side, test in (("앞(2017~2020)", lambda d: d < MID), ("뒤(2021~)", lambda d: d >= MID)):
    print(f"  {side}", flush=True)
    for lo, hi, nm in TIERS:
        sel = [x for x in cyc if test(x["day"]) and lo <= x["gap"] < hi]
        if len(sel) < 20:
            continue
        r = np.array([x["ret"] for x in sel])
        exr = np.array([x["ret"] - mean_by[x["day"][:6]] for x in sel])
        print(f"    {nm:14s} {len(sel):5d}철 · 다음 실적 전 목표가에 닿음 {np.mean([x['reach'] for x in sel]) * 100:4.1f}% · "
              f"철 수익 {np.mean(r) * 100:+5.1f}%(같은 달 시작 평균 대비 {np.mean(exr) * 100:+5.1f}) · 이김 {np.mean(r > 0) * 100:4.1f}%", flush=True)

print("\n[C2] 철 안의 때(이른 0~30% · 중간 · 늦은 70~100%)마다 그날 여유(그날 가운데 목표가 ÷ 주가 − 1)별 앞으로 20거래일 수익(같은 달 평균 대비)", flush=True)
pts = []
for x in cyc:
    v, i, j = x["v"], x["i"], x["j"]
    for k in range(i, j, 5):
        if k + 21 >= len(v["c"]):
            break
        t = consensus(v, v["days"][k])
        if t is None:
            continue
        ph = (k - i) / max(1, j - i)
        pts.append((v["days"][k], "이른" if ph < 0.3 else "중간" if ph < 0.7 else "늦은", t / v["c"][k] - 1,
                    v["c"][k + 21] / v["c"][k + 1] - 1))
m20 = defaultdict(list)
for d, _, _, f in pts:
    m20[d[:6]].append(f)
m20 = {k: float(np.mean(v)) for k, v in m20.items()}
for side, test in (("앞", lambda d: d < MID), ("뒤", lambda d: d >= MID)):
    for ph in ("이른", "중간", "늦은"):
        line = []
        for lo, hi, nm in TIERS:
            sel = [f - m20[d[:6]] for d, p, g, f in pts if test(d) and p == ph and lo <= g < hi]
            line.append(f"{nm} {np.mean(sel) * 100:+5.2f}({len(sel)})" if len(sel) >= 30 else f"{nm} -")
        print(f"  {side} {ph}: " + " | ".join(line), flush=True)

# ── [D] 실적 뒤 목표가 고침 ──
print("\n[D] 실적 접수 40일 앞 → 20일 뒤 가운데 목표가 바뀜과 그 뒤(접수 20일 뒤 다음 날 종가부터) 20 · 60거래일 수익", flush=True)
ev = []
for code, v in DATA.items():
    for f in v["f"]:
        a_ = consensus(v, S(D(f) - timedelta(days=40)))
        b_ = consensus(v, S(D(f) + timedelta(days=20)))
        i = px_idx(v, S(D(f) + timedelta(days=20)))
        if not a_ or not b_ or i + 61 >= len(v["c"]):
            continue
        pre = v["c"][i - 1] / v["c"][max(0, bisect.bisect_left(v["days"], S(D(f) - timedelta(days=40))))] - 1
        ev.append((v["days"][i], b_ / a_ - 1, v["c"][i + 20] / v["c"][i] - 1, v["c"][i + 60] / v["c"][i] - 1, pre))
mm = defaultdict(lambda: [[], []])
for d, _, r20, r60, _ in ev:
    mm[d[:6]][0].append(r20)
    mm[d[:6]][1].append(r60)
mm = {k: (np.mean(a), np.mean(b)) for k, (a, b) in mm.items()}
for side, test in (("앞", lambda d: d < MID), ("뒤", lambda d: d >= MID)):
    for lo, hi, nm in ((-9, -0.1, "10%↑ 내림"), (-0.1, -0.02, "2~10% 내림"), (-0.02, 0.02, "그대로"), (0.02, 0.1, "2~10% 올림"), (0.1, 9, "10%↑ 올림")):
        sel = [(r20 - mm[d[:6]][0], r60 - mm[d[:6]][1], pre) for d, ch, r20, r60, pre in ev if test(d) and lo <= ch < hi]
        if len(sel) < 20:
            continue
        a = np.array(sel)
        print(f"  {side} {nm:10s} {len(sel):5d}번 · 20일 {np.mean(a[:, 0]) * 100:+5.2f} · 60일 {np.mean(a[:, 1]) * 100:+5.2f} · "
              f"(그 사이 이미 오른 몫 {np.mean(a[:, 2]) * 100:+5.1f}%)", flush=True)
print("끝", flush=True)
