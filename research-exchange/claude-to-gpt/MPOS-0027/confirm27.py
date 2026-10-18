"""MPOS-0027 사후 확인용 재현 — 대조 · 사건 기록(PREREG 2판 1 ~ 3절 · 손익 요약 없음).
EX_MODE=PRE  : 실행 전 점검(캐시 경로 · 옛 전역 없음 · trend_leg가 그 판 T를 씀 · FLOW 종목 · 000500 양성 · 합성 음성 · 목표가 감싸기 동일성).
EX_MODE=LED  : 장부 + 사건(매수 사건 · 후보 · 종료 매매 · 끝 열린 보유). 바꿀 수 있는 것:
               EX_FCUT=c · EX_FMODE=drop|poison(c 뒤 수급 · 의견 원자료를 읽는 순간 지우거나 엉터리로) · EX_DPOISON=d(그날 모든 수급 줄 외국인 = −1e13)
               EX_MUT=none|lag0|lead1(돌연변이 teacher: 당일 수급 · 다음 날 수급을 읽음).
EX_MODE=SIG  : 당일 가용성 신호 단위 대조(PREREG 2-B · 8날).
EX_MODE=CMP  : 사건 파일 둘(EX_A · EX_B)을 c(EX_CUT)까지 비교.
원자료 → 파서 → 전역: final_group.flow_rows(investor-data) · study.target_timeline(opinion-data)을 nrl import **전에** 바꿔 끼워, nrl이 새 프로세스에서 FLOW · TARGETS를 다시 만듦.
cwd = 고정 나무 · tree_run. NRL_CACHE = 그 판 정직 캐시 · EX_FULL = 그 판 build pkl(T). 출력 EX_OUT."""
import bisect
import hashlib
import json
import os
import pickle
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
HC = os.environ["EX_HC"]
assert "nrl" not in sys.modules
import final_group  # noqa: E402
import study  # noqa: E402

MODE, OUT = os.environ["EX_MODE"], os.environ["EX_OUT"]
FCUT, FMODE, DPOISON = os.environ.get("EX_FCUT"), os.environ.get("EX_FMODE", "drop"), os.environ.get("EX_DPOISON")
MUT = os.environ.get("EX_MUT", "none")
FLOW_COLS = ("개인", "외국인", "기관", "투신", "연기금", "사모")


def junk(code, day, col):
    h = int(hashlib.sha256(f"{code}|{day}|{col}".encode()).hexdigest()[:8], 16)
    return (1 if h % 2 else -1) * 1e12


_fr = final_group.flow_rows


def flow_rows(code, folder=final_group.FLOWS):
    rows = _fr(code, folder)
    if FCUT:
        if FMODE == "drop":
            rows = [x for x in rows if str(x.get("date", "")) <= FCUT]
        else:
            rows = [dict(x, **{c: junk(code, x["date"], c) for c in FLOW_COLS}) if str(x.get("date", "")) > FCUT else x for x in rows]
    if DPOISON:
        rows = [dict(x, 외국인=-1e13) if str(x.get("date", "")) == DPOISON else x for x in rows]
    return rows


_tt = study.target_timeline


def target_timeline(code, folder="opinion-data", months=3):
    """study.target_timeline 본문과 같은 셈 · 원자료 줄만 자르기 · 바꾸기(PRE에서 바꾸지 않은 판이 원 함수와 같은지 모든 종목 대조)."""
    try:
        source = json.loads((Path(folder) / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    raw = source.get("rows") or []
    if FCUT:
        if FMODE == "drop":
            raw = [r for r in raw if str(r.get("date", "")) <= FCUT]
        else:
            raw = [dict(r, target=(r.get("target") or 0) * (0.01 if junk(code, r.get("date"), "t") > 0 else 100)) if str(r.get("date", "")) > FCUT else r
                   for r in raw]
    rows = sorted((r for r in raw if str(r.get("date", "")).isdigit() and (r.get("target") or 0) > 0), key=lambda r: r["date"])
    if not rows:
        return []
    found, seen = [], {}
    for row in rows:
        seen[row.get("member") or row["date"]] = row
        edge = study._months_before(row["date"], months)
        live = [r for r in seen.values() if r["date"] >= edge]
        if not live:
            continue
        prices = sorted(r["target"] for r in live)
        middle = len(prices) // 2
        base = (prices[middle] if len(prices) % 2 else (prices[middle - 1] + prices[middle]) / 2)
        found.append((row["date"], {"목표가": base, "목표가곳수": len(live)}))
    return found


final_group.flow_rows = flow_rows
study.target_timeline = target_timeline
assert "nrl" not in sys.modules, "nrl이 바꿔 끼우기 전에 import됨(FLOW · TARGETS가 원자료로 먼저 만들어짐)"
ns = {"__name__": "honest_cache", "__file__": HC}
exec(compile(open(HC, encoding="utf-8").read(), HC, "exec"), ns)       # 여기서 nrl import → 바꿔 끼운 로더로 FLOW · TARGETS 생성
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
assert nrl.final_group.flow_rows is flow_rows and study.target_timeline is target_timeline

T = pickle.load(open(os.environ["EX_FULL"], "rb"))["T"]
rule.trend_leg = ns["trend_leg_with"](T)


def window(row, n, col, k):
    got = nrl.FLOW.get(row["code"])
    if not got:
        return None
    days, acc, ok, _ = got
    lo = k - n
    if lo < 0 or k > len(days) or ok[k] - ok[lo] < n:
        return None
    return acc[col][k] - acc[col][lo]


def teacher_lag0(row, n=5):          # 돌연변이: 판단 날 당일 수급까지 씀
    got = nrl.FLOW.get(row["code"])
    if not got:
        return False
    k = bisect.bisect_right(got[0], row["date"])
    f, t, p = (window(row, n, c, k) for c in ("외국인", "투신", "개인"))
    return None not in (f, t, p) and f > 0 and t > 0 and p < 0


def teacher_lead1(row, n=5):         # 돌연변이: 다음 관측(미래) 하루까지 씀
    got = nrl.FLOW.get(row["code"])
    if not got:
        return False
    k = bisect.bisect_right(got[0], row["date"]) + 1
    f, t, p = (window(row, n, c, k) for c in ("외국인", "투신", "개인"))
    return None not in (f, t, p) and f > 0 and t > 0 and p < 0


def target_before_same_day(r, back_days=0):   # 돌연변이: 판단 날 당일 의견까지
    got = nrl.TARGETS.get(r["code"])
    if not got:
        return None
    days, vals = got
    day = r["date"]
    if back_days:
        from datetime import date, timedelta
        day = (date(int(day[:4]), int(day[4:6]), int(day[6:8])) - timedelta(days=back_days)).strftime("%Y%m%d")
    k = bisect.bisect_right(days, day)
    if k == 0:
        return None
    return vals[k - 1] if days[k - 1] >= study._months_before(day, 3) else None


if MUT == "lag0":
    nrl.teacher = teacher_lag0
elif MUT == "lead1":
    nrl.teacher = teacher_lead1
out = {"모드": MODE, "캐시": str(nrl.CACHE), "공시 자름": [FCUT, FMODE], "당일 독": DPOISON, "돌연변이": MUT,
       "적용 증거: FLOW 마지막 날 · TARGETS 마지막 날 · 당일 독 날 외국인 값(첫 종목)": [max(v[0][-1] for v in nrl.FLOW.values()), max(v[0][-1] for v in nrl.TARGETS.values() if v[0]),
           next((v[1]["외국인"][v[0].index(DPOISON) + 1] - v[1]["외국인"][v[0].index(DPOISON)] for v in nrl.FLOW.values() if DPOISON in v[0]), None) if DPOISON else None]}

if MODE == "PRE":
    inside_codes = {r["code"] for r in nrl.inside}
    files = {p[:-5] for p in os.listdir("investor-data") if p.endswith(".json")}
    syn_q = {"date": "20200601", "code": "Z1", "변동성": -1.0, "추세 기울기": 99, "60일 전 대비": 99}
    syn_n = dict(syn_q, 변동성=1e9)
    same_tt = all(target_timeline(c) == _tt(c) for c in sorted({p[:-5] for p in os.listdir("opinion-data") if p.endswith(".json")}))
    out.update({"rule._calm None": rule._calm is None, "CALM_MONTH None": nrl.CALM_MONTH is None,
                "trend_leg: 조용한 합성 행 참 · 시끄러운 행 거짓": [rule.trend_leg(syn_q), rule.trend_leg(syn_n)],
                "FLOW 종목 = inside ∩ 수급 파일": set(nrl.FLOW) == {c for c in inside_codes if c in files and final_group.flow_rows(c)},
                "000500 양성(FLOW · TARGETS · inside 행)": ["000500" in nrl.FLOW, "000500" in nrl.TARGETS, sum(1 for r in nrl.inside if r["code"] == "000500")],
                "합성 음성(수급 파일 없는 종목 teacher)": nrl.teacher({"code": "Z99999", "date": "20200601"}),
                "목표가 감싸기 = 원 함수(모든 종목)": same_tt,
                "kin 지문(가격 rows 묶음)": hashlib.sha256(json.dumps({c: nrl.prices[c]["rows"] for c in sorted(nrl.prices)}).encode()).hexdigest(),
                "inside 행": len(nrl.inside), "FLOW 종목": len(nrl.FLOW), "TARGETS 종목": len(nrl.TARGETS)})
    out["통과"] = out["rule._calm None"] and out["CALM_MONTH None"] and out["trend_leg: 조용한 합성 행 참 · 시끄러운 행 거짓"] == [True, False] and \
        out["FLOW 종목 = inside ∩ 수급 파일"] and all(out["000500 양성(FLOW · TARGETS · inside 행)"][:2]) and not out["합성 음성(수급 파일 없는 종목 teacher)"] and same_tt
elif MODE == "LED":
    EV, CAND = [], set()

    def size_w(row):
        s = nrl.BASE_SIZE(row)
        EV.append([CUR[0], len(EV), row["date"], row["code"], int(s)])
        return s

    def hold_w(row):
        v = nrl.BASE_HOLD(row)
        if v:
            CAND.add((CUR[0], row["date"], row["code"]))
        return v
    CUR = [None]
    rows, closed = [], []
    for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
        CUR[0] = side
        g = lab.run(pool, nrl.prices, hold_w, nrl.BASE_EXIT, rank=rule.order, slots=nrl.SLOTS, since=since, apart=nrl.kin,
                    realistic=True, cap=130, detail=True, size=size_w)
        rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for t in g["매매목록"]]
        closed += [[side, t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1] for t in g["매매목록"]]
    from collections import Counter
    opened = Counter((e[0], e[3], e[2]) for e in EV)
    shut_n = Counter((c[0], c[1], c[2]) for c in closed)          # 나눠 팔기면 한 매수에 종료 기록이 둘 이상
    gone = []
    for key, n in opened.items():                                  # 종료 기록이 없는 매수: 앞 반 끝 이음새 · 기간 끝 열린 보유 · 130일 한도(lab.py 851 ~ 854줄)
        if key not in shut_n:
            side, code, day = key
            ln = nrl.lanes[code]
            left = len(ln["날"]) - 1 - bisect.bisect_left(ln["날"], day)
            why = ("앞 반 끝(rule.MID) 열린 보유 — 뒤 반에 이어지지 않고 장부에서 빠짐" if side == "앞" else
                   "기간 끝 열린 보유" if left <= 130 else "130일 넘게 들어 장부에서 빠짐(정산 기록 없음)")
            gone += [[side, code, day, why]] * n
    led_path = os.environ.get("EX_LED")
    if led_path:
        json.dump(rows, open(led_path, "w"))
    ev = {"매수 사건": EV, "후보": sorted(CAND), "종료 매매": closed, "종료 기록 없는 매수": gone}
    json.dump(ev, open(OUT + ".events.json", "w"), ensure_ascii=False)
    out.update({"매수 사건": len(EV), "후보(날 · 종목)": len(CAND), "종료 매매(나눠 팔기 포함)": len(closed), "나눠 판 매수": sum(1 for v in shut_n.values() if v > 1),
                "종료 기록 없는 매수(이유별)": dict(Counter(g[3] for g in gone)),
                "사건 없는 종료 매매(0이어야)": sum(1 for k in shut_n if k not in opened),
                "장부 지문": hashlib.sha256(open(led_path, "rb").read()).hexdigest() if led_path else None})
elif MODE == "SIG":
    days8 = []
    for y in range(2018, 2026):
        got = sorted(d for d in nrl.BR if d.startswith(f"{y}06"))
        if got:
            days8.append(got[0])
    res = {}
    for d in days8:
        rows = [r for r in nrl.inside if r["date"] == d and r["code"] in nrl.FLOW and d in nrl.FLOW[r["code"]][0]]
        flow_same = flip0 = tgt_same = tgt_flip = tgt_n = 0
        for r in rows:
            c = r["code"]
            keep = nrl.FLOW[c]
            n0, m0 = nrl.teacher(r), teacher_lag0(r)
            fr = final_group.flow_rows(c)
            mod = [dict(x, 외국인=-1e13) if (x["date"] == d and m0) else (dict(x, 외국인=1e13, 투신=1e13, 개인=-1e13) if x["date"] == d else x) for x in fr]
            nrl.FLOW[c] = nrl.flow_entry(mod)
            n1, m1 = nrl.teacher(r), teacher_lag0(r)
            nrl.FLOW[c] = keep
            flow_same += (n0 == n1)
            flip0 += (m0 != m1)
            tk = nrl.TARGETS.get(c)
            if tk:
                b = target_before_same_day(r, 45)
                if b:
                    dd, vv = list(tk[0]), list(tk[1])
                    j = bisect.bisect_left(dd, d)
                    new = {"목표가": b["목표가"] * 0.01, "목표가곳수": 1}
                    if j < len(dd) and dd[j] == d:
                        vv[j] = new
                    else:
                        dd.insert(j, d)
                        vv.insert(j, new)
                    c0 = nrl.target_cut(r)
                    mb0 = target_before_same_day(r)
                    nrl.TARGETS[c] = (dd, vv)
                    c1 = nrl.target_cut(r)
                    mb1 = target_before_same_day(r)
                    nrl.TARGETS[c] = tk
                    tgt_n += 1
                    tgt_same += (c0 == c1)
                    tgt_flip += ((mb0 or {}).get("목표가") != (mb1 or {}).get("목표가"))
        res[d] = {"행": len(rows), "정상 teacher 같음": flow_same, "lag0 뒤집힘": flip0, "목표가 시험 행": tgt_n, "목표가 바꾼 행 정상 target_cut 같음": tgt_same,
                  "당일 조회 돌연변이 값 바뀜": tgt_flip}
    out["날별"] = res
    tot = {k: sum(v[k] for v in res.values()) for k in next(iter(res.values()))}
    out["합"] = tot
    out["통과"] = tot["정상 teacher 같음"] == tot["행"] and tot["lag0 뒤집힘"] >= 1 and tot["목표가 바꾼 행 정상 target_cut 같음"] == tot["목표가 시험 행"] and tot["당일 조회 돌연변이 값 바뀜"] >= 1
elif MODE == "CMP":
    c = os.environ["EX_CUT"]
    A, B = json.load(open(os.environ["EX_A"])), json.load(open(os.environ["EX_B"]))
    ea = [e[:1] + e[2:] for e in A["매수 사건"] if e[2] <= c]
    eb = [e[:1] + e[2:] for e in B["매수 사건"] if e[2] <= c]
    ca = [x for x in A["후보"] if x[1] <= c]
    cb = [x for x in B["후보"] if x[1] <= c]
    ta = [x for x in A["종료 매매"] if x[2] <= c]
    tb = [x for x in B["종료 매매"] if x[2] <= c]
    first = next((i for i, (x, y) in enumerate(zip(ea, eb)) if x != y), None if len(ea) == len(eb) else min(len(ea), len(eb)))
    out.update({"자르는 날": c, "매수 사건(c까지) 같음 · 수": [ea == eb, len(ea), len(eb)], "후보(c까지) 같음 · 수": [ca == cb, len(ca), len(cb)],
                "처음 다른 매수 사건": [ea[first] if first is not None and first < len(ea) else None, eb[first] if first is not None and first < len(eb) else None],
                "참고: c까지 산 종료 매매(미래 판 날 · 손익 포함) 같음": ta == tb})
    out["같음"] = ea == eb and ca == cb
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k not in ("날별",)}, ensure_ascii=False, default=str)[:3000])
