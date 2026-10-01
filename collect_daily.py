"""장 마감 뒤 하루 한 번, 모아 둔 종목의 DART 자료를 다시 받습니다.

받을 종목은 public-data에 이미 있는 종목입니다. PUBLIC_CODES로 직접 지정할 수도
있습니다. DART 한 번에 묻는 수를 25개로 제한하고 있어, 나눠서 차례로 받습니다.

내용이 달라지지 않은 파일은 다시 쓰지 않습니다. 수집일(fetched)만 바뀐 파일까지
저장하면 매일 커밋이 생기고, 커밋할 때마다 Streamlit이 다시 시작돼 저장해 둔
관심종목과 투자일지가 지워집니다. 실제로 바뀐 것이 있을 때만 남깁니다.
"""
import json
import os
import re
import time
from datetime import date, timedelta
from pathlib import Path

from collect_public_dart import FIRST_YEAR as FIRST_YEAR_DEFAULT, Official, collect

CHUNK = 25
FOLDER = Path("public-data")


def stored_codes():
    """받을 종목. 대상 목록이 있으면 그것을 먼저 봅니다."""
    try:
        chosen = json.loads(Path("universe.json").read_text(encoding="utf-8"))
        picked = [str(c) for c in chosen.get("codes", [])
                  if re.fullmatch(r"[0-9]{6}", str(c))]
        if picked:
            return picked
    except (OSError, ValueError):
        pass
    return sorted(p.stem for p in FOLDER.glob("*.json")
                  if re.fullmatch(r"[0-9]{6}", p.stem))


def same_apart_from_fetched(old, new):
    """수집일만 다르고 내용이 같은지 봅니다."""
    return {k: v for k, v in old.items() if k != "fetched"} == \
           {k: v for k, v in new.items() if k != "fetched"}


def already_done(code, first_year, on_day):
    """오늘 이미 그 깊이까지 받아 둔 종목인지 봅니다.

    시간이 모자라 도중에 끊긴 뒤 다시 돌릴 때, 끝난 종목을 또 받으면 남은
    시간이 그대로 사라집니다. 받아 둔 깊이와 날짜가 맞을 때만 건너뜁니다.
    """
    try:
        kept = json.loads((FOLDER / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if kept.get("fetched") != on_day:
        return False
    # 표시가 있으면 그 깊이로 판단합니다. 표시를 남기기 전에 받아 둔 파일도
    # 오늘 받은 것이라면 이미 같은 깊이로 물어본 것이므로 건너뜁니다. 그
    # 종목에 결산이 세 해치뿐이어서 세 개만 온 경우도 여기에 들어갑니다.
    return kept.get("since") in (first_year, None)


# ── 빠른 하루치 갱신(2026-10-01) ─────────────────────────────────────────
# 예전에는 매일 모든 종목을 처음부터 다시 받았습니다(종목마다 결산 · 반기 스무 번 넘게 +
# 사업보고서 원문 수십 MB). 하루 60종목쯤에서 6시간 제한에 걸려 멈추고, 그 뒤 일봉 · A그룹
# 계산이 새벽 3시까지 밀렸습니다. 지난 결산은 바뀌지 않으므로 이제는
#   1) 그사이 올라온 시장 전체 공시 목록을 한 번에 받아(100줄씩 몇십 번) 종목마다 붙이고,
#   2) 정기보고서(사업 · 반기 · 분기)가 새로 나온 종목, 파일이 없는 종목, 오래된 종목,
#      그리고 돌아가며 하루 1/28만 처음부터 다시 받습니다(4갈래로 나눠 동시에).
#   3) 사업보고서 원문은 마지막 결산 접수번호가 그대로면 전에 받은 것을 씁니다.
PERIODIC = ("사업보고서", "반기보고서", "분기보고서")
WINDOW = 89          # 시장 전체 공시 목록은 석 달까지만 한 번에 물을 수 있음
ROTATE = 28          # 이 날수에 한 번은 모든 종목을 처음부터 다시 받음
LANES = int(os.getenv("PUBLIC_LANES", "4"))
DEADLINE_MIN = float(os.getenv("PUBLIC_DEADLINE_MIN", "150"))


def market_list(p, begin, end):
    """begin~end(YYYYMMDD) 시장 전체 공시 목록. 종목코드가 있는 줄만."""
    rows, page = [], 1
    while True:
        got = p.dart("list.json", bgn_de=begin, end_de=end, page_count=100, page_no=page) or {}
        rows += [r for r in got.get("list", []) if str(r.get("stock_code") or "").strip()]
        if page >= int(got.get("total_page") or 1):
            return rows
        page += 1


def notice(r):
    return {"title": r.get("report_nm", ""), "date": r.get("rcept_dt", ""),
            "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + str(r.get("rcept_no", ""))}


def merged_disclosures(old, rows, today):
    """전에 받아 둔 공시 + 새 공시 → 최근 90일 · 새것 먼저 · 30건까지(처음부터 받을 때와 같은 모양)."""
    floor = (today - timedelta(days=90)).strftime("%Y%m%d")
    seen, out = set(), []
    for d in [notice(r) for r in rows] + list(old or []):
        if d["url"] in seen or str(d.get("date", "")) < floor:
            continue
        seen.add(d["url"])
        out.append(d)
    return sorted(out, key=lambda d: d["date"], reverse=True)[:30]


def needs_full(code, kept, new_rows, today):
    """처음부터 다시 받을 까닭(없으면 빈 글)."""
    if not kept:
        return "파일 없음"
    if kept.get("since") not in (FIRST_YEAR_DEFAULT, None):
        return "받은 깊이 다름"
    try:
        fetched = date.fromisoformat(str(kept.get("fetched")))
    except ValueError:
        return "받은 날 모름"
    if (today - fetched).days >= WINDOW:
        return "오래됨"
    if any(any(k in str(r.get("report_nm", "")) for k in PERIODIC) for r in new_rows):
        return "정기보고서 새로 나옴"
    if int(code) % ROTATE == today.toordinal() % ROTATE:
        return "돌아가며 다시 받기"
    return ""


def _full(code, shared, kept):
    """처음부터 받되, 사업보고서 원문은 마지막 결산이 같으면 전 것을 씀."""
    os.environ["PUBLIC_WITH_EXCERPT"] = "0"
    data = collect(code, shared)
    receipt = (data.get("years") or [{}])[-1].get("receipt")
    if kept and (kept.get("years") or [{}])[-1].get("receipt") == receipt and kept.get("business_excerpt"):
        data["business_excerpt"] = kept["business_excerpt"]
    else:
        try:
            data["business_excerpt"] = shared.business_excerpt(receipt)
        except Exception:
            data["business_excerpt"] = ""
    return data


def _save(code, data, kept):
    """내용이 같으면 쓰지 않음. 바뀌었으면 True."""
    if kept and same_apart_from_fetched(kept, data):
        return False
    (FOLDER / f"{code}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def _kept(code):
    try:
        return json.loads((FOLDER / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run(codes=None, shared=None, today=None):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    codes = codes or stored_codes()
    if not codes:
        print("받을 종목이 없습니다.")
        return 0, 0, 0
    today = today or date.today()
    began = time.monotonic()
    FOLDER.mkdir(exist_ok=True)
    shared = shared or Official()
    kept = {c: _kept(c) for c in codes}
    if os.getenv("PUBLIC_SKIP_DONE", "1").strip() not in ("0", "false", "False"):
        done = [c for c in codes if kept[c] and kept[c].get("fetched") == today.isoformat()
                and kept[c].get("since") in (FIRST_YEAR_DEFAULT, None)]
        if done:
            print(f"오늘 이미 받아 둔 {len(done)}종목은 건너뜁니다.")
        codes = [c for c in codes if c not in set(done)]
        if not codes:
            print("모두 받아 두었습니다.")
            return 0, len(done), 0
    # 1) 시장 전체 공시 목록(가장 오래 전에 받은 날부터 오늘까지, 석 달 안)
    dates = [date.fromisoformat(k["fetched"]) for k in kept.values() if k and _is_day(k.get("fetched"))]
    begin = max([today - timedelta(days=WINDOW)] + [min(dates)] if dates else [today - timedelta(days=WINDOW)])
    rows = market_list(shared, begin.strftime("%Y%m%d"), today.strftime("%Y%m%d"))
    by_code = {}
    for r in rows:
        by_code.setdefault(str(r["stock_code"]).strip(), []).append(r)
    print(f"시장 공시 {len(rows)}건 · {begin} ~ {today}")
    # 2) 가벼운 갱신(공시만 붙임)과 처음부터 받을 종목 나누기
    changed, same, failed, full = 0, 0, 0, []
    for c in codes:
        k = kept[c]
        since = str(k.get("fetched", "")).replace("-", "") if k else ""
        fresh = [r for r in by_code.get(c, []) if str(r.get("rcept_dt", "")) >= since]
        why = needs_full(c, k, fresh, today)
        if why:
            full.append((c, why))
            continue
        data = dict(k, disclosures=merged_disclosures(k.get("disclosures"), fresh, today), fetched=today.isoformat())
        if _save(c, data, k):
            changed += 1
        else:
            same += 1
    order = {"정기보고서 새로 나옴": 0, "받은 깊이 다름": 1, "오래됨": 2, "받은 날 모름": 2, "돌아가며 다시 받기": 3, "파일 없음": 4}
    full.sort(key=lambda x: order.get(x[1], 5))
    print(f"공시만 붙인 종목 {changed + same} · 처음부터 받을 종목 {len(full)}")
    # 3) 처음부터 받기(여러 갈래 · 시간 넘으면 남은 것은 다음 날)
    if full:
        shared.corp(full[0][0])          # 종목코드 목록을 한 번만 받아 둠(갈래끼리 겹치지 않게)
    left = list(full)
    with ThreadPoolExecutor(max_workers=max(1, LANES)) as pool:
        jobs = {}
        while left or jobs:
            while left and len(jobs) < LANES and (time.monotonic() - began) / 60 < DEADLINE_MIN:
                c, why = left.pop(0)
                jobs[pool.submit(_full, c, shared, kept[c])] = (c, why)
            if not jobs:
                break
            fut = next(as_completed(jobs))
            c, why = jobs.pop(fut)
            try:
                data = fut.result()
            except Exception as error:
                failed += 1
                print(f"{c} 수집 실패 · 기존 파일 유지 · {str(error)[:60]}")
                continue
            if _save(c, data, kept[c]):
                changed += 1
                print(f"{c} 갱신 · {why}")
            else:
                same += 1
    if left:
        print(f"시간({DEADLINE_MIN:g}분)이 다 되어 {len(left)}종목은 다음 날로 넘깁니다.")
    print(f"갱신 {changed} · 변화 없음 {same} · 실패 {failed} · 대상 {len(codes)}종목 · {(time.monotonic() - began) / 60:.1f}분")
    return changed, same, failed


def _is_day(v):
    try:
        date.fromisoformat(str(v))
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    picked = [c.strip() for c in os.getenv("PUBLIC_CODES", "").split(",") if c.strip()]
    if picked and any(not re.fullmatch(r"[0-9]{6}", c) for c in picked):
        raise SystemExit("종목코드는 숫자 6자리여야 합니다.")
    changed, same, failed = run(picked or None)
    if changed:
        from build_research_bundle import build
        path, count = build()
        print(f"조사 파일 갱신 · {path} · {count}종목")
    else:
        print("바뀐 자료가 없어 조사 파일은 그대로 둡니다.")
    # 전부 실패했을 때만 실패로 끝냅니다.
    raise SystemExit(1 if failed and not changed and not same else 0)
