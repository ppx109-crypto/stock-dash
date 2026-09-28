"""A그룹 — 연구 89회차의 최종 조건으로 오늘 살 후보를 고릅니다.

한 계좌에서 두 갈래를 함께 굴리는 조건입니다(docs/RL-LOG.md 89회차).

  갈래 1 · 기본 규칙(rule.holds): 그날 시가총액 100등 안 · 변동성 아래 40% ·
          180일선 기울기 1.46 이상 · 60일 전보다 20% 이상.
          팔기: 종가 +10% 익절 · −5% 손절 · 최대 10거래일.
  갈래 2 · 정배열: 100등 안 · 단순이동평균 3>15>20>90>150>200 · 가장 짧은 선이
          가장 긴 선보다 19~53% 위 · 그날 100등 안 종목 가운데 50일선이 200일선
          위인 몫(시장 폭)이 50% 이상.
          팔기: 정배열이 깨지는 날 종가 · −8% 손절 · 최대 60거래일.
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
BATCH = 40


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
    picks, near = [], []
    for row in today:
        form = shape.get(row["code"]) or {}
        by_rule = rule.holds(row)
        by_lines = (caps.inside(row, rule.TOP) and bool(form.get("정배열"))
                    and SPREAD[0] <= form.get("간격", -1) < SPREAD[1])
        doors = (["기본 규칙"] if by_rule else []) + (["정배열"] if by_lines and align_open else [])
        entry = {"code": row["code"], "name": prices[row["code"]].get("name") or row["code"],
                 "시총순위": row.get(caps.RANK),
                 "추세 기울기": _round(row.get("추세 기울기")),
                 "60일 전 대비": _round(row.get("60일 전 대비")),
                 "변동성": _round(row.get("변동성")),
                 "정배열": form.get("정배열"), "정배열 된 지": form.get("된 지"),
                 "선 간격": _round(form.get("간격")), "종가": row.get("price")}
        if doors:
            picks.append({**entry, "갈래": doors,
                          "팔기": "종가 +10% 익절 · −5% 손절 · 최대 10거래일" if doors[0] == "기본 규칙"
                          else "정배열이 깨지는 날 종가 · −8% 손절 · 최대 60거래일"})
        elif by_lines and not align_open:
            near.append({**entry, "모자란 것": f"시장 폭 {breadth:.0f}% (50% 이상일 때만 삼)"})
    picks.sort(key=lambda one: -(one.get("추세 기울기") or -99))
    near.sort(key=lambda one: -(one.get("추세 기울기") or -99))
    return {"date": day, "breadth": round(breadth, 1), "align_open": align_open,
            "calm_edge": round(rule._calm, 3), "slots": SLOTS, "picks": picks, "near": near,
            "made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")}


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

    오늘 A그룹 목록에 있으면 A, 아니면 예전 이평선 판정에서 A였던 것도 B(보류)로,
    B·C는 그대로 둡니다. 판정하지 못한 종목(그룹 없음)은 건드리지 않습니다.
    """
    chosen = {one["code"]: one for one in (found or {}).get("picks", [])}
    out = []
    for row in graded or []:
        group = row.get("group")
        if group is None:
            out.append(row)
        elif row.get("code") in chosen:
            doors = "·".join(chosen[row["code"]].get("갈래") or [])
            out.append({**row, "group": "A", "reason": f"매수 후보 · 최종 조건 충족({doors})"})
        elif group == "A":
            out.append({**row, "group": "B",
                        "reason": "투자보류 · 이평선은 모두 위이나 최종 조건 미충족"})
        else:
            out.append(row)
    return out


if __name__ == "__main__":
    got = compute()
    save(got)
    print(f'{got["date"]} · 시장 폭 {got.get("breadth")}% · A그룹 {len(got["picks"])}종목 · '
          f'시장 폭만 모자란 정배열 {len(got.get("near", []))}종목')
    for one in got["picks"]:
        print(f'  {one["name"]}({one["code"]}) · {"·".join(one["갈래"])} · 시총 {one["시총순위"]}등')
