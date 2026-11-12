"""바깥 입력 이용가능 시각 감사 판 2(SHARES_NEXT.md 5절 · GPT #457 5·6차 2절 A ~ D · 손익 없음 · 건수 · 날 · 종목만).
A 정정 흔적: investor-data · opinion-data · share-data 파일의 git 판(끝점 = 고정 나무 커밋 TREE_REV 고정)끼리 같은 열쇠 값이 바뀐 건수.
  git 반환값 · 판 읽기 · JSON 실패는 오류로 따로 셈 → 하나라도 있으면 '불완전 감사'. 수급은 칸 이름으로 맞춤 · 목표가 · 주식수는 열쇠 중복을 먼저 셈(값 묶음 비교).
  바뀐 열쇠의 위치(앞 판 마지막 날 · 마지막 5개 날 안 · 그 앞)와 사건 수 · 서로 다른 (종목, 날) 수를 나눔.
B 주식수: 이 파일에서 셈하지 않음 → run_honest.py COMPARE(같은 모집단 비교).
C 날별 자료 충족: 정직 캐시 inside 행마다 판단 날 앞 5관측 · 6칸 값 · 마지막 관측일과 앞 거래일 간격 · 엔진 FLOW/TARGETS가 그 종목을 담는지.
D 결측 방향: flow_sum 세 합(외국인 · 투신 · 개인) 각각 None · 목표가 target_before None 이유별(→ target_cut 거짓 = 차단 풀림).
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
import final_group  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402

REPO = os.environ["EX_REPO"]
TREE_REV = "9743cb802732ed381a15da9ae45109f3a0f8a2c9"
ERR = []


def git(*a, binary=False):
    r = subprocess.run(["git", *a], capture_output=True, text=not binary, cwd=REPO)
    if r.returncode != 0:
        ERR.append({"명령": " ".join(a)[:120], "반환값": r.returncode})
        return None
    return r.stdout


def files_at(folder):
    out = git("ls-tree", "--name-only", f"{TREE_REV}:{folder}")
    return sorted(p[:-5] for p in (out or "").split() if p.endswith(".json"))


def versions(path):
    out = git("log", "--format=%H", TREE_REV, "--", path)
    return [h for h in (out or "").split() if h][::-1]          # 옛 판부터


def load_rev(h, path):
    out = git("show", f"{h}:{path}", binary=True)
    if out is None:
        return None
    try:
        return json.loads(out)
    except ValueError:
        ERR.append({"명령": f"json {h[:9]}:{path}", "반환값": "JSON 실패"})
        return None


def keyed_inv(body):
    """수급: 날 → {칸 이름: 값}. 같은 날 줄이 둘 이상이면 중복으로 셈."""
    cols = body.get("cols") or []
    out, dup = {}, 0
    if "date" not in cols:
        ERR.append({"명령": "수급 cols에 date 없음", "반환값": str(cols)[:80]})
        return {}, 0, tuple(cols)
    di = cols.index("date")
    for r in body.get("rows") or []:
        if not r:
            continue
        d = str(r[di])
        if d in out:
            dup += 1
        out.setdefault(d, []).append(tuple(sorted((c, v) for c, v in zip(cols, r) if c != "date")))
    return {k: tuple(sorted(v)) for k, v in out.items()}, dup, tuple(c for c in cols if c != "date")


def keyed_op(body):
    out, dup = {}, 0
    for r in body.get("rows") or []:
        k = (str(r.get("date")), r.get("member"))
        if k in out:
            dup += 1
        out.setdefault(k, []).append((r.get("target"), r.get("opinion"), r.get("prior_opinion")))
    return {k: tuple(sorted(v, key=repr)) for k, v in out.items()}, dup, None


def keyed_share(body):
    out, dup = {}, 0
    for r in body.get("날") or []:
        if not r:
            continue
        k = str(r[0])
        if k in out:
            dup += 1
        out.setdefault(k, []).append(r[1])
    return {k: tuple(sorted(v, key=repr)) for k, v in out.items()}, dup, None


OP_FIELDS = ("target", "opinion", "prior_opinion")


def changed_fields(a, b):
    """바뀐 칸 이름(값 묶음이 한 줄씩일 때만 · 아니면 '줄 수 다름'). 수급 = (칸, 값) 쌍 줄 · 목표가 = OP_FIELDS 순서 · 주식수 = 수."""
    if len(a) != 1 or len(b) != 1:
        return ["줄 수 다름"]
    x, y = a[0], b[0]
    if isinstance(x, tuple) and x and isinstance(x[0], tuple):
        dx, dy = dict(x), dict(y)
        return sorted(c for c in dx.keys() | dy.keys() if dx.get(c) != dy.get(c))
    if isinstance(x, tuple):
        return [OP_FIELDS[i] for i in range(len(x)) if x[i] != y[i]]
    return ["주식수"]


def day_of(k):
    return k if isinstance(k, str) else k[0]


def revisions(folder, keyer):
    tot, where, gone_where, fields = Counter(), Counter(), Counter(), Counter()
    uniq, ex = set(), []
    for c in files_at(folder):
        path = f"{folder}/{c}.json"
        vs = versions(path)
        tot["종목"] += 1
        tot["판"] += len(vs)
        prev = prev_cols = None
        for h in vs:
            b = load_rev(h, path)
            if b is None:
                tot["읽기 실패 판"] += 1
                continue
            cur, dup, cols = keyer(b)
            tot["판 안 열쇠 중복(줄)"] += dup
            if prev is not None:
                tot["비교한 판 쌍"] += 1
                proj = lambda v: v  # noqa: E731
                if cols is not None and prev_cols != cols:
                    tot["칸 이름 다른 판 쌍"] += 1
                    both = set(prev_cols) & set(cols)          # 칸 이름이 다르면 두 판에 다 있는 칸끼리만 비교
                    proj = lambda v: tuple(tuple(p for p in row if p[0] in both) for row in v)  # noqa: E731
                pdays = sorted({day_of(k) for k in prev})
                last, last5 = pdays[-1], set(pdays[-5:])

                def place(k):
                    d = day_of(k)
                    return "앞 판 마지막 날" if d == last else ("앞 판 마지막 5개 날 안(마지막 날 뺌)" if d in last5 else ("앞 판 마지막 날 뒤" if d > last else "그 앞"))
                ch = [k for k in prev.keys() & cur.keys() if proj(prev[k]) != proj(cur[k])]
                gone = [k for k in prev if k not in cur]
                for k in ch:
                    where[place(k)] += 1
                    for f in changed_fields(proj(prev[k]), proj(cur[k])):
                        fields[f] += 1
                    uniq.add((c, day_of(k)))
                for k in gone:
                    gone_where[place(k)] += 1
                tot["같은 열쇠 값 바뀜(사건 = 판 쌍 × 열쇠)"] += len(ch)
                tot["앞 판 열쇠 사라짐(사건)"] += len(gone)
                if ch and len(ex) < 10:
                    ex.append({"종목": c, "판": h[:9], "예 열쇠": str(sorted(ch, key=repr)[0])})
            prev, prev_cols = cur, cols
    tot["값 바뀐 서로 다른 (종목, 날)"] = len(uniq)
    return {"합계": dict(tot), "바뀐 칸(사건마다 칸별)": dict(fields), "바뀜 위치": dict(where), "사라짐 위치": dict(gone_where), "예": ex}


A = {f: revisions(f, k) for f, k in (("investor-data", keyed_inv), ("opinion-data", keyed_op), ("share-data", keyed_share))}
tree_time = (git("log", "-1", "--format=%ci", TREE_REV) or "").strip()

# C · D: 정직 캐시 inside 행(SINCE ~)
P = study.load_prices()
full = pickle.load(open(os.environ["EX_FULL"], "rb"))
inside = {k: r for k, r in full["inside"].items() if k[1] >= rule.SINCE}
codes = sorted({k[0] for k in inside})
cal = {c: [d for d, _ in P[c]["rows"]] for c in codes}
fl = {}
for c in codes:
    fr = final_group.flow_rows(c)
    fl[c] = ([x.get("date") for x in fr], fr)
C = Counter()
gap = Counter()
mismatch = []
for (c, d), r in sorted(inside.items()):
    days, fr = fl[c]
    if not fr:
        C["수급 파일 없음(또는 빈 파일)"] += 1
        continue
    k = bisect.bisect_left(days, d)
    win = fr[max(0, k - 5):k]
    ok = len(win) == 5 and all(x.get(col) is not None for x in win for col in nrl.COLS)
    C["앞 5관측 · 6칸 모두 값(쓸 수 있음)" if ok else ("앞 관측 5개 모자람" if len(win) < 5 else "앞 5관측 안 빈 칸")] += 1
    if k:
        j = bisect.bisect_left(cal[c], d)
        prev_trade = cal[c][j - 1] if j else None
        g = (j - 1) - bisect.bisect_left(cal[c], days[k - 1]) if prev_trade else None
        gap["없음" if g is None else (str(g) if g <= 5 else "6 이상")] += 1
    if (nrl.flow_sum(r, 5, "외국인") is None) == ok:
        mismatch.append((c, d))
C["엔진 flow_sum None 여부와 위 셈이 다른 행"] = len(mismatch)
eng_flow_missing = sorted(set(codes) - set(nrl.FLOW))
eng_flow_missing_with_file = [c for c in eng_flow_missing if fl[c][1]]
eng_tgt_missing = sorted(set(codes) - set(nrl.TARGETS))
eng_tgt_missing_with_file = [c for c in eng_tgt_missing if study.target_timeline(c)]


def t_reason(r, back):
    got = nrl.TARGETS.get(r["code"])
    if not got:
        return "엔진 TARGETS에 종목 없음"
    v = nrl.target_before(r, back)
    if v is not None:
        return "값 있음"
    days = got[0]
    day = r["date"]
    if back:
        from datetime import date, timedelta
        day = (date(int(day[:4]), int(day[4:6]), int(day[6:8])) - timedelta(days=back)).strftime("%Y%m%d")
    return "앞 의견 없음" if bisect.bisect_left(days, day) == 0 else "3달 넘음"


D_flow = {col: sum(1 for r in inside.values() if nrl.flow_sum(r, 5, col) is None) for col in ("외국인", "투신", "개인")}
masks_differ = sum(1 for r in inside.values() if len({nrl.flow_sum(r, 5, col) is None for col in ("외국인", "투신", "개인")}) > 1)
now_r = Counter(t_reason(r, 0) for r in inside.values())
bef_r = Counter(t_reason(r, 45) for r in inside.values())
free = sum(1 for r in inside.values() if nrl.target_before(r) is None or nrl.target_before(r, 45) is None)
D = {"수급 합 None 행(외국인 · 투신 · 개인 각각)": D_flow, "세 합 None 여부가 서로 다른 행": masks_differ,
     "공통 마스크 근거": "nrl.flow_sum은 lo < 0 또는 ok(6칸 모두 값인 날 누적) 창 < n이면 None — 칸과 무관한 같은 조건(고정 나무 nrl.py 87 ~ 99줄)",
     "목표가 지금(target_before) 이유별": dict(now_r), "목표가 45일 전 이유별": dict(bef_r),
     "둘 중 하나 None → target_cut 거짓(차단 풀림) 행": free,
     "방향": "수급 결측 → teacher 거짓(후보 막힘) · 목표가 결측 → target_cut 거짓(차단 풀림 · 반대 방향)",
     "낡음": "nrl.flow_sum에는 낡음 검사 없음(FLOW_STALE은 final_group.flow_before 것) — 간격 분포는 C"}
out = {"판정": "완전한 감사" if not ERR else "불완전 감사(오류 있음)", "오류 수": len(ERR), "오류 앞 20": ERR[:20],
       "git 끝점(고정 나무 커밋 · 시각)": [TREE_REV, tree_time], "A 정정 흔적": A,
       "C 날별 자료 충족(inside 행 SINCE ~)": {"inside 행": len(inside), **dict(C),
                                         "마지막 관측일 ~ 판단 날 앞 거래일 간격(거래일 · 0 = 바로 앞날)": dict(gap),
                                         "엔진 FLOW에 없는 inside 종목 · 그중 수급 파일 있음": [len(eng_flow_missing), eng_flow_missing_with_file],
                                         "엔진 TARGETS에 없는 inside 종목 · 그중 목표가 줄 있음": [len(eng_tgt_missing), eng_tgt_missing_with_file],
                                         "다름 예": mismatch[:10],
                                         "남는 열린 문제": "당시 종목 집합 · 상폐 종목 누락 · flow_universe(시총 120위 이력) 미래 선택 — 파일 안 충족으로 풀리지 않음"},
       "D 결측 방향": D,
       "범위": "고정 나무 판(9743cb802) 위 정직 캐시 · git 기록은 끝점까지의 판(수집 뒤 바뀐 값) · git 시각은 실제 입수 시각 아님 · 손익 · 성과 출력 없음"}
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:6000])
