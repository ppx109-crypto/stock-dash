"""SIG-MAP-0045 — 쉬운 신호 여덟 개가 21해 동안 꾸준했는지 보는 지도(진단 · 규칙 채택 없음 · 사전등록 그대로).
- 대상: investor-full 268종목 가운데 그날 전날까지 20거래일 평균 거래대금 상위 100(brk_build 스냅샷 · 생존 편향 있음).
- 지도 기간 M = 2006-01-02 ~ 2021-12-30: /tmp/sig-m1.pkl(2005-01-03 ~ 2016-12-29 · 2006 ~ 2016 평가) + /tmp/sig-m2.pkl(2016-01-04 ~ 2021-12-30 · 2017 ~ 2021 평가).
  지도 셈은 시험 기간 스냅샷(/tmp/sig-t.pkl)을 읽지 않습니다.
- 잼: t날까지의 값으로 신호를 셈 → t+1 종가에 사서 t+11 종가까지(10거래일) 수익 → 그날 위 20% 평균 − 아래 20% 평균(벌어짐).
  해 값 = 그해 날마다 벌어짐의 평균. 국면 = 스냅샷 안 069500 그날까지 60일 수익(> +5% 오름 · < −5% 내림 · 그 사이 횡보).
- 꾸준함(STABLE) = ① 16해 가운데 12해 이상 + ② 세 국면 평균 모두 + ③ 2006 ~ 2013 · 2014 ~ 2021 평균 모두 +.
- 시험(T = 2022-01-03 ~ 2026-09-15 · /tmp/sig-t.pkl): STABLE 가운데 '두 시대 평균의 작은 쪽'이 가장 큰 신호 하나만 한 번(S5 · S6 수급은 이미 T 값을 봤으므로 고르지 않음).
  통과 = T 평균 > 0 · 5해(2026은 9월까지) 가운데 3해 이상 +.
python3 research/sig_map.py --map            지도만(M)
python3 research/sig_map.py --t              잠금 확인 · 영수증 · 지도 다시 셈 · 고른 신호 하나만 T
python3 research/sig_map.py --cut-test       자르기 시험(/tmp/sig-cut.pkl = 2013-12-30에서 자른 굽기와 날마다 벌어짐 비교)"""
import bisect
import hashlib
import json
import math
import os
import pickle
import random
import sys
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
BOX = ROOT / "research-exchange/claude-to-gpt/SIG-MAP-0045"
M_PARTS = (("/tmp/sig-m1.pkl", "20060102", "20161229"), ("/tmp/sig-m2.pkl", "20170102", "20211230"))
T_PART = ("/tmp/sig-t.pkl", "20220103", "20260915")
CUT_PART = ("/tmp/sig-cut.pkl", "20060102", "20131230")
SIGS = ("S1_MOM20", "S2_REV5", "S3_HIGH120", "S4_LOWVOL60", "S5_FLOW_FT10", "S6_RETAIL_CONTRA10", "S7_EMA_ALIGN", "S8_MOM120_SKIP20")
NO_T = ("S5_FLOW_FT10", "S6_RETAIL_CONTRA10")
HOLD, MINN = 10, 50
LOCK = BOX / "t_lock.json"
RECEIPT = BOX / "t_receipt.json"


def ema_list(xs, n):
    a, out, e = 2 / (n + 1), [], None
    for x in xs:
        e = x if e is None else e + a * (x - e)
        out.append(e)
    return out


def load(path):
    s = pickle.load(open(path, "rb"))
    lanes = {}
    for c, b in s["prices"].items():
        ds = [d for d, _ in b["rows"]]
        xs = [x for _, x in b["rows"]]
        lanes[c] = {"d": ds, "x": xs, "pos": {d: k for k, d in enumerate(ds)},
                    "e": {n: ema_list(xs, n) for n in (5, 20, 60, 120)}}
    ixd = sorted(s["ix"])
    return s, lanes, ixd


def phase(s, ixd, d):
    k = bisect.bisect_right(ixd, d) - 1
    if k < 60:
        return None
    r = s["ix"][ixd[k]] / s["ix"][ixd[k - 60]] - 1
    return "오름" if r > 0.05 else "내림" if r < -0.05 else "횡보"


def flow_val(s, lane, r, col, sign):
    """t날까지 10거래일(수급 날짜 기준) 순매수 수량 × 그날 종가 합 / 전날까지 20일 평균 거래대금."""
    got = s["flow"].get(r["code"])
    if not got:
        return None
    fd, acc, ok = got
    k = bisect.bisect_right(fd, r["date"])
    if k < 10 or ok[k] - ok[k - 10] < 10:
        return None
    tot = 0.0
    for j in range(k - 10, k):
        p = lane["pos"].get(fd[j])
        if p is None:
            return None
        q = sum(acc[c][j + 1] - acc[c][j] for c in col)
        tot += q * lane["x"][p]
    return sign * tot / r["거래대금20"]


def signals(s, lane, r):
    i, x = r["i"], lane["x"]
    out = {}
    if i >= 20:
        out["S1_MOM20"] = x[i] / x[i - 20] - 1
    if i >= 5:
        out["S2_REV5"] = -(x[i] / x[i - 5] - 1)
    if i >= 119:
        out["S3_HIGH120"] = x[i] / max(x[i - 119:i + 1])
    if i >= 60:
        rs = [x[j] / x[j - 1] - 1 for j in range(i - 59, i + 1)]
        m = sum(rs) / 60
        out["S4_LOWVOL60"] = -math.sqrt(sum((v - m) ** 2 for v in rs) / 59)
    f = flow_val(s, lane, r, ("외국인", "투신"), 1)
    if f is not None:
        out["S5_FLOW_FT10"] = f
    p = flow_val(s, lane, r, ("개인",), -1)
    if p is not None:
        out["S6_RETAIL_CONTRA10"] = p
    if i >= 119:
        e = lane["e"]
        out["S7_EMA_ALIGN"] = (e[5][i] > e[20][i]) + (e[20][i] > e[60][i]) + (e[60][i] > e[120][i])
    if i >= 120:
        out["S8_MOM120_SKIP20"] = x[i - 20] / x[i - 120] - 1
    return out


def spreads(part, only=None):
    """{신호: {날: (벌어짐, 국면)}} — 날마다 위 20% − 아래 20%(S7은 3점 무리 − 0점 무리 · 무리마다 5종목 이상)."""
    path, lo, hi = part
    s, lanes, ixd = load(path)
    byd = {}
    for r in s["rows"]:
        if lo <= r["date"] <= hi:
            byd.setdefault(r["date"], []).append(r)
    out = {k: {} for k in (only or SIGS)}
    for d in sorted(byd):
        ph = phase(s, ixd, d)
        if ph is None:
            continue
        got = []
        for r in byd[d]:
            lane = lanes[r["code"]]
            i = r["i"]
            if i + 1 + HOLD >= len(lane["x"]):
                continue
            fwd = lane["x"][i + 1 + HOLD] / lane["x"][i + 1] - 1
            got.append((r["code"], fwd, signals(s, lane, r)))
        for k in out:
            have = [(sg[k], c, f) for c, f, sg in got if k in sg]
            if len(have) < MINN:
                continue
            if k == "S7_EMA_ALIGN":
                top = [f for v, _, f in have if v == 3]
                bot = [f for v, _, f in have if v == 0]
                if len(top) < 5 or len(bot) < 5:
                    continue
            else:
                have.sort(key=lambda z: (-z[0], z[1]))
                q = len(have) // 5
                top = [f for _, _, f in have[:q]]
                bot = [f for _, _, f in have[-q:]]
            out[k][d] = (sum(top) / len(top) - sum(bot) / len(bot), ph)
    return out


def merge(parts, only=None):
    res = {k: {} for k in (only or SIGS)}
    for p in parts:
        got = spreads(p, only)
        for k in res:
            res[k].update(got[k])
    return res


def mean(v):
    return sum(v) / len(v) if v else None


def boot_month(daily, reps=2000, seed=45):
    """달 덩어리 부트스트랩(보고 전용): 달마다 날 벌어짐을 묶어 달을 되뽑아 평균의 95% 구간."""
    months = {}
    for d, (v, _) in sorted(daily.items()):
        months.setdefault(d[:6], []).append(v)
    blocks = list(months.values())
    rnd = random.Random(seed)
    got = []
    for _ in range(reps):
        pick = [blocks[rnd.randrange(len(blocks))] for _ in blocks]
        flat = [x for b in pick for x in b]
        got.append(sum(flat) / len(flat))
    got.sort()
    return [round(got[int(reps * 0.025)] * 100, 3), round(got[int(reps * 0.975)] * 100, 3)]


def summarize(daily, years):
    ys = {y: mean([v for d, (v, _) in daily.items() if d[:4] == y]) for y in years}
    ph = {p: mean([v for v, q in daily.values() if q == p]) for p in ("오름", "횡보", "내림")}
    n = {p: sum(1 for _, q in daily.values() if q == p) for p in ("오름", "횡보", "내림")}
    return ys, ph, n


def map_table(res):
    years = [str(y) for y in range(2006, 2022)]
    table = {}
    for k in SIGS:
        daily = res[k]
        ys, ph, n = summarize(daily, years)
        e1 = mean([v for d, (v, _) in daily.items() if d < "20140101"])
        e2 = mean([v for d, (v, _) in daily.items() if d >= "20140101"])
        pos = sum(1 for v in ys.values() if v is not None and v > 0)
        c1 = pos >= 12
        c2 = all(v is not None and v > 0 for v in ph.values())
        c3 = e1 is not None and e2 is not None and e1 > 0 and e2 > 0
        table[k] = {"days": len(daily), "mean_pct": round(mean([v for v, _ in daily.values()]) * 100, 3),
                    "years_pos": f"{pos}/16", "years_pct": {y: (round(v * 100, 3) if v is not None else None) for y, v in ys.items()},
                    "phase_pct": {p: (round(v * 100, 3) if v is not None else None) for p, v in ph.items()}, "phase_days": n,
                    "era_2006_2013_pct": round(e1 * 100, 3) if e1 is not None else None,
                    "era_2014_2021_pct": round(e2 * 100, 3) if e2 is not None else None,
                    "boot95_report_only": boot_month(daily),
                    "c1_years_ge_12": c1, "c2_all_phases_pos": c2, "c3_both_eras_pos": c3, "STABLE": c1 and c2 and c3}
    cands = [k for k in SIGS if table[k]["STABLE"] and k not in NO_T]
    pick = max(cands, key=lambda k: (min(table[k]["era_2006_2013_pct"], table[k]["era_2014_2021_pct"]), -SIGS.index(k))) if cands else None
    return table, pick


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lock_body():
    return {"research/sig_map.py": sha(__file__), "/tmp/sig-m1.pkl": sha(M_PARTS[0][0]), "/tmp/sig-m2.pkl": sha(M_PARTS[1][0]),
            "/tmp/sig-t.pkl": sha(T_PART[0])}


def run_t():
    want = json.loads(LOCK.read_text())
    have = lock_body()
    if want != have:
        sys.exit("잠금이 다름(멈춤): " + json.dumps({k: (want.get(k), v) for k, v in have.items() if want.get(k) != v}, ensure_ascii=False))
    key = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    table, pick = map_table(merge(M_PARTS))
    import subprocess
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    import time
    body = {"status": "STARTED", "lock_key": key, "git_head": head, "pick": pick, "at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}
    fd = os.open(str(RECEIPT), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as fh:
        fh.write(json.dumps(body, ensure_ascii=False))
        fh.flush()
        os.fsync(fh.fileno())
    out = {"task": "SIG-MAP-0045", "phase": "T", "lock_key": key, "receipt": body, "map": table, "pick": pick}
    if pick is None:
        out["verdict"] = "NO_STABLE_SIGNAL"
        print(json.dumps(out, ensure_ascii=False))
        return
    daily = merge([T_PART], only=(pick,))[pick]
    years = [str(y) for y in range(2022, 2027)]
    ys, ph, n = summarize(daily, years)
    m = mean([v for v, _ in daily.values()])
    pos = sum(1 for v in ys.values() if v is not None and v > 0)
    out["T"] = {"signal": pick, "days": len(daily), "mean_pct": round(m * 100, 3) if m is not None else None, "years_pos": f"{pos}/5",
                "years_pct": {y: (round(v * 100, 3) if v is not None else None) for y, v in ys.items()},
                "phase_pct": {p: (round(v * 100, 3) if v is not None else None) for p, v in ph.items()}, "phase_days": n,
                "boot95_report_only": boot_month(daily) if daily else None}
    out["verdict"] = "STABLE_SIGNAL_CONFIRMED" if m is not None and m > 0 and pos >= 3 else "STABLE_IN_MAP_ONLY"
    print(json.dumps(out, ensure_ascii=False))


def cut_test():
    """같은 2006 ~ 2013 평가를 '온 굽기(sig-m1)'와 '2013-12-30에서 자른 굽기(sig-cut)'로 셈.
    자른 굽기에서 셀 수 있는 날(앞 10거래일 뒤 값이 자른 날 안)의 벌어짐이 모두 같아야 함."""
    a = merge([(M_PARTS[0][0], "20060102", "20131230")])
    b = merge([CUT_PART])
    bad, n = [], 0
    for k in SIGS:
        for d, v in b[k].items():
            n += 1
            if d not in a[k] or a[k][d] != v:
                bad.append((k, d, v, a[k].get(d)))
    lost = {k: len(set(a[k]) - set(b[k])) for k in SIGS}
    print(json.dumps({"compared": n, "differ": len(bad), "first_bad": bad[:5], "only_in_full_days(끝 쪽 앞날 값 없음)": lost,
                      "last_cut_day": {k: max(b[k]) if b[k] else None for k in SIGS}}, ensure_ascii=False))


def main():
    if "--t" in sys.argv:
        return run_t()
    if "--cut-test" in sys.argv:
        return cut_test()
    if "--lock" in sys.argv:
        LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1))
        print(LOCK.read_text())
        return
    table, pick = map_table(merge(M_PARTS))
    print(json.dumps({"task": "SIG-MAP-0045", "phase": "M", "map": table, "pick_for_T": pick}, ensure_ascii=False))


if __name__ == "__main__":
    main()
