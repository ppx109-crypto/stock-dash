"""KMF-0015 — 시간대 짧은 추세 봇 + 전날 수급 거름(5분봉 판단 · 1분봉 신호 없음) · 하루 −25p · 1계약.
사용자 2026-10-13: "위 10일을 제외하고 작거나 짧은 추세에도 작동할 추세봇 · +800p" → 추세 따라가기로는 못 찾음(KMF-0014) →
 "고"(거래량 급증 · 시간대 · 수급으로). 개발 = 전체 자료 2026-01-02 ~ 10-12 한 번에(탐색 KMF-0015/explore) · 판정 = 시험 2만.
규칙(5분봉 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · −25p 봉 안 멈춤 · 그날 마지막 봉 정리 · 편도 0.04p):
  창(30분 + 30분): 이어감 창 09:05 · 09:35 · 10:05 · 11:35 · 13:05 · 13:35 / 되돌림 창 14:05
   앞 30분(창 시작 봉 시가 → 30분째 봉 종가) 움직임 방향으로(되돌림 창은 반대로) 뒤 30분 듦 → 60분째 봉 종가에 정리
  수급 거름: 전날(그날 앞 마지막 거래일) 코스피 개인 순매수가 앞 20거래일 평균보다 많으면 '오름 쪽' · 적으면 '내림 쪽' →
   그 쪽과 같은 방향의 창만 듦(장 끝난 뒤 나온 자료를 다음 거래일에만 씀)
  창은 전체 자료 진단에서 앞 반(01 ~ 05) · 뒤 반(06 ~ 10) 모두 같은 부호인 창만 고름(explore/time_flow_diag)
수급 자료 출처(round 2 · GPT #309): 한국투자증권 Open API FHPTJ04040000(/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market)
  코스피(FID_INPUT_ISCD 0001) 일별 · 개인 = prsn_ntby_tr_pbmn(순매수 거래대금 · 같은 줄의 부호만 견줘 단위는 판정에 영향 없음)
  모으는 곳: collect_kis_extra.py market ← .github/workflows/kis-extra-history.yml(평일 18:40 KST) · 커밋 'Collect KIS extra history (market)'
  정정 정책: 모으는 코드가 새 날만 이어 붙이고 지난 날은 다시 받지 않음 · 공급자 정정 버전: 미제공 → 잠근 스냅샷 SHA · 커밋으로 재현
  시험 2(KMF-0015만 10-14부터 완전한 거래일 처음 20일): 날마다 그 앞 21거래일(선물 거래일 달력) 수급 줄이 모두 있고,
   각 줄이 처음 커밋된 시각 ≤ 그 거래일 09:00 KST · 값 정정 없음(영수증) · 하나라도 아니면 판정 파일 쓰기 전에 NEEDS_DATA로 멈춤
   test2_ok.json = {gpt_pr, data_sha256, flow_sha256, receipt_sha256} · 영수증 SHA도 판정 전에 대조(round 3)
python3 research/kmf15.py lock | report | cut | receipt | test2"""
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402
import kmf4 as K4  # noqa: E402
import kmf13 as M13  # noqa: E402
import kmf14 as M14  # noqa: E402

K.DAY_STOP = -25.0
ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0015"
LOCK = BOX / "input_lock.json"
FLOW = ROOT / "market-data/investor_KSP.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf13.py", "research/kmf14.py", "research/kmf15.py"]
TF = 5
END = M13.END
GUARD_BEFORE = END
MOM = (545, 575, 605, 695, 785, 815)
REV = (845,)
PICK = {"mom": MOM, "rev": REV, "flow": 1, "q": 0.0}
TEST2_MIN_PER_DAY = 1.94                   # 개발 하루 평균 3.882의 절반 1.941(PLAN §4)


def grid():
    g = [dict(PICK), dict(PICK, rev=()), dict(PICK, flow=0), dict(PICK, q=0.5)]
    for c in g:
        c["tag"] = f"m{len(c['mom'])}_r{len(c['rev'])}_f{c['flow']}_q{c['q']}"
    return g


def name(cfg):
    return cfg["tag"]


def prep(rows, cfg=None):
    return K4.day_start_aligned(rows, TF)


_BIAS = {}


def flow_bias(days):
    """날마다 전날 개인 순매수 z 부호(+1 / −1) · 그날 앞 마지막 거래일 값과 그 앞 20거래일만 씀."""
    key = (tuple(days), FLOW.stat().st_mtime)
    if key in _BIAS:
        return _BIAS[key]
    inv = {r["date"]: r["개인"] for r in json.loads(FLOW.read_text())["rows"]}
    idates = sorted(inv)
    out = {}
    import bisect
    for d in days:
        k = bisect.bisect_left(idates, d)                # idates[:k] 모두 d 앞
        if k < 21:
            continue
        prev = idates[k - 21:k]
        hist = [inv[x] for x in prev[:-1]]
        sd = float(np.std(hist)) or 1.0
        out[d] = 1 if (inv[prev[-1]] - float(np.mean(hist))) / sd > 0 else -1
    _BIAS[key] = out
    return out


def signals(b, cfg):
    n = len(b)
    want = [None] * n
    if n == 0:
        return want
    c = np.array([r[5] for r in b]); o = np.array([r[2] for r in b]); h = np.array([r[3] for r in b]); l = np.array([r[4] for r in b])
    pc = np.r_[c[0], c[:-1]]
    trr = np.maximum(np.maximum(h - l, np.abs(h - pc)), np.abs(l - pc))
    atr = np.full(n, np.nan)
    for i in range(20, n):
        atr[i] = trr[i - 20:i].mean()
    idx = {(r[0], r[1]): i for i, r in enumerate(b)}
    days = sorted({r[0] for r in b})
    bias = flow_bias(days)
    wins = sorted([(x, 1) for x in cfg["mom"]] + [(x, -1) for x in cfg["rev"]])
    for d in days:
        for h0, sgn in wins:
            s0, s1, e1 = idx.get((d, h0 + 4)), idx.get((d, h0 + 29)), idx.get((d, h0 + 59))
            if s0 is None or s1 is None:                  # 들기는 그 봉까지 자료로만 정함(정리 봉이 있는지는 안 봄 · round 1 검사 뒤 고침)
                continue
            a = c[s1] - o[s0]
            if a == 0 or (cfg["q"] and (np.isnan(atr[s1]) or abs(a) < cfg["q"] * atr[s1])):
                continue
            side = int(np.sign(a)) * sgn
            if cfg["flow"] and bias.get(d) != side:
                continue
            if want[s1] is None or want[s1] == 0:
                want[s1] = side
            if e1 is not None:                            # 60분째 봉이 없으면(자료 빠짐) 다음 창이나 장 끝에 정리
                want[e1] = 0
    return want


def lock_body():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    body = {f: sha(ROOT / f) for f in CODE_FILES}
    body.update({f"kiwoom-data/{p.name}": sha(p) for p in (K.MINI, K.FUT)})
    body["market-data/investor_KSP.json"] = sha(FLOW)
    return body


def verify_inputs(path=None):
    want = json.loads(Path(path or LOCK).read_text())
    have = lock_body()
    bad = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k))
    if bad:
        sys.exit("입력 잠금이 다름(멈춤): " + json.dumps(bad, ensure_ascii=False))
    return want


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1)); print(LOCK.read_text())


def report():
    verify_inputs()
    b = prep(K._rows_before(END))
    d13, _ = K.simulate(b, M13.signals(b, M13.grid()[0]))
    d14, _ = K.simulate(b, M14.signals(b, M14.grid()[0]))
    top13 = set(sorted(d13, key=lambda d: -d13[d])[:10])
    out = {}
    for cfg in grid():
        days, trades = K.simulate(b, signals(b, cfg))
        st = K.stats(days, trades, "20260101", "20261012")
        vs = sorted(days.values(), reverse=True)
        st["concentration"] = {"top10_sum": round(sum(vs[:10]), 2), "rest_sum": round(sum(vs[10:]), 2)}
        ds = sorted(days)
        st["corr"] = {"kmf13": round(float(np.corrcoef([days[d] for d in ds], [d13[d] for d in ds])[0, 1]), 3),
                      "kmf14": round(float(np.corrcoef([days[d] for d in ds], [d14[d] for d in ds])[0, 1]), 3)}
        for nm, parts in (("with13", (d13,)), ("with13_14", (d13, d14))):
            both = {d: days[d] + sum(p[d] for p in parts) for d in ds}
            bv = sorted(both.values(), reverse=True)
            st[nm] = {"total": round(sum(bv), 2), "ex_own_top10": round(sum(bv[10:]), 2),
                      "ex_kmf13_top10_days": round(sum(v for d, v in both.items() if d not in top13), 2), "worst_day": round(min(bv), 2)}
        out[name(cfg)] = st
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/dev_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    p = out[name(grid()[0])]
    print(json.dumps({"pick": name(grid()[0]), "total_p": p["total_p"], "per_day_p": p["per_day_p"], "concentration": p["concentration"],
                      "with13_14": p["with13_14"], "neighbors_total": {k: v["total_p"] for k, v in out.items()}}, ensure_ascii=False))


TEST2_N = 20
TEST2_FROM = "20261014"                   # KMF-0015만: 10-13 판단에 쓸 10-12 수급은 10-13 09:00 전에 없었음(수집 고침 #310 · 10-13 저녁부터 그날 줄)
TEST2_OK = BOX / "test2_ok.json"
TEST2_OUT = BOX / "evidence/test2.json"


RECEIPT = BOX / "evidence/flow_receipt.json"
FLOW_REL = "market-data/investor_KSP.json"


def make_receipt(ref="origin/main"):
    """수급 파일의 저장 이력(ref · 오래된 것부터)에서 날짜마다 처음 들어온 커밋 · 시각 · 뒤에 값이 바뀐 횟수."""
    log = subprocess.run(["git", "log", "--reverse", "--format=%H %cI", ref, "--", FLOW_REL], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    first, last_val, changes = {}, {}, defaultdict(int)
    for sha, when in zip(log[0::2], log[1::2]):
        body = subprocess.run(["git", "show", f"{sha}:{FLOW_REL}"], cwd=ROOT, capture_output=True, text=True)
        if body.returncode:
            continue
        for r in json.loads(body.stdout)["rows"]:
            d, v = r["date"], r["개인"]
            if d not in first:
                first[d] = {"commit": sha, "committed_at": when}
            elif last_val.get(d) != v:
                changes[d] += 1
            last_val[d] = v
    out = {"ref": ref, "file": FLOW_REL, "dates": {d: dict(first[d], value_changes=changes.get(d, 0)) for d in sorted(first)}}
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print(json.dumps({"dates": len(first), "changed_dates": sum(1 for d in changes if changes[d])}, ensure_ascii=False))


def flow_ready(pick_days, trade_days, flow_dates, receipt):
    """시험 2 날마다: 그 앞 21개 선물 거래일 모두 수급 줄 있음 · 각 줄 처음 커밋 ≤ 그날 09:00 KST · 값 정정 없음. 문제 목록과 쓴 수급 날짜."""
    from datetime import datetime, timezone, timedelta
    kst = timezone(timedelta(hours=9))
    td = sorted(set(trade_days)); fd = set(flow_dates); rec = receipt.get("dates", {})
    problems, used = [], {}
    for d in pick_days:
        prev = [x for x in td if x < d][-21:]
        if len(prev) < 21:
            problems.append(f"{d}: 앞 거래일 21개 모자람"); continue
        used[d] = prev
        cutoff = datetime.strptime(d + " 09:00", "%Y%m%d %H:%M").replace(tzinfo=kst)
        for x in prev:
            if x not in fd:
                problems.append(f"{d}: 수급 {x} 없음"); continue
            r = rec.get(x)
            if not r:
                problems.append(f"{d}: 수급 {x} 영수증 없음"); continue
            if datetime.fromisoformat(r["committed_at"]) > cutoff:
                problems.append(f"{d}: 수급 {x} 처음 커밋 {r['committed_at']} > 그날 09:00")
            if r.get("value_changes"):
                problems.append(f"{d}: 수급 {x} 값이 뒤에 바뀜")
    return problems, used


def receipt_check(ok, path=None):
    """test2_ok.json의 receipt_sha256과 실제 영수증 SHA가 같아야 함 · 다르거나 없으면 NEEDS_DATA로 멈춤. 같으면 그 SHA를 돌려줌."""
    have = hashlib.sha256(Path(path or RECEIPT).read_bytes()).hexdigest()
    if not ok.get("receipt_sha256") or have != ok["receipt_sha256"]:
        sys.exit("NEEDS_DATA: 수급 영수증 SHA가 시험 2 잠금과 다름(판정 안 함)")
    return have


def test2():
    """시험 2 한 번(KMF-0013과 같은 날 고르기 · 워밍업 · 결손일 처리) + 수급 자료도 잠금 해시가 맞아야 함."""
    verify_inputs()
    if TEST2_OUT.exists():
        sys.exit("시험 2는 이미 했음(다시 안 돌림)")
    if not TEST2_OK.exists() or not K.TEST2_FILE.exists():
        sys.exit("시험 2 자료 잠금 동의(test2_ok.json) 또는 자료가 없음(멈춤)")
    ok = json.loads(TEST2_OK.read_text())
    if hashlib.sha256(K.TEST2_FILE.read_bytes()).hexdigest() != ok["data_sha256"]:
        sys.exit("시험 2 자료 해시가 잠금과 다름(멈춤)")
    if hashlib.sha256(FLOW.read_bytes()).hexdigest() != ok.get("flow_sha256"):
        sys.exit("수급 자료 해시가 시험 2 잠금과 다름(멈춤)")
    rows = K.load()
    good, bad = M13.complete_days(rows, start=TEST2_FROM)
    if len(good) < TEST2_N:
        sys.exit(f"완전한 거래일 {len(good)}일 < {TEST2_N}일(멈춤)")
    pick_days = good[:TEST2_N]
    last = pick_days[-1]
    if not RECEIPT.exists():
        sys.exit("NEEDS_DATA: 수급 영수증(evidence/flow_receipt.json) 없음 — python3 research/kmf15.py receipt 먼저(멈춤)")
    receipt_sha = receipt_check(ok)                       # 잠근 영수증 SHA와 다르면 판정 전에 멈춤(round 3)
    flow_dates = [r["date"] for r in json.loads(FLOW.read_text())["rows"]]
    problems, used = flow_ready(pick_days, sorted({r[0] for r in rows}), flow_dates, json.loads(RECEIPT.read_text()))
    if problems:
        sys.exit("NEEDS_DATA: 수급 자료 문제(판정 안 함) " + json.dumps(problems[:20], ensure_ascii=False))
    b = prep(M13.test2_rows(rows, pick_days))
    days, trades = K.simulate(b, signals(b, grid()[0]))
    sel = {d: days.get(d, 0.0) for d in pick_days}
    st = K.stats(sel, [t for t in trades if t[0] in sel], pick_days[0], last)
    passed = st["total_p"] > 0 and st["per_day_p"] >= TEST2_MIN_PER_DAY and st["worst_day_p"] >= -25.5
    out = {"verdict": "PASS" if passed else "NO_EDGE", "pick": name(grid()[0]), "days": pick_days,
           "excluded_incomplete": {d: v for d, v in bad.items() if d <= last}, "stats": st, "data_sha256": ok["data_sha256"],
           "flow_sha256": ok["flow_sha256"], "flow_dates_used": {d: used[d][-1] for d in pick_days},
           "receipt_sha256": receipt_sha}
    TEST2_OUT.parent.mkdir(parents=True, exist_ok=True)
    TEST2_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": out["verdict"], "total_p": st["total_p"], "per_day_p": st["per_day_p"]}, ensure_ascii=False))


def cut():
    cuts = ("20260302", "20260601", "20260901")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf15 as M;"
            "c=json.loads(os.environ['KC']);c['mom']=tuple(c['mom']);c['rev']=tuple(c['rev']);b=M.prep(K.load());d,_=K.simulate(b,M.signals(b,c));print(json.dumps(d))")
    res = []
    for cfg in grid():
        env = dict(os.environ, KC=json.dumps(cfg), KMF_CUT=END)
        full = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for ct in cuts:
            env["KMF_CUT"] = ct
            part = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in part if d < ct]
            res.append({"cfg": name(cfg), "cut": ct, "days": len(ds), "diff": sum(1 for d in ds if abs(part[d] - full[d]) > 1e-9),
                        "no_future_days": all(d < ct for d in part)})
    print(json.dumps({"pass": all(r["diff"] == 0 and r["no_future_days"] for r in res), "runs": res}, ensure_ascii=False))


if __name__ == "__main__":
    {"lock": write_lock, "cut": cut, "report": report, "receipt": make_receipt, "test2": test2}[sys.argv[1]]()
