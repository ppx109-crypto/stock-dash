"""최근 며칠 일봉을 한투에 다시 물어 확정 값으로 바로잡기(사용자 2026-10-06 "원인파악하고 다시는 이런일 없도록 해").

원인(2026-10-06 확인 · research/probe_m15_close.py): 한투 기간별시세(FHKST03010100 · 시장 J=거래소)는 그날 밤 정리 전까지
'오늘' 줄 종가에 넥스트레이드(저녁 8시까지 거래) 값을 줍니다. 10-02 밤 22:28에 받은 일봉이 그래서
424종목 중 356종목 틀렸고(000250: 넥스트레이드 210,000 · 거래소 종가 207,000 = 야후 · 한투 1분봉 15:30),
연휴라 정리가 10-05 밤에야 되어 10-05 저녁 수집도 틀린 값을 그대로 받았습니다. 다른 날은 수집이 자정을 넘겨 끝나 우연히 맞았음.

그래서 장 시작 전(평일 07:05)에 최근 MAX_ROWS줄만 다시 물어, 다른 값을 확정 값으로 바꿉니다(새 날은 더하지 않음 —
그건 원래 수집기 몫). 그보다 오래된 날이 다르면 수정주가가 바뀐 것이라 건드리지 않고 셉니다(원래 수집기가 처음부터 다시 받음).
고치는 곳: price-data(종가) · kosdaq-data(시가 · 고가 · 저가 · 종가 · 거래량 · 거래대금) · investor-data(종가 칸).
바뀐 것이 있으면 fix-recent/last.json에 적고 종료 코드 0 · 출력 끝에 changed=1을 남깁니다(작업이 A그룹 · 1시간봉 후보를 다시 셈).
조회 전용(주문 없음) · 응답 본문 · 키는 찍지 않습니다.
python fix_recent_days.py [종목코드,...]
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis

KST = ZoneInfo("Asia/Seoul")
MAX_ROWS = int(os.getenv("FIX_MAX_ROWS", "5"))       # 최근 몇 줄까지 고칠지
TOL = 0.0005                                         # 이만큼(0.05%) 넘게 다르면 다름
PRICE, KOSDAQ, FLOW = Path("price-data"), Path("kosdaq-data"), Path("investor-data")
OUT = Path("fix-recent/last.json")
KQ_COLS = ("시가", "고가", "저가", "종가", "거래량", "거래대금")


def _load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(path, body):
    """원래 수집기와 같은 모양으로 씀(rows가 있으면 한 줄에 하루 · 없으면 한 줄)."""
    if "rows" in body:
        head = {k: v for k, v in body.items() if k != "rows"}
        lines = ",\n".join(json.dumps(r, ensure_ascii=False) for r in body["rows"])
        text = json.dumps(head, ensure_ascii=False)[:-1] + ', "rows": [\n' + lines + "\n]}\n"
    else:
        text = json.dumps(body, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")


def _diff(a, b):
    return a is None or b is None or abs(float(a) - float(b)) > max(abs(float(a)), abs(float(b))) * TOL


def fix_price(body, fresh):
    """price-data 한 종목 → (바꾼 [(날, 옛 값, 새 값)], 오래된 날이 다른가)."""
    rows = body.get("closes") or []
    tail = {str(d) for d, _ in rows[-MAX_ROWS:]}
    changed, older = [], False
    for i, (d, c) in enumerate(rows):
        d = str(d)
        if d not in fresh or not _diff(c, fresh[d]["종가"]):
            continue
        if d in tail:
            changed.append((d, c, fresh[d]["종가"]))
            rows[i] = [d, fresh[d]["종가"]]
        else:
            older = True
    return changed, older


def fix_kosdaq(body, fresh):
    cols = body.get("cols") or []
    idx = {name: cols.index(name) for name in KQ_COLS if name in cols}
    rows = body.get("rows") or []
    tail = {str(r[0]) for r in rows[-MAX_ROWS:]}
    changed = []
    for r in rows:
        d = str(r[0])
        if d not in tail or d not in fresh:
            continue
        new = fresh[d]
        if any(name in new and _diff(r[i], new[name]) for name, i in idx.items()):
            changed.append((d, r[idx["종가"]] if "종가" in idx else None, new.get("종가")))
            for name, i in idx.items():
                if name in new:
                    r[i] = new[name]
    return changed


def fix_flow(body, fresh):
    cols = body.get("cols") or []
    if "종가" not in cols:
        return []
    i = cols.index("종가")
    rows = body.get("rows") or []
    tail = {str(r[0]) for r in rows[-MAX_ROWS:]}
    changed = []
    for r in rows:
        d = str(r[0])
        if d in tail and d in fresh and _diff(r[i], fresh[d]["종가"]):
            changed.append((d, r[i], fresh[d]["종가"]))
            r[i] = fresh[d]["종가"]
    return changed


def main(codes=None):
    now = datetime.now(KST)
    start, end = (now - timedelta(days=20)).strftime("%Y%m%d"), now.strftime("%Y%m%d")
    files = {}
    for home in (PRICE, KOSDAQ, FLOW):
        for p in sorted(home.glob("*.json")):
            if p.stem.isdigit() and len(p.stem) == 6 and (not codes or p.stem in codes):
                files.setdefault(p.stem, []).append(p)
    try:
        client = broker_kis.market()
    except broker_kis.BrokerError as e:
        print("증권사 연결을 만들지 못했습니다 ·", e)
        return 1

    def ask(code):
        try:
            return code, {d: g for d, g in client.daily(code, start, end, detail=True)}
        except broker_kis.BrokerError as e:
            return code, e

    report = {"at": now.strftime("%Y-%m-%d %H:%M"), "price-data": {}, "kosdaq-data": {}, "investor-data": {},
              "오래된 날 다름(수정주가 · 원래 수집기 몫)": [], "못 물음": 0}
    lanes = max(1, int(os.getenv("FIX_LANES", "4")))
    with concurrent.futures.ThreadPoolExecutor(lanes) as pool:
        for code, fresh in pool.map(ask, sorted(files)):
            if isinstance(fresh, Exception) or not fresh:
                report["못 물음"] += 1
                continue
            for p in files[code]:
                body = _load(p)
                if not body:
                    continue
                if p.parent == PRICE:
                    changed, older = fix_price(body, fresh)
                    if older:
                        report["오래된 날 다름(수정주가 · 원래 수집기 몫)"].append(code)
                elif p.parent == KOSDAQ:
                    changed = fix_kosdaq(body, fresh)
                else:
                    changed = fix_flow(body, fresh)
                if changed:
                    _write(p, body)
                    report[p.parent.name][code] = changed
    n = {k: len(report[k]) for k in ("price-data", "kosdaq-data", "investor-data")}
    days = sorted({d for k in n for ch in report[k].values() for d, *_ in ch})
    print(f"최근 {MAX_ROWS}줄 다시 확인 · 고친 종목 {n} · 고친 날 {days} · 못 물음 {report['못 물음']}"
          f" · 오래된 날 다름 {len(report['오래된 날 다름(수정주가 · 원래 수집기 몫)'])}종목")
    for k in n:
        for code, ch in list(report[k].items())[:3]:
            print(f"  {k} {code}: " + " ".join(f"{d} {a}→{b}" for d, a, b in ch))
    if any(n.values()):
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        gh = os.getenv("GITHUB_OUTPUT")
        if gh:
            with open(gh, "a") as f:
                f.write("changed=1\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1].split(",") if len(sys.argv) > 1 else None))
