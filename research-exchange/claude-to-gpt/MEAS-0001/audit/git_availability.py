"""MEAS-0001 B — git 이력으로 본 '그 날짜 줄이 저장소에 처음 들어온 시각'(received_at 대용 · 커밋 시각) 감사.
git 객체만 읽음(운영 코드 import · 실행 없음 · 네트워크 없음). python git_availability.py <저장소> <스냅샷 커밋> <out.json>"""
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

REPO, SNAP, OUT = sys.argv[1:4]
KST = timezone(timedelta(hours=9))


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, check=True).stdout


def history(path):
    rows = [l.split(" ", 1) for l in git("log", "--reverse", "--format=%H %cI", SNAP, "--", path).splitlines()]
    return [(h, datetime.fromisoformat(t).astimezone(KST)) for h, t in rows]


def load(h, path):
    try:
        return json.loads(git("show", f"{h}:{path}"))
    except subprocess.CalledProcessError:
        return None


def rows_of(body, kind):
    if body is None:
        return {}
    if kind == "investor":
        return {str(r[0]): r[1:] for r in body.get("rows") or [] if isinstance(r, list) and r}
    if kind == "price":
        return {str(d): c for d, c in body.get("closes") or []}
    if kind == "event":
        return {f'{r.get("date")}|{r.get("kind")}|{r.get("title", "")[:40]}': r.get("date") for r in body.get("rows") or [] if isinstance(r, dict)}
    return {}


FIRST = {}


def first_seen(path, kind):
    """{key: 첫 등장 시각} · {key: [값이 바뀐 시각들]} — 파일 첫 커밋(과거를 한꺼번에 채운 백필)에 있던 줄은 FIRST로 따로 표시."""
    seen, val, changes = {}, {}, defaultdict(list)
    hist = history(path)
    FIRST[path] = hist[0][1] if hist else None
    for h, t in hist:
        rows = rows_of(load(h, path), kind)
        for k, v in rows.items():
            if k not in seen:
                seen[k] = t
                val[k] = json.dumps(v, sort_keys=True, ensure_ascii=False)
            else:
                s = json.dumps(v, sort_keys=True, ensure_ascii=False)
                if s != val[k]:
                    changes[k].append(t)
                    val[k] = s
    return seen, changes


def trading_next(d, cal):
    i = cal.index(d) if d in cal else None
    return cal[i + 1] if i is not None and i + 1 < len(cal) else None


idx = load(SNAP, "market-data/index_KOSPI.json")
cal = sorted(str(r["date"]) for r in (idx or {}).get("rows", []) if r.get("종가"))
out = {"snapshot": SNAP, "repo_history_start": git("log", "--reverse", "--format=%cI", SNAP).splitlines()[0], "investor": {}, "price": {}, "event": {}}
codes = sorted(p.split("/")[1][:-5] for p in git("ls-tree", "-r", "--name-only", SNAP, "investor-data").splitlines() if p.endswith(".json"))
SAMPLE = codes[::10]                       # 10개마다 1개(미리 고정 · 결과 보고 바꾸지 않음)
# 1) 수급: D 줄이 처음 들어온 시각 vs 그 줄을 쓰는 첫 판단(D+1 거래일 15:20 · 1일봉)
inv = []
for c in SAMPLE:
    seen, ch = first_seen(f"investor-data/{c}.json", "investor")
    f0 = FIRST[f"investor-data/{c}.json"]
    for d, t in seen.items():
        if f0 is None or d <= f0.strftime("%Y%m%d"):       # 첫 커밋 날짜까지는 백필 → 수신 시각을 알 수 없음
            continue
        nx = trading_next(d, cal)
        dec = datetime.strptime(nx + "1520", "%Y%m%d%H%M").replace(tzinfo=KST) if nx else None
        inv.append({"code": c, "date": d, "first_seen_kst": t.isoformat(), "decision_D+1_1520": dec.isoformat() if dec else None,
                    "available_before_decision": (t <= dec) if dec else None, "later_changes": len(ch.get(d, []))})
out["file_first_commit_kst"] = {k: (v.isoformat() if v else None) for k, v in FIRST.items()}
out["investor"] = {"sample_codes": len(SAMPLE), "rows": inv,
                   "summary": {"rows": len(inv), "available_before_D+1_1520": sum(1 for r in inv if r["available_before_decision"]),
                               "not_available_before_D+1_1520": sum(1 for r in inv if r["available_before_decision"] is False),
                               "no_next_trading_day_yet": sum(1 for r in inv if r["available_before_decision"] is None),
                               "rows_later_changed": sum(1 for r in inv if r["later_changes"])}}
# 2) 종가: D 종가가 처음 들어온 시각 · 뒤에 바뀐 횟수(교정 · 수정주가)
prc = []
for c in SAMPLE:
    seen, ch = first_seen(f"price-data/{c}.json", "price")
    f0 = FIRST[f"price-data/{c}.json"]
    for d, t in seen.items():
        if f0 is None or d <= f0.strftime("%Y%m%d"):
            continue
        prc.append({"code": c, "date": d, "first_seen_kst": t.isoformat(), "same_day_evening": t.date().isoformat() == f"{d[:4]}-{d[4:6]}-{d[6:]}",
                    "later_changes": len(ch.get(d, [])), "last_change_kst": ch[d][-1].isoformat() if ch.get(d) else None})
out["price"] = {"rows": prc, "summary": {"rows": len(prc), "first_seen_same_day": sum(r["same_day_evening"] for r in prc),
                                         "later_changed": sum(1 for r in prc if r["later_changes"])}}
# 3) 공시: 사건이 처음 들어온 시각 vs 바구니 판단(접수일 다음 거래일 15:10)
ev = []
for c in SAMPLE:
    seen, _ = first_seen(f"event-data/{c}.json", "event")
    for k, t in seen.items():
        d = k.split("|")[0]
        f0 = FIRST[f"event-data/{c}.json"]
        if f0 is None or d <= f0.strftime("%Y%m%d"):
            continue
        nx = next((x for x in cal if x > d), None)
        dec = datetime.strptime(nx + "1510", "%Y%m%d%H%M").replace(tzinfo=KST) if nx else None
        ev.append({"code": c, "rcept_dt": d, "kind": k.split("|")[1], "first_seen_kst": t.isoformat(),
                   "available_before_next_1510": (t <= dec) if dec else None})
out["event"] = {"rows": ev, "summary": {"rows": len(ev), "available_before_next_1510": sum(1 for r in ev if r["available_before_next_1510"]),
                                        "late": sum(1 for r in ev if r["available_before_next_1510"] is False)}}
open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({k: out[k]["summary"] for k in ("investor", "price", "event")}, ensure_ascii=False))
