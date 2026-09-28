"""A그룹 — 연구 89회차의 최종 조건으로 오늘 살 후보를 고릅니다.

한 계좌에서 두 갈래를 함께 굴리는 조건입니다(docs/RL-LOG.md 89회차).

  갈래 1 · 기본 규칙(rule.holds): 그날 시가총액 100등 안 · 변동성 아래 40% ·
          180일선 기울기 1.46 이상 · 60일 전보다 20% 이상.
          팔기: 종가 +10% 익절 · −5% 손절 · 최대 10거래일.
  갈래 2 · 정배열: 100등 안 · 단순이동평균 3>15>20>90>150>200 · 가장 짧은 선이
          가장 긴 선보다 19~53% 위 · 그날 100등 안 종목 가운데 50일선이 200일선
          위인 몫(시장 폭)이 50% 이상.
          팔기: 정배열이 깨지는 날 종가 · −8% 손절 · 최대 60거래일.
  공통(97회차 · 스승님 수급 조건): 전날까지 5거래일 합으로 외국인 순매수 · 투신 순매수 ·
        개인 순매도. 수급은 장 마감 뒤에 나오므로 그날 것은 쓰지 않습니다(investor-data).
  자리: 최대 5종목(한 종목에 계좌의 1/5) · 하루 2종목까지 · 후보가 많으면
        180일선 기울기가 가파른 순.

연구용 표(features.json)는 앞날 수익이 있는 날까지만 있어 마지막 5거래일이
빠집니다. 여기서는 앞날 없이 그날까지의 종가만으로 다시 셉니다. 메모리를
아끼려고 종목을 나눠 굽고, 마지막 날 줄과 변동성 값만 남깁니다.

매수·매도 신호가 아닙니다. 지나간 자료로 고른 조건에 오늘 값을 대 본 것입니다.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import caps
import lab
import rule
import study

OUT = Path("study") / "a_group.json"
LINES = (3, 15, 20, 90, 150, 200)
SPREAD = (19.0, 53.0)
BREADTH = 50.0
SLOTS = 5
CONDITIONS = 5      # 갈래마다 조건 다섯: 시총 100위 안 + 그 갈래의 조건 셋 + 수급
FLOWS = Path("investor-data")
FLOW_DAYS = 5
FLOW_STALE = 10     # 수급의 마지막 날이 이보다 많이(달력 날) 앞이면 낡은 자료로 봅니다.
BATCH = 40
# 화면에 나가는 두 방식의 이름. 연구 기록에서는 '기본 규칙'·'정배열 갈래'라고 불렀습니다.
RULE_DOOR = "추세 규칙"
LINES_DOOR = "정배열 추세"


def sma(closes, span):
    """단순이동평균. 앞쪽 span−1일은 None입니다. (CI에 numpy를 깔지 않아 손으로 셉니다.)"""
    out, total = [None] * len(closes), 0.0
    for k, close in enumerate(closes):
        total += close
        if k >= span:
            total -= closes[k - span]
        if k >= span - 1:
            out[k] = total / span
    return out


def lines_now(closes):
    """마지막 날의 정배열 여부 · 된 지 며칠 · 간격 · 50일선>200일선."""
    if len(closes) < max(LINES) + 50:
        return None
    means = {span: sma(closes, span) for span in sorted(set(LINES) | {50})}

    def aligned(k):
        return all(means[a][k] is not None and means[b][k] is not None and means[a][k] > means[b][k]
                   for a, b in zip(LINES, LINES[1:]))

    last = len(closes) - 1
    run = 0
    while last - run >= 0 and aligned(last - run):
        run += 1
    return {"정배열": aligned(last), "된 지": run,
            "간격": (means[LINES[0]][last] / means[LINES[-1]][last] - 1) * 100,
            "50>200": means[50][last] > means[200][last]}


NAMES = Path("study") / "names.json"
CORP_CODES = "https://opendart.fss.or.kr/api/corpCode.xml"


def names_for(codes, prices=None):
    """종목 이름. 일봉 파일 → 조사 자료(public-data) → 저장해 둔 이름표 → DART 순으로 채웁니다.

    일봉 파일 가운데 300여 종목은 이름 칸에 코드가 들어 있습니다. DART 기업 목록은
    인증키(DART_CRTFC_KEY)가 있을 때만 받고, 받은 이름은 study/names.json에 남겨
    다음에는 키 없이도 씁니다. 인증키와 응답 본문은 어디에도 적지 않습니다.
    """
    import os
    found = {}
    for code in codes:
        name = ((prices or {}).get(code) or {}).get("name")
        if name and name != code:
            found[code] = name
    for code in codes:
        if code not in found:
            try:
                name = json.loads((Path("public-data") / f"{code}.json").read_text(encoding="utf-8")).get("name")
            except (OSError, ValueError):
                name = None
            if name:
                found[code] = name
    try:
        kept = json.loads(NAMES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        kept = {}
    for code in codes:
        if code not in found and kept.get(code):
            found[code] = kept[code]
    key = os.getenv("DART_CRTFC_KEY", "").strip()
    if key and any(code not in found for code in codes):
        dart = _dart_names(key)
        for code in codes:
            if code not in found and dart.get(code):
                found[code] = dart[code]
        kept.update({code: found[code] for code in codes if code in found})
        NAMES.parent.mkdir(exist_ok=True)
        NAMES.write_text(json.dumps(dict(sorted(kept.items())), ensure_ascii=False, indent=0), encoding="utf-8")
    return found


def _dart_names(key):
    """DART 기업 목록(corpCode.xml)에서 종목코드→회사명. 실패하면 빈 사전입니다."""
    import io
    import urllib.parse
    import urllib.request
    import zipfile
    from xml.etree import ElementTree
    try:
        with urllib.request.urlopen(CORP_CODES + "?" + urllib.parse.urlencode({"crtfc_key": key}),
                                    timeout=60) as reply:
            raw = reply.read()
        with zipfile.ZipFile(io.BytesIO(raw)) as box:
            root = ElementTree.fromstring(box.read(box.namelist()[0]))
    except Exception:           # 응답 본문에 계정 정보가 섞일 수 있어 그대로 적지 않습니다.
        print("DART 기업 목록을 받지 못했습니다 · 이름은 코드로 둡니다")
        return {}
    return {(one.findtext("stock_code") or "").strip(): (one.findtext("corp_name") or "").strip()
            for one in root.findall("list") if (one.findtext("stock_code") or "").strip()}


def compute(prices=None):
    """오늘(마지막 종가 날) A그룹을 셉니다."""
    prices = prices if prices is not None else study.load_prices()
    codes = sorted(prices)
    vols, latest = [], []
    for start in range(0, len(codes), BATCH):
        part = {code: prices[code] for code in codes[start:start + BATCH]}
        rows = lab.build(part, horizons=(0,))
        vols.extend(r["변동성"] for r in rows if r.get("변동성") is not None)
        last = {}
        for row in rows:
            if row["code"] not in last or row["date"] > last[row["code"]]["date"]:
                last[row["code"]] = row
        latest.extend(last.values())
        del rows
    if not latest:
        return {"date": None, "picks": [], "note": "일봉이 없습니다."}
    vols.sort()
    # rule.calm_edge와 같은 셈입니다(표 전체 변동성의 아래 CALM 자리).
    rule._calm = vols[int(len(vols) * rule.CALM)]
    day = max(row["date"] for row in latest)
    today = [row for row in latest if row["date"] == day]
    caps.tag(today, rule.TOP)
    shape = {row["code"]: lines_now([c for _, c in prices[row["code"]]["rows"]][:row["i"] + 1])
             for row in today}
    inside = [row for row in today if caps.inside(row, rule.TOP) and shape.get(row["code"])]
    breadth = (sum(shape[row["code"]]["50>200"] for row in inside) / len(inside) * 100
               if inside else 0.0)
    align_open = breadth >= BREADTH
    names = names_for([row["code"] for row in today], prices)
    picks, b_group, rest, far = [], [], 0, {}
    for row in today:
        form = shape.get(row["code"]) or {}
        entry = {"code": row["code"], "name": names.get(row["code"], row["code"]),
                 "시총순위": row.get(caps.RANK),
                 "추세 기울기": _round(row.get("추세 기울기")),
                 "60일 전 대비": _round(row.get("60일 전 대비")),
                 "변동성": _round(row.get("변동성")),
                 "정배열": form.get("정배열"), "정배열 된 지": form.get("된 지"),
                 "선 간격": _round(form.get("간격")), "종가": row.get("price")}
        flow = flow_before(flow_rows(row["code"]), day)
        entry["수급 5일"] = flow
        missing = shortfalls(row, form, breadth, rule._calm, flow)
        doors = [door for door, gaps in missing.items() if not gaps]
        if doors:
            picks.append({**entry, "갈래": doors,
                          "팔기": "종가 +10% 익절 · −5% 손절 · 최대 10거래일" if doors[0] == RULE_DOOR
                          else "정배열이 깨지는 날 종가 · −8% 손절 · 최대 60거래일"})
            continue
        fewest = min(len(gaps) for gaps in missing.values())
        doors_near = [door for door, gaps in missing.items() if len(gaps) == fewest]
        comment = " / ".join(f"{door}까지 {fewest}개 모자람: " + ", ".join(missing[door])
                             for door in doors_near)
        if fewest <= 2:
            b_group.append({**entry, "가까운 갈래": doors_near, "모자란 수": fewest,
                            "모자란 것": {door: missing[door] for door in doors_near},
                            "코멘트": comment})
        else:
            # 판에는 싣지 않지만, 종목을 골라 자세히 볼 때 무엇이 모자란지 보여 줍니다.
            far[row["code"]] = {"모자란 수": fewest, "코멘트": comment}
            rest += 1
    picks.sort(key=lambda one: -(one.get("추세 기울기") or -99))
    b_group.sort(key=lambda one: (one["모자란 수"], -(one.get("추세 기울기") or -99)))
    return {"date": day, "breadth": round(breadth, 1), "align_open": align_open,
            "calm_edge": round(rule._calm, 3), "slots": SLOTS, "picks": picks, "b_group": b_group,
            "rest": rest, "far": far, "counted": sorted(row["code"] for row in today), "made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")}


def flow_rows(code, folder=FLOWS):
    """한 종목의 날짜별 수급(오래된 날이 먼저). 없으면 빈 목록."""
    try:
        body = json.loads((folder / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    cols = body.get("cols") or []
    return [dict(zip(cols, one)) for one in body.get("rows") or []]


def flow_before(rows, day, days=FLOW_DAYS):
    """그날 **전날까지** days거래일의 외국인·투신·개인 순매수 합. 모자라거나 낡으면 None."""
    before = [r for r in rows if r.get("date", "") < day][-days:]
    if len(before) < days:
        return None
    if any(r.get(k) is None for r in before for k in ("외국인", "투신", "개인")):
        return None
    last = datetime.strptime(before[-1]["date"], "%Y%m%d")
    if (datetime.strptime(day, "%Y%m%d") - last).days > FLOW_STALE:
        return None
    return {"외국인": sum(r["외국인"] for r in before), "투신": sum(r["투신"] for r in before),
            "개인": sum(r["개인"] for r in before), "끝날": before[-1]["date"]}


def flow_gap(flow):
    """수급 조건을 못 채웠으면 그 까닭 한 줄, 채웠으면 None."""
    if flow is None:
        return f"수급 자료 없음 (외국인·투신 {FLOW_DAYS}일 순매수, 개인 순매도여야 함)"
    if flow["외국인"] > 0 and flow["투신"] > 0 and flow["개인"] < 0:
        return None
    return (f"{FLOW_DAYS}일 수급 외국인 {flow['외국인']:+,.0f} · 투신 {flow['투신']:+,.0f} · "
            f"개인 {flow['개인']:+,.0f}주 (외국인·투신 순매수, 개인 순매도여야 함)")


def shortfalls(row, form, breadth, calm_edge, flow=None):
    """갈래마다 오늘 못 채운 조건을 사람이 읽을 말로 돌려줍니다. 빈 목록이면 채운 것입니다."""
    place = row.get(caps.RANK)
    rank_gap = ([] if place is not None and place <= rule.TOP
                else [f"시총 {place}위 (100위 안이어야 함)" if place else "시총 순위 모름"])
    vol, slope, sixty = row.get("변동성"), row.get("추세 기울기"), row.get("60일 전 대비")
    by_rule = list(rank_gap)
    if vol is None or vol > calm_edge:
        by_rule.append(f"주가 흔들림 {_text(vol)} (조용함 문턱 {calm_edge:.2f} 이하여야 함)")
    if slope is None or slope < rule.SLOPE:
        by_rule.append(f"180일선 기울기 {_text(slope)} ({rule.SLOPE:g} 이상이어야 함)")
    if sixty is None or sixty < rule.SIXTY:
        by_rule.append(f"60일 상승 {_text(sixty, '%')} ({rule.SIXTY:g}% 이상이어야 함)")
    by_lines = list(rank_gap)
    if not form:
        by_lines.append("상장 기간이 짧아 정배열을 셀 수 없음")
    else:
        if not form.get("정배열"):
            by_lines.append("단순이동평균 3>15>20>90>150>200 정배열 아님")
        gap = form.get("간격")
        if gap is None or not SPREAD[0] <= gap < SPREAD[1]:
            by_lines.append(f"선 간격 {_text(gap, '%', 0)} ({SPREAD[0]:g}~{SPREAD[1]:g}%여야 함)")
    if breadth < BREADTH:
        by_lines.append(f"시장 폭 {breadth:.0f}% ({BREADTH:g}% 이상이어야 함)")
    # 두 갈래 공통: 외국인·투신이 사고 개인이 판 추세만 삽니다(97회차).
    gap = flow_gap(flow)
    if gap:
        by_rule.append(gap)
        by_lines.append(gap)
    return {RULE_DOOR: by_rule, LINES_DOOR: by_lines}


def _text(value, unit="", places=2):
    return "모름" if value is None else f"{value:.{places}f}{unit}"


def _round(value, places=2):
    return round(value, places) if isinstance(value, (int, float)) else None


def save(found, path=OUT):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")


def load(path=OUT):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def regroup(graded, found):
    """관심종목 그룹판을 최종 조건으로 다시 나눕니다.

    오늘 A그룹 목록에 있으면 A, 조건이 1~2개 모자라면 B(무엇이 모자란지 코멘트),
    그 밖(3개 이상 모자람)은 '밖'으로 두어 판에 싣지 않습니다. 조사 대상 507종목
    밖이라 셀 수 없는 종목은 그룹 없이 '판정 보류'로 남깁니다.
    """
    found = found or {}
    chosen = {one["code"]: one for one in found.get("picks", [])}
    close = {one["code"]: one for one in found.get("b_group", [])}
    counted = chosen.keys() | close.keys() | set(found.get("counted", []))
    out = []
    for row in graded or []:
        code = row.get("code")
        if code in chosen:
            doors = "·".join(chosen[code].get("갈래") or [])
            out.append({**row, "group": "A", "reason": f"매수 후보 · {doors} 조건 충족",
                        "comment": f"{doors} 조건을 모두 채움"})
        elif code in close:
            out.append({**row, "group": "B", "reason": close[code]["코멘트"],
                        "comment": close[code]["코멘트"], "shortfall": close[code]["모자란 수"]})
        elif code in counted:
            far = (found.get("far") or {}).get(code) or {}
            out.append({**row, "group": "밖", "reason": "조건이 3개 이상 모자람",
                        "comment": far.get("코멘트"), "shortfall": far.get("모자란 수")})
        else:
            out.append({**row, "group": None,
                        "note": "조사 대상 507종목 밖이거나 시세가 없어 조건을 셀 수 없습니다"})
    return out


if __name__ == "__main__":
    got = compute()
    save(got)
    print(f'{got["date"]} · 시장 폭 {got.get("breadth")}% · A그룹 {len(got["picks"])}종목 · '
          f'B그룹 {len(got.get("b_group", []))}종목 · 그 밖 {got.get("rest")}종목')
    for one in got["picks"]:
        print(f'  {one["name"]}({one["code"]}) · {"·".join(one["갈래"])} · 시총 {one["시총순위"]}등')
