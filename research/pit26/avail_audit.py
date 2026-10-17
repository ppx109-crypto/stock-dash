"""바깥 입력 이용가능 시각 감사 A ~ D(AVAIL_DESIGN.md · 손익 없음 · 건수 · 날 · 종목만).
A 정정 흔적: investor-data · opinion-data 파일의 git 판끼리 같은 날(같은 열쇠) 값이 바뀐 건수.
B 주식수 접수일 당일 사용: caps.known_by(접수일 ≤ 날) 대 '접수일 < 날'로 그날 시총 100위 집합이 바뀌는 (날, 종목) 수 · 그중 정직 캐시 BASE_HOLD 참 행.
C 대상 종목 선택: study/flow_universe.json의 git 첫 판 · 정직 캐시 inside 행 가운데 수급 파일이 없는 종목의 행 수.
D 결측: 정직 캐시 inside 행 가운데 teacher의 수급 합이 None(자료 모자람 · 낡음)인 행 수.
cwd = 고정 나무(tree_run) · EX_REPO = 저장소 뿌리(git 기록) · EX_FULL = 정직 캐시 pkl · EX_HC = honest_cache.py. 출력 EX_OUT."""
import bisect
import json
import os
import pickle
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
HC = os.environ["EX_HC"]
ns = {"__name__": "honest_cache", "__file__": HC}
exec(compile(open(HC, encoding="utf-8").read(), HC, "exec"), ns)
import caps  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402

REPO = os.environ["EX_REPO"]
TREE_REV = "9743cb802"


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=REPO).stdout


def versions(path):
    return [h for h in git("log", "--format=%H", "--", path).split() if h]


def load_rev(h, path):
    out = subprocess.run(["git", "show", f"{h}:{path}"], capture_output=True, cwd=REPO).stdout
    try:
        return json.loads(out)
    except ValueError:
        return None


def keyed_inv(body):
    cols = body.get("cols") or []
    return {r[0]: tuple(r[1:]) for r in body.get("rows") or [] if r}


def keyed_op(body):
    return {(r.get("date"), r.get("member")): (r.get("target"), r.get("opinion")) for r in body.get("rows") or []}


def revisions(folder, keyer, codes):
    tot = Counter()
    ex = []
    for c in codes:
        path = f"{folder}/{c}.json"
        vs = versions(path)[::-1]          # 옛 판부터
        prev = None
        for h in vs:
            b = load_rev(h, path)
            if b is None:
                continue
            cur = keyer(b)
            if prev is not None:
                common = set(prev) & set(cur)
                ch = [k for k in common if prev[k] != cur[k]]
                gone = [k for k in prev if k not in cur]
                tot["비교한 판 쌍"] += 1
                tot["같은 열쇠 값 바뀜"] += len(ch)
                tot["앞 판에 있던 열쇠가 사라짐"] += len(gone)
                if ch and len(ex) < 10:
                    ex.append({"종목": c, "판": h[:9], "예 열쇠": str(sorted(ch)[0])})
            prev = cur
        tot["종목"] += 1
    return dict(tot), ex


inv_codes = sorted(p[:-5] for p in os.listdir(os.path.join(REPO, "investor-data")) if p.endswith(".json"))
op_codes = sorted(p[:-5] for p in os.listdir(os.path.join(REPO, "opinion-data")) if p.endswith(".json"))
A_inv, A_inv_ex = revisions("investor-data", keyed_inv, inv_codes)
A_op, A_op_ex = revisions("opinion-data", keyed_op, op_codes)

# B 주식수 접수일 당일 대 다음 날부터
P = study.load_prices()
full = pickle.load(open(os.environ["EX_FULL"], "rb"))


def known_strict(code, day):
    found = None
    for when, count in caps.timeline(code):
        if when >= day:
            break
        found = count
    return found


def top_sets(known):
    by_day = {}
    for c in sorted(P):
        for d, px in P[c]["rows"]:
            if d < rule.SINCE or not px:
                continue
            cnt = known(c, d)
            if cnt is not None:
                by_day.setdefault(d, []).append((c, cnt * px))
    out = {}
    for d, here in by_day.items():
        here.sort(key=lambda one: -one[1])
        out[d] = {c for c, _ in here[:rule.TOP]}
    return out


same_day = top_sets(caps.known_by)
next_day = top_sets(known_strict)
left, entered = [], []
for d in same_day:
    a, b = same_day[d], next_day.get(d, set())
    left += [(c, d) for c in a - b]
    entered += [(c, d) for c in b - a]
tl = ns["trend_leg_with"](full["T"])
left_bh = [k for k in left if k in full["inside"] and ns["gates"](full["inside"][k], tl, full["shape"], full["BR"])["BASE_HOLD"]]
recv_same = 0
for c in sorted(P):
    days = {d for d, _ in P[c]["rows"]}
    recv_same += sum(1 for when, _ in caps.timeline(c) if when in days and when >= rule.SINCE)
B = {"접수일이 거래일인 공시(SINCE ~)": recv_same, "시총 100위에서 빠지는 (종목, 날)": len(left), "새로 드는 (종목, 날)": len(entered),
     "빠지는 행 가운데 정직 캐시 BASE_HOLD 참": len(left_bh), "빠지는 예": sorted(left)[:10], "BASE_HOLD 참 예": sorted(left_bh)[:10]}

# C 대상 종목 선택
fu = "study/flow_universe.json"
fu_vs = versions(fu)
fu_first = git("log", "--format=%h %ci %s", "--diff-filter=A", "--", fu).strip()
inside = {k: r for k, r in full["inside"].items() if k[1] >= rule.SINCE}
no_flow = [k for k in inside if not os.path.exists(os.path.join(os.getcwd(), "investor-data", f"{k[0]}.json"))]
C = {"flow_universe 첫 판(커밋 · 시각 · 제목)": fu_first, "판 수": len(fu_vs), "inside 행(SINCE ~)": len(inside),
     "수급 파일 없는 종목의 inside 행": len(no_flow), "그 종목 수": len({k[0] for k in no_flow}), "예 종목": sorted({k[0] for k in no_flow})[:15]}

# D 결측
none_rows = [k for k, r in inside.items() if nrl.flow_sum(r, 5, "외국인") is None]
D = {"teacher 수급 합 None 인 inside 행": len(none_rows), "그중 수급 파일 없음": len(set(none_rows) & set(no_flow)),
     "파일은 있는데 None(창 모자람 · 결측 칸)": len(set(none_rows) - set(no_flow))}
out = {"A 정정 흔적 · 수급": A_inv, "A 수급 예": A_inv_ex, "A 정정 흔적 · 목표가": A_op, "A 목표가 예": A_op_ex, "B 주식수 접수일 당일": B, "C 대상 종목 선택": C, "D 결측": D,
       "범위": "고정 나무 판(9743cb802) 위 정직 캐시 · git 기록은 저장소 전체 판(수집 뒤 바뀐 값) · git 시각은 실제 입수 시각 아님 · 손익 · 성과 출력 없음"}
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:5000])
