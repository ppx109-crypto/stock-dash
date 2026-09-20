"""PlanX 첫 화면 · 보태니컬 브리핑.

3열 그리드 하나로만 구성합니다. 시장 지수 스트립과 티커는 두지 않고,
카드마다 꽃 엠블럼을 달아 한 화면에 꼭 필요한 정보만 담습니다.

research/ 폴더에 조사 결과가 있으면 숫자와 문장은 실제 조사값으로 채우고,
없으면 라벨이 붙은 샘플로 화면 구성을 보여줍니다.
"""
from __future__ import annotations

from datetime import date
import html

import streamlit as st

from chat_research import growth

UP = "#C2503F"     # 국내 관례: 상승 = 빨강
DOWN = "#36699E"   # 하락 = 파랑
INK = "#2E2822"
GOLD = "#B08343"
SAMPLE = "샘플"

# (꽃잎 수, 꽃잎 색, 꽃술 색)
_BLOOMS = [
    (8, "#D9846F", "#F0C97D"),
    (6, "#7FA98B", "#E4D6A7"),
    (5, "#C9A24D", "#8C6B36"),
    (7, "#8C7BB0", "#EBD9B4"),
    (6, "#6F9BC4", "#F2DFA8"),
    (9, "#D4A0B4", "#E9CE8E"),
    (5, "#79A9A3", "#EBD7A4"),
    (8, "#C58B4E", "#F1D79C"),
    (6, "#A8836B", "#EAD5A6"),
]

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&display=swap');
@keyframes pxbRise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes pxbSway{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(4deg)}}

.pxb{font-family:Pretendard,"Noto Sans KR","Apple SD Gothic Neo",sans-serif;color:#2E2822;margin-bottom:8px}
.pxb *{box-sizing:border-box}

.pxb-top{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;flex-wrap:wrap;
  padding:6px 4px 20px;border-bottom:1px solid #E7DCC7}
.pxb-title em{display:block;font:600 40px/1.15 "Playfair Display",Georgia,serif;font-style:normal;
  letter-spacing:-.6px;color:#2E2822}
.pxb-title em i{font-style:normal;color:#B08343}
.pxb-title span{display:block;margin-top:9px;font-size:13px;color:#8A8271}
.pxb-meta{text-align:right;font-size:12px;color:#8A8271;line-height:1.9}
.pxb-meta b{display:block;font-size:11px;letter-spacing:.22em;color:#B08343}

.pxb-live{display:flex;align-items:stretch;gap:10px;overflow-x:auto;margin-top:18px;padding-bottom:2px}
.pxb-live-head{flex:none;display:flex;flex-direction:column;justify-content:center;padding-right:16px;
  border-right:1px solid #EDE3D2}
.pxb-live-head b{font-size:11px;font-weight:800;letter-spacing:.16em;color:#B08343;white-space:nowrap}
.pxb-live-head span{margin-top:5px;font-size:10.5px;color:#A39781;white-space:nowrap}
.pxb-live-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#7FA98B;margin-right:6px;
  animation:pxbPulse 1.8s ease-in-out infinite}
@keyframes pxbPulse{0%,100%{opacity:1}50%{opacity:.25}}
.pxb-quote{flex:none;min-width:132px;padding:12px 15px;border-radius:14px;background:linear-gradient(170deg,#FFFDF8,#FBF6EC);
  border:1px solid #EDE3D2;box-shadow:0 8px 20px rgba(90,72,44,.05)}
.pxb-quote span{display:block;font-size:11px;color:#8A8271;white-space:nowrap}
.pxb-live.mock .pxb-quote{background:linear-gradient(170deg,#FCFAF4,#F6F1E6);border-style:dashed}
.pxb-quote b{display:block;margin-top:6px;font:600 20px/1 "Playfair Display",Georgia,serif;letter-spacing:-.4px}
.pxb-quote em{display:block;margin-top:5px;font-style:normal;font-size:11px;font-weight:800}
.pxb-live-off{flex:1;display:flex;align-items:center;padding:14px 16px;border-radius:14px;border:1px dashed #E0D3B8;
  font-size:11.5px;color:#8A8271;background:rgba(255,255,255,.5)}
.pxb-board{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:20px}
.pxb-slot{position:relative;padding:18px 18px 16px;border-radius:18px;overflow:hidden;min-height:150px;
  border:1px solid #EDE3D2;background:linear-gradient(170deg,#FFFDF8,#FBF6EC);
  box-shadow:0 10px 26px rgba(90,72,44,.06);animation:pxbRise .5s ease both}
.pxb-slot.a{border-color:#BFD8C4;background:linear-gradient(170deg,#FBFEFB,#F1F7F0)}
.pxb-slot.c{border-color:#E2D6BD;background:linear-gradient(170deg,#FFFDF6,#F8F3E6)}
.pxb-slot.d{background:linear-gradient(170deg,#FEFCFA,#F7F2EE)}
.pxb-slot-h{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.pxb-slot-h b{font-size:13px;font-weight:800;letter-spacing:.02em;color:#2E2822}
.pxb-slot-h i{font-style:normal;font:600 22px "Playfair Display",Georgia,serif;color:#B08343}
.pxb-slot small{display:block;margin-top:6px;font-size:11px;color:#8A8271;line-height:1.55}
.pxb-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.pxb-chip{padding:4px 10px;border-radius:999px;font-size:11px;background:#FFFFFFAA;border:1px solid #E7DCC7;color:#5F584B}
.pxb-chip em{font-style:normal;color:#A39781;margin-left:4px;font-size:10px}
.pxb-slot.a .pxb-chip{border-color:#CFE2D2}
.pxb-empty{margin-top:12px;font-size:11px;color:#A39781}
.pxb-note{font-size:11px;color:#8A8271;line-height:1.6}
.pxb-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:18px}
.pxb-card{position:relative;overflow:hidden;padding:24px 24px 22px;border-radius:20px;min-height:208px;
  background:linear-gradient(170deg,#FFFDF8,#FBF6EC);border:1px solid #EDE3D2;
  box-shadow:0 14px 34px rgba(90,72,44,.07);animation:pxbRise .55s ease both;
  transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease}
.pxb-card:hover{transform:translateY(-4px);border-color:#E0CFA9;box-shadow:0 22px 46px rgba(90,72,44,.13)}
.pxb-card:nth-child(2){animation-delay:.05s}.pxb-card:nth-child(3){animation-delay:.1s}
.pxb-card:nth-child(4){animation-delay:.15s}.pxb-card:nth-child(5){animation-delay:.2s}
.pxb-card:nth-child(6){animation-delay:.25s}.pxb-card:nth-child(7){animation-delay:.3s}
.pxb-card:nth-child(8){animation-delay:.35s}.pxb-card:nth-child(9){animation-delay:.4s}

.pxb-bloom{position:absolute;top:18px;right:20px;width:46px;height:46px;opacity:.92;
  transform-origin:50% 50%;animation:pxbSway 7s ease-in-out infinite}
.pxb-card:nth-child(even) .pxb-bloom{animation-duration:9s}
.pxb-petal{position:absolute;right:-34px;bottom:-34px;width:150px;height:150px;opacity:.09;pointer-events:none}

.pxb-label{font-size:11px;font-weight:800;letter-spacing:.16em;color:#B08343}
.pxb-value{margin:14px 0 0;font:600 42px/1 "Playfair Display",Georgia,serif;letter-spacing:-1px}
.pxb-value small{font-size:16px;font-weight:600;margin-left:4px}
.pxb-sub{margin:11px 0 0;font-size:12.5px;line-height:1.7;color:#7C7361;max-width:78%}
.pxb-tag{display:inline-block;margin-top:14px;padding:4px 11px;border-radius:999px;font-size:10.5px;
  font-weight:800;letter-spacing:.04em}

.pxb-meter{margin-top:16px;display:flex;flex-direction:column;gap:9px}
.pxb-meter div{display:grid;grid-template-columns:60px 1fr 28px;align-items:center;gap:10px;
  font-size:11px;color:#8A8271}
.pxb-meter i{display:block;height:5px;border-radius:5px;background:#EFE7D8;overflow:hidden;font-style:normal}
.pxb-meter i u{display:block;height:100%;border-radius:5px;text-decoration:none;
  background:linear-gradient(90deg,#DCC08A,#B08343)}
.pxb-meter b{text-align:right;color:#2E2822;font-variant-numeric:tabular-nums}

.pxb-chart{display:block;width:100%;height:104px;margin-top:18px}
.pxb-chart.mini{height:62px;margin-top:20px;opacity:.95}
.pxb-chart text{fill:#A39781;font-size:9.5px}
.pxb-range{margin-top:26px}
.pxb-range-line{position:relative;height:7px;border-radius:7px;background:#EFE7D8}
.pxb-range-line u{position:absolute;top:0;bottom:0;border-radius:7px;text-decoration:none;
  background:linear-gradient(90deg,#CBD9C4,#7FA98B)}
.pxb-range-line i{position:absolute;top:-5px;width:17px;height:17px;margin-left:-8px;border-radius:50%;
  background:linear-gradient(140deg,#F3DFA9,#B08343);border:3px solid #FFFDF8;
  box-shadow:0 3px 8px rgba(90,72,44,.25)}
.pxb-range-lab{display:flex;justify-content:space-between;margin-top:10px;font-size:10px;color:#A39781}

.pxb-list{margin:16px 0 0;padding:0;list-style:none}
.pxb-list li{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 0;
  border-bottom:1px solid #F0E8D9;font-size:12px;color:#5F584B}
.pxb-list li:last-child{border-bottom:0}
.pxb-list b{font:600 13px Georgia,serif;color:#2E2822}
.pxb-list em{font-style:normal;font-weight:800;font-size:11.5px}
.pxb-notes{margin:16px 0 0;padding-left:16px}
.pxb-notes li{font-size:12px;line-height:1.85;color:#6B6353;margin-bottom:6px}
.pxb-pens{display:flex;gap:10px;margin-top:20px}
.pxb-pens i{width:22px;height:6px;border-radius:6px;transform:rotate(-40deg);background:#D9846F}
.pxb-pens i:nth-child(2){background:#6F9BC4}.pxb-pens i:nth-child(3){background:#7FA98B}
.pxb-pens i:nth-child(4){background:#C9A24D}

.px-live-divider{display:flex;align-items:center;gap:12px;margin:34px 0 8px;color:#80612f;
  font-size:11px;font-weight:800;letter-spacing:.08em}
.px-live-divider:before,.px-live-divider:after{content:"";height:1px;background:#d9cbb5;flex:1}

@media(max-width:1080px){.pxb-grid,.pxb-board{grid-template-columns:repeat(2,1fr)}}
@media(max-width:720px){
  .pxb-grid,.pxb-board{grid-template-columns:1fr;gap:14px}
  .pxb-title em{font-size:30px}
  .pxb-meta{text-align:left}
  .pxb-sub{max-width:100%}
}
</style>
"""


def _e(value) -> str:
    return html.escape(str(value))


def _bloom(index: int, size: int = 46, klass: str = "pxb-bloom") -> str:
    """꽃 엠블럼 하나를 SVG로 그립니다."""
    petals, petal, core = _BLOOMS[index % len(_BLOOMS)]
    leaves = "".join(
        f'<ellipse cx="24" cy="13.5" rx="5.6" ry="10.2" fill="{petal}" opacity=".62"'
        f' transform="rotate({360 / petals * i:.1f} 24 24)"/>'
        for i in range(petals)
    )
    return (
        f'<svg class="{klass}" width="{size}" height="{size}" viewBox="0 0 48 48">'
        f"{leaves}"
        f'<circle cx="24" cy="24" r="5.4" fill="{core}"/>'
        f'<circle cx="24" cy="24" r="2.2" fill="{petal}" opacity=".55"/></svg>'
    )


def _spark(values: list[float], color: str, key: str, mini: bool = False) -> str:
    w, h, pad = 300.0, (62.0 if mini else 104.0), (8.0 if mini else 14.0)
    low, high = min(values), max(values)
    span = (high - low) or 1
    step = w / max(len(values) - 1, 1)
    pts = [(i * step, pad + (h - pad * 2) * (1 - (v - low) / span)) for i, v in enumerate(values)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"M0,{h} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" L{w},{h} Z"
    tip_x, tip_y = pts[-1]
    return (
        f'<svg class="pxb-chart{" mini" if mini else ""}" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none">'
        f'<defs><linearGradient id="pxb{key}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{color}" stop-opacity=".3"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
        f'<path d="{area}" fill="url(#pxb{key})"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2.4"'
        f' stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{tip_x:.1f}" cy="{tip_y:.1f}" r="4" fill="{color}"/></svg>'
    )


def _bars(labels: list[str], revenue: list[float], profit: list[float]) -> str:
    w, h, base = 300.0, 104.0, 82.0
    slot = w / max(len(labels), 1)
    width = min(30.0, slot * 0.34)
    peak = max(revenue) or 1
    low_p, high_p = min(profit), max(profit)
    span_p = (high_p - low_p) or 1
    bars, dots, labs = "", [], ""
    for i, name in enumerate(labels):
        cx = slot * (i + 0.5)
        tall = revenue[i] / peak * (base - 12)
        bars += (f'<rect x="{cx - width / 2:.1f}" y="{base - tall:.1f}" width="{width:.1f}"'
                 f' height="{tall:.1f}" rx="5" fill="url(#pxbBar)"/>')
        dots.append((cx, base - ((profit[i] - low_p) / span_p * 0.5 + 0.3) * (base - 12)))
        labs += f'<text x="{cx:.1f}" y="{h - 4:.0f}" text-anchor="middle">{_e(name)}</text>'
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in dots)
    marks = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="{GOLD}"/>' for x, y in dots)
    return (
        f'<svg class="pxb-chart" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none">'
        '<defs><linearGradient id="pxbBar" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#9FBCD8"/><stop offset="1" stop-color="#D8E4EE"/></linearGradient></defs>'
        f'{bars}<polyline points="{poly}" fill="none" stroke="{GOLD}" stroke-width="2.2"/>{marks}{labs}</svg>'
    )


def _card(index: int, label: str, body: str, wide_bloom: bool = False) -> str:
    petal = _bloom(index + 3, 150, "pxb-petal") if wide_bloom else ""
    return (
        f'<div class="pxb-card">{_bloom(index)}{petal}'
        f'<div class="pxb-label">{_e(label)}</div>{body}</div>'
    )


def _score_of(reports: list[dict]) -> tuple[int, list[tuple[str, int]], str]:
    if not reports:
        return 78, [("매크로", 76), ("산업", 82), ("실적", 80), ("밸류", 70)], "관망 우위"

    def grade(current, prior, weight) -> int:
        if not prior or prior <= 0:
            return 50
        return int(min(max(50 + (current / prior - 1) * 100 * weight, 0), 100))

    money = [r["financial"] for r in reports if r.get("financial")]
    revenue = int(sum(grade(f["revenue"], f["prior_revenue"], 2.0) for f in money) / len(money)) if money else 50
    profit = int(sum(grade(f["operating_profit"], f["prior_operating_profit"], 1.0) for f in money) / len(money)) if money else 50
    # 종목이 늘수록 무조건 0이 되지 않도록 종목당 평균 확인필요 건수로 환산합니다.
    gaps = sum(len(r.get("data_gaps") or []) for r in reports) / len(reports)
    quality = int(min(max(100 - gaps * 12, 0), 100))
    peers = min(60 + sum(1 for r in reports if r.get("peers")) * 10, 100)
    rows = [("매출 성장", revenue), ("이익 성장", profit), ("경쟁 비교", peers), ("자료", quality)]
    verdict = "이익 성장 우위" if profit >= 70 else ("점검 필요" if profit < 45 else "중립 구간")
    return int(sum(v for _, v in rows) / len(rows)), rows, verdict


def _pct(current, prior) -> float | None:
    try:
        return (current / prior - 1) * 100 if prior and prior > 0 else None
    except TypeError:
        return None


def live_strip(live: dict | None) -> str:
    """관심종목 실시간 시세 줄. 연결 전에는 안내만 보여줍니다."""
    if not live:
        return ""
    mode = live.get("mode")
    mock = mode in ("mock", "public")
    title = {"mock": "모의 시세", "public": "종가 시세"}.get(mode, "실시간 시세")
    head = ('<div class="pxb-live-head"><b>'
            + ('' if mock else '<i class="pxb-live-dot"></i>')
            + title + '</b>'
            f'<span>{_e(live.get("state", ""))}'
            + (f' · {_e(live["at"])}' if live.get("at") else "") + "</span></div>")
    rows = live.get("rows") or []
    if not rows:
        return (f'<div class="pxb-live{" mock" if mock else ""}">{head}<div class="pxb-live-off">'
                '관심종목 실시간 시세는 키움 앱키·시크릿키를 설정하면 여기에 표시됩니다.</div></div>')
    cards = ""
    for row in rows:
        rate = row.get("rate")
        color = DOWN if (rate or 0) < 0 else UP
        move = f'{rate:+.2f}%' if rate is not None else "—"
        if row.get("change") is not None:
            move += f' ({row["change"]:+,.0f})'
        cards += (f'<div class="pxb-quote"><span>{_e(row.get("name") or row["code"])}</span>'
                  f'<b>{row["price"]:,.0f}</b><em style="color:{color}">{_e(move)}</em></div>')
    return f'<div class="pxb-live{" mock" if mock else ""}">{head}{cards}</div>'


GROUP_TITLES = {"A": ("A그룹 · 투자적기", "정배열 + 실적 양호", "a"),
                "B": ("B그룹 · 투자보류", "한 축이 1~2개 미달", "b"),
                "C": ("C그룹 · 대기", "이평선 수렴 · 방향 미정", "c"),
                "D": ("D그룹 · 관망", "추세 붕괴 또는 실적 부진", "d")}


def group_board(graded: list | None) -> str:
    """A·B·C·D 그룹판. 판정에 쓸 자료가 없으면 이유를 적습니다."""
    if not graded:
        return ""
    buckets = {key: [] for key in GROUP_TITLES}
    pending = [row for row in graded if row.get("group") not in buckets]
    for row in graded:
        if row.get("group") in buckets:
            buckets[row["group"]].append(row)
    cards = ""
    for key, (title, note, klass) in GROUP_TITLES.items():
        rows = sorted(buckets[key], key=lambda r: (-r.get("met", 0), r["name"]))
        chips = "".join(
            f'<span class="pxb-chip">{_e(r["name"])}'
            f'<em>{r["trend"]["grade"] or "-"}·{r["earnings"]["grade"]}</em></span>'
            for r in rows[:8])
        more = f'<span class="pxb-chip">외 {len(rows) - 8}</span>' if len(rows) > 8 else ""
        body = f'<div class="pxb-chips">{chips}{more}</div>' if rows else '<div class="pxb-empty">해당 종목 없음</div>'
        cards += (f'<div class="pxb-slot {klass}"><div class="pxb-slot-h"><b>{title}</b>'
                  f'<i>{len(rows)}</i></div><small>{note}</small>{body}</div>')
    board = f'<div class="pxb-board">{cards}</div>'
    if pending:
        names = ", ".join(_e(r["name"]) for r in pending[:6])
        reason = _e(pending[0].get("note") or pending[0].get("reason") or "자료 부족")
        board += (f'<div class="pxb-note" style="margin-top:10px">판정 보류 {len(pending)}종목 · '
                  f'{names}{"…" if len(pending) > 6 else ""} · {reason}</div>')
    return board


def render_decision_dashboard(details: dict, live: dict | None = None, graded: list | None = None) -> None:
    """3열 카드 한 판으로 첫 화면을 그립니다."""
    st.markdown(_CSS, unsafe_allow_html=True)
    reports = sorted((details or {}).values(), key=lambda r: r.get("as_of", ""), reverse=True)
    focus = reports[0] if reports else None
    money = (focus or {}).get("financial") or {}
    score, rows, verdict = _score_of(reports)
    name = focus.get("name", "삼성전자") if focus else "삼성전자"
    code = focus.get("code", "005930") if focus else "005930"
    focus_grade = next((g for g in (graded or []) if g["code"] == code), None)
    closes = (focus_grade or {}).get("closes") or []

    # 1행 ─ 점수 · 이익 · 매출
    meter = "".join(
        f'<div><span>{_e(k)}</span><i><u style="width:{v}%"></u></i><b>{v}</b></div>' for k, v in rows
    )
    card_score = _card(
        0, "종합 투자판단",
        f'<div class="pxb-value">{score}<small>/100</small></div>'
        f'<p class="pxb-sub">{_e(verdict)} · '
        + (f"공식 자료 {len(reports)}건 기준" if reports else f"{SAMPLE} 점수")
        + f'</p><div class="pxb-meter">{meter}</div>',
        wide_bloom=True,
    )

    if money:
        profit_text = growth(money["operating_profit"], money["prior_operating_profit"])
        revenue_text = growth(money["revenue"], money["prior_revenue"])
        period = f'{_e(money.get("prior_period", ""))} → {_e(money.get("period", ""))}'
        source = f'{_e(name)} · {_e(money.get("basis", "연결"))} 공식 자료'
    else:
        profit_text, revenue_text = "+33.2%", "+10.9%"
        period, source = "2024-12 → 2025-12", f"{name} · {SAMPLE}"
    profit_color = DOWN if profit_text.startswith("-") or "적자" in profit_text else UP
    revenue_color = DOWN if revenue_text.startswith("-") or "적자" in revenue_text else UP

    card_profit = _card(
        1, "영업이익 성장",
        f'<div class="pxb-value" style="color:{profit_color}">{_e(profit_text)}</div>'
        f'<p class="pxb-sub">{period}</p>'
        f'<span class="pxb-tag" style="color:{profit_color};background:{profit_color}16">{source}</span>'
        + (_spark([money["prior_operating_profit"], money["operating_profit"]], profit_color, "p", mini=True)
           if money else ""),
    )
    card_revenue = _card(
        2, "매출 성장",
        f'<div class="pxb-value" style="color:{revenue_color}">{_e(revenue_text)}</div>'
        f'<p class="pxb-sub">{period}</p>'
        f'<span class="pxb-tag" style="color:{revenue_color};background:{revenue_color}16">{source}</span>'
        + (_spark([money["prior_revenue"], money["revenue"]], revenue_color, "r", mini=True)
           if money else ""),
    )

    # 2행 ─ 흐름 · 실적 · 적정가치
    if len(closes) >= 20:
        lines = (focus_grade or {}).get("trend", {}).get("ema") or {}
        order = "정배열" if (focus_grade or {}).get("trend", {}).get("grade") == "정배열" else \
                (focus_grade or {}).get("trend", {}).get("grade") or "판정 전"
        note = f'{_e(name)} · 최근 {len(closes)}거래일 · 이평선 {order}'
        if lines:
            note += (f'<br><span style="font-size:11px;color:#A39781">'
                     + " · ".join(f'{k} {v:,.0f}' for k, v in lines.items()) + "</span>")
        body = (f'<p class="pxb-sub" style="margin-top:12px">{note}</p>'
                + _spark(closes, "#7FA98B", "t"))
    else:
        body = (f'<p class="pxb-sub" style="margin-top:12px">{_e(name)} 일별 종가를 모으는 중입니다. '
                '이동평균 60일선에는 62거래일이 필요합니다.</p>')
    card_trend = _card(3, "성장 흐름", body)
    if money:
        chart = _bars([money.get("prior_period", "이전"), money.get("period", "최근")],
                      [money["prior_revenue"], money["revenue"]],
                      [money["prior_operating_profit"], money["operating_profit"]])
        note = f'매출액 막대 · 영업이익 선 · 단위 {_e(money.get("unit", ""))}'
    else:
        chart = _bars(["3Q24", "4Q24", "1Q25", "2Q25"], [67, 72, 79, 84], [42, 48, 60, 67])
        note = f"매출액 막대 · 영업이익 선 · {SAMPLE}"
    card_earnings = _card(4, "실적 추이", f'<p class="pxb-sub" style="margin-top:12px">{note}</p>{chart}')

    value = (focus or {}).get("valuation") or {}
    if value:
        low, high, now = value["low"], value["high"], value["current_price"]
        mark = min(max((now - low) / max(high - low, 1), 0), 1) * 100
        labels = "".join(f"<span>{v:,.0f}</span>" for v in (low, value["base"], high))
        value_note = _e(str(value.get("method", "")))[:40]
        head, value_title = f"{now:,.0f}원", "적정가치 범위"
    elif len(closes) >= 20:
        # 평가 근거가 없으면 값을 지어내지 않고, 실제 종가가 어디쯤인지만 보여줍니다.
        low, high, now = min(closes), max(closes), closes[-1]
        mark = (now - low) / (high - low) * 100 if high > low else 50
        labels = "".join(f"<span>{v:,.0f}</span>" for v in (low, (low + high) / 2, high))
        value_note = f"최근 {len(closes)}거래일 종가 범위의 {mark:.0f}% 지점 · 적정주가가 아닙니다."
        head, value_title = f"{now:,.0f}원", "가격 범위 속 위치"
    else:
        mark, head, value_title = 50, "자료 대기", "가격 범위 속 위치"
        value_note = "일별 종가가 모이면 최근 범위와 현재 위치를 표시합니다."
        labels = "<span>-</span><span>-</span><span>-</span>"
    card_value = _card(
        5, value_title,
        f'<div class="pxb-value" style="font-size:32px">{head}</div>'
        f'<div class="pxb-range"><div class="pxb-range-line"><u style="left:24%;right:22%"></u>'
        f'<i style="left:{mark:.0f}%"></i></div>'
        f'<div class="pxb-range-lab">{labels}</div></div>'
        f'<p class="pxb-sub" style="margin-top:14px">{value_note}</p>',
    )

    # 3행 ─ 관심종목 · 확인할 것 · 교육자료
    if reports:
        watch_rows = [
            (r.get("name", ""), r.get("code", ""),
             growth((r.get("financial") or {}).get("operating_profit", 0),
                    (r.get("financial") or {}).get("prior_operating_profit", 0))
             if r.get("financial") else "조사 필요")
            for r in reports[:5]
        ]
        watch_note = f"영업이익 성장 · 공식 자료 {len(reports)}종목"
    else:
        watch_rows = [("삼성전자", "005930", "+33.2%"), ("SK하이닉스", "000660", "+101.2%"),
                      ("현대차", "005380", "+8.4%"), ("NAVER", "035420", "+12.1%")]
        watch_note = f"영업이익 성장 · {SAMPLE}"
    group_of = {g["code"]: g.get("group") for g in (graded or [])}
    watch = "".join(
        f'<li><span>{_e(label)} <small style="color:#A39781">'
        + (f'{group_of[row_code]}그룹' if group_of.get(row_code) else _e(row_code)) + '</small></span>'
        f'<em style="color:{DOWN if text.startswith("-") or "적자" in text else UP}">{_e(text)}</em></li>'
        for label, row_code, text in watch_rows
    )
    card_watch = _card(6, "관심종목",
                       f'<p class="pxb-sub" style="margin-top:12px">{_e(watch_note)}</p>'
                       f'<ul class="pxb-list">{watch}</ul>')

    gaps = [f'{_e(r.get("name", ""))} · {_e(g)}' for r in reports for g in (r.get("data_gaps") or [])][:4]
    if not gaps:
        gaps = ["분기 누적 실적 추가 조사", "수급·수정주가 시계열 수집", "적정주가 가정과 현 주가 대조"]
    card_todo = _card(7, "다음에 확인할 것",
                      '<ul class="pxb-notes">' + "".join(f"<li>{g}</li>" for g in gaps) + "</ul>")

    card_learn = _card(
        8, "교육자료",
        '<p class="pxb-sub" style="margin-top:14px">차트 기초 · 기술적 분석 · 투자 전략을 순서대로 익히고, '
        "차트에 직접 그려보며 확인하세요.</p>"
        '<div class="pxb-pens"><i></i><i></i><i></i><i></i></div>',
    )

    st.markdown(
        '<div class="pxb"><div class="pxb-top">'
        '<div class="pxb-title"><em>오늘의 <i>투자판단</i></em>'
        "<span>공식 자료로 확인한 변화와, 아직 확인이 필요한 것만 담았습니다.</span></div>"
        f'<div class="pxb-meta"><b>PLANX · STOCK INTELLIGENCE</b>{date.today():%Y년 %m월 %d일}</div></div>'
        + live_strip(live)
        + group_board(graded)
        + f'<div class="pxb-grid">{card_score}{card_profit}{card_revenue}'
        f"{card_trend}{card_earnings}{card_value}"
        f"{card_watch}{card_todo}{card_learn}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="px-live-divider"><span>내 관심종목 실데이터 분석</span></div>', unsafe_allow_html=True)
