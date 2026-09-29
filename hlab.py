"""1시간봉 RL 도구 — 자료 읽기 · 그날 종목 모음 · 앞날 손익(다음 봉 시가에 삼) · 사건 연구 · 미래 참조 가드.

미래 참조 막기(docs/RL-1H-PLAN.md):
- 신호는 봉이 닫힌 뒤 그 봉까지의 값으로만 셈 → **다음 봉 시가**에 사고, k봉 뒤 종가에 판다고 봄.
- 그날 종목 모음은 **전 거래일** 시총 순위로 정함(오늘 오른 종목만 고르지 않게).
- 일봉 재료(수급 등)는 전날 것까지만.
"""
import bisect
from pathlib import Path

import numpy as np

import rna

HOME = Path("hourly-data")
COST = 0.30          # 왕복 비용 %(수수료 · 세금 · 미끄러짐을 넉넉히)
EARLY = ("2023100100", "2025040100")   # 앞 반
LATE = ("2025040100", "2026093000")    # 뒤 반(2026-09-30 뒤는 쓰지 않는 시험지)


def load(codes=None):
    """{code: {'t': [YYYYMMDDHH], 'o','h','l','c','v': np.array}} — 시각 순."""
    found = {}
    for folder in sorted(HOME.iterdir()):
        if not folder.is_dir() or (codes and folder.name not in codes):
            continue
        lines = []
        for f in sorted(folder.glob("*.csv")):
            lines += [ln.split(",") for ln in f.read_text(encoding="utf-8").splitlines() if ln.count(",") == 5]
        # 15시 봉은 가장 최근 날에만 따로 있어(옛날은 14시 봉에 합쳐짐) 모양을 맞추려 뺌
        lines = [p for p in lines if p[0][8:] != "15"]
        # 하루에 봉이 하나뿐인 날이 많은 종목은 야후가 1시간봉을 안 주는 종목(그 봉에 하루 전체 값이 들어 있어 쓰면 안 됨)
        per_day = {}
        for p in lines:
            per_day[p[0][:8]] = per_day.get(p[0][:8], 0) + 1
        if not per_day or sum(1 for n in per_day.values() if n <= 1) > 0.2 * len(per_day):
            continue
        lines = [p for p in lines if per_day[p[0][:8]] >= 4]
        if len(lines) < 200:
            continue
        lines.sort(key=lambda p: p[0])
        arr = np.array([[float(x) for x in p[1:]] for p in lines])
        found[folder.name] = {"t": [p[0] for p in lines], "o": arr[:, 0], "h": arr[:, 1], "l": arr[:, 2],
                              "c": arr[:, 3], "v": arr[:, 4]}
    return found


def daily_tables(since="20230101"):
    """일봉 표에서 ({날: {code: 시총 순위}}, {(code, 날): 추세 규칙 문을 지났나}) — 모두 **그날 종가 기준** 값.
    1시간봉에 붙일 때는 반드시 전 거래일 값을 씀(prev_day)."""
    import caps
    import lab
    import rule
    rows = lab.load()
    caps.tag(rows, 150)
    rule.calm_edge(rows)            # nrl과 같은 '조용함' 문턱(전체 표로 한 번)
    ranks, trend = {}, {}
    for r in rows:
        if r["date"] >= since and r.get(caps.RANK):
            ranks.setdefault(r["date"], {})[r["code"]] = r[caps.RANK]
            if r[caps.RANK] <= rule.TOP and rule.trend_leg(r):
                trend[(r["code"], r["date"])] = True
    return ranks, trend


def cached_tables(since="20220101"):
    """daily_tables를 한 번만 굽고 .cache/에 둠. 일봉 표(study/features.json, 4GB)를 읽는 데 2분 반 · 메모리 13GB가
    들어 여러 회차를 동시에 못 돌렸음. 표 파일의 크기 · 고친 시각이 같으면 저장본을 씀(몇 초 · 1GB 안)."""
    import os
    import pickle
    import lab
    src = Path(lab.CACHE)
    st = os.stat(src)
    key = (st.st_size, int(st.st_mtime), since)
    path = Path(".cache") / "hourly_tables.pkl"
    if path.exists():
        try:
            saved = pickle.loads(path.read_bytes())
            if saved.get("key") == key:
                return saved["ranks"], saved["trend"]
        except Exception:
            pass
    ranks, trend = daily_tables(since)
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(pickle.dumps({"key": key, "ranks": ranks, "trend": trend}))
    tmp.replace(path)
    return ranks, trend


def ranks_by_day():
    """{YYYYMMDD: {code: 시총 순위}} — 일봉 표에서. 오늘 모음에는 **전 거래일** 순위를 씀."""
    return daily_tables("20230801")[0]


def prev_day(days, stamp):
    """정렬된 일봉 날 목록에서 stamp(YYYYMMDD…)보다 앞선 마지막 날. 없으면 None."""
    k = bisect.bisect_left(days, stamp[:8]) - 1
    return days[k] if k >= 0 else None


def daily_context(codes, ranks, trend, since="20220101"):
    """종목마다 {날: 재료} — 그날 **종가까지** 아는 일봉 재료. 1시간봉에는 prev_day로 전 거래일 것을 붙임.
    재료: 정배열(3>15>20>90>150>200일 단순평균) · 간격(3일선÷200일선−1, %) · 50>200 · 시장 폭(그날 100위 안 50>200 몫)
    · 추세 문 · 수급 5일 합(외국인 · 투신 · 기관 · 연기금 · 사모 · 개인) · 가르침(외국인+ · 투신+ · 개인−) · 3일 연속(외국인 · 투신 둘 다 +)
    · 자사주 · 희석 공시(접수일이 그날까지인 것, 20거래일 안)."""
    import json
    import final_group
    ctx, fifty = {}, {}
    for code in codes:
        p = Path(f"price-data/{code}.json")
        if not p.exists():
            continue
        rows = [x for x in json.loads(p.read_text(encoding="utf-8"))["closes"] if x[0] >= "20210101"]
        if len(rows) < 260:
            continue
        d = [x[0] for x in rows]
        c = np.array([x[1] for x in rows], float)
        cs = np.r_[0.0, np.cumsum(c)]
        sma = lambda n, i: (cs[i + 1] - cs[i + 1 - n]) / n
        fl = {x["date"]: x for x in final_group.flow_rows(code)}
        fdays = sorted(fl)
        ev = _events(code)
        one = {}
        for i in range(200, len(c)):
            day = d[i]
            if day < since:
                continue
            m = {n: sma(n, i) for n in (3, 15, 20, 50, 90, 150, 200)}
            k = bisect.bisect_right(fdays, day)
            last5 = [fl[x] for x in fdays[max(0, k - 5):k]]
            s5 = {col: (sum((x.get(col) or 0.0) for x in last5) if len(last5) == 5 else None)
                  for col in ("외국인", "투신", "기관", "연기금", "사모", "개인")}
            last3 = [fl[x] for x in fdays[max(0, k - 3):k]]
            one[day] = {
                "정배열": m[3] > m[15] > m[20] > m[90] > m[150] > m[200],
                "간격": (m[3] / m[200] - 1) * 100,
                "추세문": bool(trend.get((code, day))),
                "수급5": s5,
                "가르침": None not in (s5["외국인"], s5["투신"], s5["개인"]) and s5["외국인"] > 0 and s5["투신"] > 0 and s5["개인"] < 0,
                "3일연속": len(last3) == 3 and all((x.get("외국인") or 0) > 0 and (x.get("투신") or 0) > 0 for x in last3),
                "자사주20": _had(ev, ("자기주식취득", "자기주식신탁체결"), d, i, 20),
                "희석20": _had(ev, ("유상증자", "전환사채", "신주인수권부사채", "교환사채"), d, i, 20),
            }
            fifty.setdefault(day, {})[code] = m[50] > m[200]
        ctx[code] = one
    # 시장 폭: 그날 100위 안 종목 가운데 50일선 > 200일선 몫(%)
    breadth = {}
    for day, got in fifty.items():
        top = ranks.get(day, {})
        vals = [v for code, v in got.items() if top.get(code, 999) <= 100]
        if len(vals) >= 30:
            breadth[day] = sum(vals) / len(vals) * 100
    for one in ctx.values():
        for day, f in one.items():
            f["시장폭"] = breadth.get(day)
    return ctx


def _events(code):
    import json
    p = Path(f"dart-events/{code}.json")
    if not p.exists():
        return {}
    got = json.loads(p.read_text(encoding="utf-8")).get("rows") or {}
    return {k: sorted(str(x.get("rcept_no", ""))[:8] for x in v if x.get("rcept_no")) for k, v in got.items()}


def _had(ev, kinds, days, i, n):
    """접수일이 days[i](그날)까지이고 n거래일 안인 공시가 있었나. 1시간봉엔 전 거래일 값으로 붙으므로 접수 다음 날부터 씀."""
    lo = days[max(0, i - n)]
    return any(lo < x <= days[i] for k in kinds for x in ev.get(k, ()))


def attach(b, one, days):
    """1시간봉 b의 봉마다 전 거래일 일봉 재료(dict 또는 None) 목록."""
    out, memo = [], {}
    for t in b["t"]:
        day = t[:8]
        if day not in memo:
            pd = prev_day(days, day)
            memo[day] = one.get(pd) if pd else None
        out.append(memo[day])
    return out


class Universe:
    """in(code, t): t시 봉의 날 기준 전 거래일 시총 순위가 top 안인가."""

    def __init__(self, ranks, top=100):
        self.days = sorted(ranks)
        self.ranks = ranks
        self.top = top

    def ok(self, code, stamp):
        k = bisect.bisect_left(self.days, stamp[:8]) - 1      # 오늘보다 앞선 마지막 거래일
        if k < 0:
            return False
        r = self.ranks[self.days[k]].get(code)
        return r is not None and r <= self.top


def forward(b, i, k, cost=COST):
    """i봉에서 신호 → i+1봉 시가에 사서 i+k봉 종가에 팜(%, 비용 뺌). 자료가 모자라면 None."""
    if i + k >= len(b["c"]) or i + 1 >= len(b["o"]):
        return None
    return (b["c"][i + k] / b["o"][i + 1] - 1) * 100 - cost


def edges(mask):
    """거짓 → 참으로 바뀐 봉만(겹치는 신호를 한 번으로)."""
    m = np.asarray(mask, bool)
    return np.flatnonzero(m & ~np.r_[False, m[:-1]])


def study(data, signal, uni, ks=(1, 3, 7, 14, 35), edge=True, periods=(("앞", EARLY), ("뒤", LATE))):
    """signal(code, b, st) → 봉마다 참/거짓 배열. 기간마다 k봉 앞날 손익의 평균 · 가운데 · 이긴 몫 · 건수."""
    out = {}
    for name, (lo, hi) in periods:
        got = {k: [] for k in ks}
        for code, b in data.items():
            if code.startswith("K"):          # 지수 폴더(KOSPI · KOSDAQ)는 종목이 아님
                continue
            mask = signal(code, b)
            idx = edges(mask) if edge else np.flatnonzero(mask)
            for i in idx:
                t = b["t"][i]
                if not (lo <= t < hi) or not uni.ok(code, t):
                    continue
                for k in ks:
                    f = forward(b, i, k)
                    if f is not None:
                        got[k].append(f)
        out[name] = {k: (len(v), float(np.mean(v)) if v else None, float(np.median(v)) if v else None,
                         float(np.mean(np.asarray(v) > 0) * 100) if v else None) for k, v in got.items()}
    return out


def show(tag, res, ks=(1, 3, 7, 14, 35)):
    parts = [f"  {tag:34s}"]
    for name, by in res.items():
        n = by[ks[0]][0]
        cells = " ".join(f"{k}봉 {by[k][1]:+.2f}({by[k][3]:.0f}%)" if by[k][1] is not None else f"{k}봉 -" for k in ks)
        parts.append(f"{name} {n:>6}건 {cells}")
    print(" | ".join(parts), flush=True)


_ST = {}


def states(code, b, spans_key="A"):
    key = (code, spans_key)
    if key not in _ST:
        _ST[key] = rna.states(b["c"], rna.SETS[spans_key])
    return _ST[key]


def guard_prefix(b, spans_key="A", cuts=(300, 900, 1500)):
    """앞부분만 넣고 센 RNA 값이 전체로 센 값의 같은 봉과 같은가(뒤 봉이 앞 값을 바꾸면 미래 참조)."""
    full = rna.states(b["c"], rna.SETS[spans_key])
    for n in cuts:
        if n >= len(b["c"]):
            continue
        part = rna.states(b["c"][:n], rna.SETS[spans_key])
        for name, arr in part.items():
            a, z = arr[n - 1], full[name][n - 1]
            if not ((np.isnan(a) and np.isnan(z)) or abs(a - z) < 1e-9):
                return f"{name} {n}봉째 {a} ≠ {z}"
    return None


# ───────────────────────── 봉 단위 계좌 모의 ─────────────────────────
# 미래 참조 막기: 봉 t가 닫힌 뒤 정한 사고팔기는 **그 종목의 다음 봉 시가**에 체결. 장중 손절만 봉 저가로(시가가 이미 아래면 시가).
# 같은 봉에서 손절선과 익절선에 둘 다 닿으면 손절이 먼저(나쁜 쪽). 비용은 팔 때 왕복 0.30%를 한 번에 뺌.

def simulate(data, entry, exit_rule, size, periods=(("앞", EARLY), ("뒤", LATE)), slots=10, seeds=8,
             stop_of=None, rank=None, cost=COST, take_of=None):
    """entry(code, b) → 봉마다 '이 봉이 닫히면 산다' 참/거짓 · exit_rule(code, b, pos, i) → 이 봉이 닫히면 팔 칸 수(0 = 안 팜, 'all')
    · size(code, b, i) → 칸 수 · stop_of(pos) → 장중 손절 값(없으면 None) · rank(code, b, i) → 작을수록 먼저.
    씨앗마다 같은 시각의 후보 순서를 조금씩 흔들어 가운데 값을 냄."""
    sigs = {c: np.asarray(entry(c, b), bool) for c, b in data.items() if not c.startswith("K")}
    out = {}
    for name, (lo, hi) in periods:
        runs = [_one_run(data, sigs, exit_rule, size, lo, hi, slots, s, stop_of, rank, cost, take_of) for s in range(seeds)]
        runs = [r for r in runs if r]
        if not runs:
            out[name] = None
            continue
        mid = lambda k: float(np.median([r[k] for r in runs]))
        spread = lambda k: float(np.max([r[k] for r in runs]) - np.min([r[k] for r in runs]))
        base = runs[0]
        out[name] = {"매매": int(mid("매매")), "연": round(mid("연"), 2), "폭": round(spread("연"), 2), "골": round(mid("골"), 1),
                     "회전": round(mid("회전"), 1),
                     "가동": round(mid("가동"), 1), "승률": round(mid("승률"), 1), "보유봉": round(mid("보유봉"), 1),
                     "단순": base["단순"], "행운뺌": base["행운뺌"], "큰2건뺌": base["큰2건뺌"], "반기": base["반기"],
                     "곡선": base["곡선"],
                     "목록": base["목록"]}
    return out


def _one_run(data, sigs, exit_rule, size, lo, hi, slots, seed, stop_of, rank, cost, take_of=None):
    rng = np.random.default_rng(seed)
    idx = {}          # code → (시각 → 봉 번호)
    times = set()
    for c in sigs:
        t = data[c]["t"]
        k0 = bisect.bisect_left(t, lo)
        k1 = bisect.bisect_left(t, hi)
        idx[c] = (k0, k1)
        times.update(t[k0:k1])
    times = sorted(times)
    if not times:
        return None
    at = {}           # 시각 → [(code, 봉 번호)]
    for c, (k0, k1) in idx.items():
        t = data[c]["t"]
        for k in range(k0, k1):
            at.setdefault(t[k], []).append((c, k))
    pos = {}          # code → dict(entry 봉, price, 칸, peak, 조각들)
    want_buy, want_sell, want_add = {}, {}, {}     # code → (다음 봉에 할 일)
    last_day, day_end, day_names = None, [], []
    bought_slots = [0]
    ledger, used_sum, n_bars = [], 0.0, 0
    for T in times:
        bars = at[T]
        # ① 다음 봉 시가에 팔기
        for c, k in bars:
            if c in want_sell and c in pos:
                n = want_sell.pop(c)
                _sell(data[c], pos, c, k, data[c]["o"][k], n, slots, ledger, cost, T)
        # ①' 다음 봉 시가에 더 사기(불타기) — 평균 단가로 합침
        for c, k in bars:
            if c in want_add and c in pos:
                n = want_add.pop(c)
                free = slots - sum(p["칸"] for p in pos.values())
                add = min(n, free)
                if add > 0:
                    p = pos[c]
                    o = data[c]["o"][k]
                    p["price"] = (p["price"] * p["칸"] + o * add) / (p["칸"] + add)
                    p["칸"] += add
                    p["처음칸"] += add
                    p["더함"] = p.get("더함", 0) + add
                    bought_slots[0] += add
            want_add.pop(c, None)
        # ② 다음 봉 시가에 사기(칸이 남은 만큼, 순서 흔들기)
        buys = [(c, k) for c, k in bars if c in want_buy and c not in pos]
        if rank:
            buys.sort(key=lambda ck: (rank(ck[0], data[ck[0]], ck[1] - 1), rng.random()))
        else:
            rng.shuffle(buys)
        for c, k in buys:
            need = want_buy.pop(c)
            free = slots - sum(p["칸"] for p in pos.values())
            if free <= 0:
                continue
            take = min(need, free)
            pos[c] = {"i": k, "price": data[c]["o"][k], "칸": take, "처음칸": take, "peak": data[c]["o"][k],
                      "now": k, "day": T[:8], "code": c}
            bought_slots[0] += take
        for c, _ in bars:              # 이 봉에서 못 산 신호는 버림(일봉 규칙처럼 그날 한 번)
            want_buy.pop(c, None)
        # ③ 장중 손절(봉 저가) → 그 값에(시가가 이미 아래면 시가) · 장중 지정가 익절(봉 고가) → 그 값에(시가가 이미 위면 시가)
        #    같은 봉에서 둘 다 닿으면 손절이 먼저(나쁜 쪽). 산 봉에서도 봄(산 값 = 그 봉 시가).
        for c, k in bars:
            p = pos.get(c)
            if not p:
                continue
            b = data[c]
            p["now"] = k
            if stop_of:
                s = stop_of(p)
                if s is not None and b["l"][k] <= s:
                    _sell(b, pos, c, k, min(b["o"][k], s), "all", slots, ledger, cost, T)
                    continue
            if take_of:
                tp, n = take_of(p)
                if tp is not None and b["h"][k] >= tp:
                    _sell(b, pos, c, k, max(b["o"][k], tp), n, slots, ledger, cost, T)
                    if c not in pos:
                        continue
            p["peak"] = max(p["peak"], b["c"][k])
        # ④ 봉이 닫힌 뒤: 팔 것 · 살 것을 정함(다음 봉 시가에)
        for c, k in bars:
            b = data[c]
            p = pos.get(c)
            if p:
                n = exit_rule(c, b, p, k)
                if isinstance(n, tuple) and n and n[0] == "add":
                    want_add[c] = n[1]
                elif n:
                    want_sell[c] = n
            elif sigs[c][k] and k + 1 < len(b["t"]):
                want_buy[c] = size(c, b, k)
        used_sum += sum(p["칸"] for p in pos.values()) / slots
        n_bars += 1
        # 하루 끝 평가(마지막 봉 종가로)
        if last_day and T[:8] != last_day:
            day_end.append(_mark(data, pos, ledger, slots))
            day_names.append(last_day)
        last_day = T[:8]
    day_end.append(_mark(data, pos, ledger, slots))
    day_names.append(last_day)
    for c in list(pos):
        b = data[c]
        _sell(b, pos, c, pos[c]["now"], b["c"][pos[c]["now"]], "all", slots, ledger, cost, "끝")
    if len(ledger) < 10:
        return None
    eq = np.array(day_end)
    years = max(len(eq) / 245, 0.25)
    total = eq[-1]
    peak = np.maximum.accumulate(eq)
    w = sorted(t["손익"] * t["칸"] for t in ledger)
    halves = {}
    for t in ledger:
        h = t["판 때"][:4] + ("상" if t["판 때"][4:6] <= "06" else "하")
        halves[h] = round(halves.get(h, 0) + t["손익"] * t["칸"] / slots, 1)
    # 연 = 복리 없이 더한 한 해 몫(칸 크기를 처음 자금 기준으로 고정했으므로) · 골 = 계좌 꼭대기 대비 가장 깊이 빠진 %(일봉 RL과 같은 뜻)
    return {"매매": len(ledger), "연": (total - 1) / years * 100, "골": float(((eq / peak) - 1).min() * 100),
            "회전": bought_slots[0] / slots / years,
            "곡선": dict(zip(day_names, (float(x) for x in eq))),
            "가동": used_sum / max(n_bars, 1) * 100, "승률": float(np.mean([t["손익"] > 0 for t in ledger]) * 100),
            "보유봉": float(np.median([t["봉"] for t in ledger])),
            "단순": round(sum(w) / slots / years, 2),
            "행운뺌": round(sum(min(t["손익"], 30) * t["칸"] for t in ledger) / slots / years, 2),
            "큰2건뺌": round(sum(w[:-2]) / slots / years, 2), "반기": halves, "목록": ledger}


def _mark(data, pos, ledger, slots):
    """하루 끝 계좌 값(1 = 처음). 실현 손익 + 들고 있는 것의 평가 손익."""
    v = 1.0 + sum(t["손익"] / 100 * t["칸"] / slots for t in ledger)
    for c, p in pos.items():
        b = data[c]
        v += (b["c"][p["now"]] / p["price"] - 1) * p["칸"] / slots
    return v


def _sell(b, pos, c, k, price, n, slots, ledger, cost, when):
    p = pos[c]
    part = p["칸"] if n == "all" or n >= p["칸"] else int(n)
    gain = (price / p["price"] - 1) * 100 - cost
    ledger.append({"code": c, "산 때": b["t"][p["i"]], "판 때": b["t"][k] if when != "끝" else "끝" + b["t"][k],
                   "봉": k - p["i"], "칸": part, "손익": round(gain, 2), "나눠": part < p["칸"]})
    p["칸"] -= part
    if p["칸"] <= 0:
        del pos[c]


def line(res):
    parts = []
    for name, r in res.items():
        if not r:
            parts.append(f"{name} -")
            continue
        parts.append(f"{name} 매매 {r['매매']:>4} 연 {r['연']:>6}({r['폭']}) 골 {r['골']:>6} 가동 {r['가동']:>5} 회전 {r.get('회전', '-')}배 승률 {r['승률']:>4} "
                     f"보유 {r['보유봉']}봉 단순 {r['단순']} 행운뺌 {r['행운뺌']} 큰2건뺌 {r['큰2건뺌']}")
    return " | ".join(parts)


def blend(parts):
    """[(비중, simulate 결과의 한 반)] → 두 자금을 날마다 합친 계좌(씨앗 0 곡선). 연 = 복리 없는 한 해 몫 · 골 = 꼭대기 대비 %."""
    days = sorted(set().union(*[set(r["곡선"]) for _, r in parts]))
    last = [1.0] * len(parts)
    eq = []
    for d in days:
        for j, (_, r) in enumerate(parts):
            if d in r["곡선"]:
                last[j] = r["곡선"][d]
        eq.append(sum(w * v for (w, _), v in zip(parts, last)))
    eq = np.array(eq)
    years = max(len(eq) / 245, 0.25)
    peak = np.maximum.accumulate(eq)
    return {"연": round((eq[-1] - 1) / years * 100, 2), "골": round(float(((eq / peak) - 1).min() * 100), 1)}
