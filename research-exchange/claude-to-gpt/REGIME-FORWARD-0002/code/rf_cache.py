"""REGIME-FORWARD-0002 · D1 캐시(nrl-cache) 복구 — 저장소 자료만 · 같은 공식 · 10월 자료 안 읽음.
python3 -E -P rf_cache.py <b2(00b98ab1)> <옛 nrl-cache.pkl(84030fcf…)> <출력 폴더>

- 다시 만들기(R): lab.build를 지금 저장소 가격(2026-09-30까지 자름)으로 종목 20개씩 돌림. horizons=(0,5,10,20,60)로 한 번 만들고
  · 2026-09-16(옛 캐시 마지막 날) 이하: 원 공식(horizons 5·10·20·60)의 '줄 있음' 조건(i+5 < 길이 = ahead에 5가 있음)만 남김 → 옛 표와 같은 조건
  · 2026-09-17 이후: 매일 운영 계산(final_group.compute)과 research/x003.py가 쓰는 horizons=(0,) 조건(그날까지 가격만 있으면 줄 있음)
  · 'ahead'(앞날 수익 · 판단에 안 씀)는 모든 줄에서 지움 → 판단 코드가 읽으면 KeyError로 멈춤
  · caps.tag(그날 시총 순위)는 날마다 그날 줄끼리만 · realign은 아래 H 가격 기준
- 겹침 동일성: R과 옛 캐시(O)를 2025-08-01 ~ 2026-09-16의 상위 100 줄(inside) · 시장 폭(BR) · 달별 조용함 문턱(2026-09) · 가격 · 모양(shape)으로 비교.
- 쓸 캐시(H): 2026-09-16 이하 = 옛 캐시 그대로(PR #68 통제 경로가 본 입력) · 2026-09-17 ~ 09-30 = R의 새 날(줄 · 시장 폭) · 가격은 그 뒤 날만 지금 저장소 값.
  옛 표에 없던 칸(실적 · 목표가 칸)은 새 줄에서 지움(옛 줄과 같은 칸만).
- 소급 수정 종목: 지금 저장소 가격이 옛 캐시와 2026-09-16 이하 모든 겹친 날에서 같은 비율 f로 다르면(10월 뒤 사건의 수정주가가 과거 전체에 입혀진 것)
  9월 값은 그 시점 원래 값으로 되돌림 — 옛 캐시(이전 저장소 시점) 값이 지금 값 ÷ f와 0.01% 안에서 맞으면 옛 값, 없거나 안 맞으면 round(지금 값 ÷ f).
  다시 만들기(R)도 이 되돌린 가격(P′)으로 함.
네트워크 막음 · 키 환경변수 지움 · 운영 파일 안 고침 · features.json 안 씀."""
import bisect
import hashlib
import json
import os
import pickle
import socket
import sys
import time
from collections import Counter
from pathlib import Path

BASE, OLD, OUT = str(Path(sys.argv[1]).resolve()), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
CUT, OLD_LAST, CMP_FROM = "20260930", "20260916", "20250801"
OUT.mkdir(parents=True, exist_ok=True)


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
        os.environ.pop(k)
os.environ.pop("CAPS_ADJ", None)
os.chdir(BASE)
sys.path[:0] = [BASE, BASE + "/research"]
t0 = time.time()
import caps  # noqa: E402
import final_study as F  # noqa: E402
import lab  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402

O = pickle.load(open(OLD, "rb"))
o_prices, o_lanes, o_shape, o_BR, o_inside, o_calm, o_CM = O
print("옛 캐시", len(o_prices), "종목 · inside", len(o_inside), "· 마지막", max(r["date"] for r in o_inside), flush=True)
assert max(r["date"] for r in o_inside) == OLD_LAST
OLD_KEYS = set().union(*(set(r) for r in o_inside[:5000])) - {"ahead"}

cur = study.load_prices()
P = {}
for c, b in cur.items():
    rows = [x for x in b["rows"] if x[0] <= CUT]
    if len(rows) >= 120:
        P[c] = {"name": b["name"], "rows": rows}
assert max(x[0] for b in P.values() for x in b["rows"]) <= CUT
import statistics  # noqa: E402
RETRO = {}
for c, b in P.items():
    a = dict((o_prices.get(c) or {}).get("rows", []))
    ov = [(d, v) for d, v in b["rows"] if d <= OLD_LAST and d in a]
    bad = [(d, v) for d, v in ov if a[d] != v]
    if len(bad) >= 100 and len(bad) == len(ov):
        f = statistics.median(v / a[d] for d, v in ov)
        dev = max(abs(v / a[d] / f - 1) for d, v in ov)
        assert dev < 1e-2, (c, f, dev)
        fixed, n_old, n_div = [], 0, 0
        for d, v in b["rows"]:
            if d <= OLD_LAST:
                fixed.append((d, a.get(d, round(v / f))))
                continue
            if d in a and abs(a[d] - v / f) / a[d] < 1e-4:
                fixed.append((d, a[d]))
                n_old += 1
            else:
                fixed.append((d, float(round(v / f))))
                n_div += 1
        RETRO[c] = {"f": f, "max_ratio_dev": dev, "overlap_days": len(ov), "tail_from_old": n_old, "tail_divided": n_div,
                    "tail_values": [x for x in fixed if x[0] > OLD_LAST]}
        P[c] = {"name": b["name"], "rows": fixed}
print("소급 수정 종목", {c: {k: v for k, v in x.items() if k != "tail_values"} for c, x in RETRO.items()}, flush=True)

# ── R: 다시 만들기 ──
vols, keep, codes = [], [], sorted(P)
for s in range(0, len(codes), 20):
    part = {c: P[c] for c in codes[s:s + 20]}
    for r in lab.build(part, horizons=(0, 5, 10, 20, 60)):
        orig = 5 in r["ahead"]
        if orig and r.get("변동성") is not None:
            vols.append((r["date"], r["변동성"]))
        if r["date"] >= CMP_FROM and (r["date"] > OLD_LAST or orig):
            del r["ahead"]
            keep.append(r)
    print("  만듦", min(s + 20, len(codes)), "/", len(codes), round(time.time() - t0), "초", flush=True)
caps.tag(keep, rule.TOP)
r_inside = [r for r in keep if caps.inside(r, rule.TOP)]
del keep


def calm_month(got, key):
    import numpy as np
    got = sorted(got)
    days = [d for d, _ in got]
    vals = np.array([v for _, v in got], dtype=float)
    k = bisect.bisect_left(days, key + "01")
    return float(np.partition(vals[:k], int(k * rule.CALM))[int(k * rule.CALM)])


r_cm = {m: calm_month(vols, m) for m in ("202509", "202510", "202601", "202606", "202608", "202609")}
del vols

# ── H 가격: 옛 캐시 ≤ 09-16 + 지금 저장소 09-17 ~ 09-30 ──
H_prices = {}
for c in sorted(set(o_prices) | set(P)):
    old = [x for x in (o_prices.get(c) or {}).get("rows", []) if x[0] <= OLD_LAST]
    new = [x for x in (P.get(c) or {}).get("rows", []) if OLD_LAST < x[0] <= CUT]
    if old or new:
        H_prices[c] = {"name": (o_prices.get(c) or P.get(c))["name"], "rows": old + new}
r_inside = lab.realign(r_inside, H_prices)

# ── 겹침 비교(2025-08-01 ~ 2026-09-16) ──
cmp = {"range": [CMP_FROM, OLD_LAST]}
oi = {(r["code"], r["date"]): r for r in o_inside if CMP_FROM <= r["date"] <= OLD_LAST}
ri = {(r["code"], r["date"]): r for r in r_inside if r["date"] <= OLD_LAST}
cmp["inside_rows_old_new"] = [len(oi), len(ri)]
cmp["only_old"] = sorted(map(list, set(oi) - set(ri)))[:50]
cmp["only_new"] = sorted(map(list, set(ri) - set(oi)))[:50]
cmp["n_only_old"], cmp["n_only_new"] = len(set(oi) - set(ri)), len(set(ri) - set(oi))
diff_f, diff_keys, diff_codes, extra = Counter(), Counter(), Counter(), Counter()
for k in set(oi) & set(ri):
    a, b = oi[k], ri[k]
    for f in (set(a) | set(b)) - {"ahead"}:
        if f not in a:
            extra[f] += 1
            continue
        if f not in b:
            diff_keys["missing_in_new:" + f] += 1
            continue
        if a[f] != b[f]:
            diff_f[f] += 1
            diff_codes[k[0]] += 1
cmp["field_diffs"] = dict(diff_f)
cmp["field_diff_codes"] = dict(diff_codes)
TGT = {"목표가괴리", "목표가곳수", "영업이익성장", "흑자", "매출성장", "영업이익률"}
dc2 = Counter()
for k in set(oi) & set(ri):
    a, b = oi[k], ri[k]
    for f in (set(a) & set(b)) - {"ahead"} - TGT:
        if a[f] != b[f]:
            dc2[(k[0], f)] += 1
cmp["field_diffs_excluding_target_earnings(code·field: 줄 수)"] = {f"{c}·{f}": n for (c, f), n in sorted(dc2.items())}
cmp["missing_fields_in_new"] = dict(diff_keys)
cmp["extra_fields_in_new(옛 표에 없던 칸 · 판단에 안 씀)"] = dict(extra)
cmp["calm_month_old_new"] = {m: [o_CM.get(m), r_cm[m]] for m in r_cm}
H_lanes = lab.lanes(H_prices)
codes_rows = set(o_shape) | {r["code"] for r in r_inside}
H_shape = F.shapes(H_lanes, codes_rows)
r_BR = F.breadth_by_day(r_inside, H_shape)
cmp["BR_days_compared"] = sum(1 for d in o_BR if CMP_FROM <= d <= OLD_LAST)
cmp["BR_diffs"] = {d: [o_BR.get(d), r_BR.get(d)] for d in sorted(set(o_BR) | set(r_BR))
                   if CMP_FROM <= d <= OLD_LAST and o_BR.get(d) != r_BR.get(d)}
pd_ = Counter()
for c in set(o_prices) | set(P):
    a = dict((o_prices.get(c) or {}).get("rows", []))
    b = dict((P.get(c) or {}).get("rows", []))
    bad = sorted(d for d in set(a) | set(b) if d <= OLD_LAST and a.get(d) != b.get(d))
    if bad:
        pd_[c] = [bad[0], bad[-1], len(bad)]
cmp["price_diffs_le_0916(code: 처음 · 끝 · 개수)"] = dict(pd_)
import numpy as np  # noqa: E402
sh_bad = Counter()
for c in o_shape:
    if c not in H_shape:
        sh_bad[c] = "missing"
        continue
    n = sum(1 for d in o_lanes[c]["날"] if d <= OLD_LAST) if c in o_lanes else 0
    for f in ("정배열", "간격", "50>200", "200"):
        a, b = np.asarray(o_shape[c][f][:n]), np.asarray(H_shape[c][f][:n])
        if not (a.shape == b.shape and np.array_equal(a, b, equal_nan=a.dtype.kind == "f")):
            sh_bad[c] = f
            break
cmp["shape_diffs_le_0916"] = dict(sh_bad)

# ── H 캐시 ──
tail = [r for r in r_inside if r["date"] > OLD_LAST]
for r in tail:
    for f in set(r) - OLD_KEYS:
        del r[f]
H_inside = []
for r in o_inside:
    r = dict(r)
    r.pop("ahead", None)
    H_inside.append(r)
H_inside = lab.realign(H_inside, H_prices)
assert len(H_inside) == len(o_inside), "옛 줄이 H 가격에서 빠짐"
H_inside += tail
H_BR = {d: v for d, v in o_BR.items() if d <= OLD_LAST}
H_BR.update({d: v for d, v in r_BR.items() if d > OLD_LAST})
tail_days = sorted({r["date"] for r in tail})
cal = sorted(d for d, _ in P["005930"]["rows"] if OLD_LAST < d <= CUT)
H = (H_prices, H_lanes, H_shape, H_BR, H_inside, o_calm, o_CM)
path = OUT / "nrl-cache-rf.pkl"
with open(path, "wb") as fh:
    pickle.dump(H, fh, protocol=pickle.HIGHEST_PROTOCOL)
sha = hashlib.sha256(path.read_bytes()).hexdigest()
info = {"compare": cmp, "tail_days": tail_days, "calendar_0917_0930": cal, "tail_days_equal_calendar": tail_days == cal,
        "tail_rows_per_day": dict(Counter(r["date"] for r in tail)), "tail_BR": {d: H_BR.get(d) for d in cal},
        "H_inside": len(H_inside), "H_last": max(r["date"] for r in H_inside),
        "H_max_price_date": max(x[0] for b in H_prices.values() for x in b["rows"]),
        "ahead_left": sum(1 for r in H_inside if "ahead" in r), "retro_adjusted": RETRO, "calm_full_kept": o_calm,
        "calm_month_202609_kept": o_CM.get("202609"), "cache_sha256": sha, "seconds": round(time.time() - t0)}
(OUT / "cache_rebuild.json").write_text(json.dumps(info, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in info.items() if k != "compare"}, ensure_ascii=False, default=str), flush=True)
print("비교", json.dumps({k: (v if not isinstance(v, (list, dict)) or len(v) < 30 else f"{len(v)}개")
                         for k, v in cmp.items()}, ensure_ascii=False, default=str), flush=True)
print("끝", flush=True)
