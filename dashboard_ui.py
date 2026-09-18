"""PlanX 첫 화면 · 투자판단 콕핏 (화면 구성 예시).

시장 API가 연결되기 전 단계이므로 지수·가격 수치는 라벨이 붙은 샘플입니다.
research/ 폴더에 조사 결과가 있으면 기업 섹션과 브리핑은 실제 조사 값으로 채웁니다.
"""
from __future__ import annotations

from datetime import date
import html

import altair as alt
import pandas as pd
import streamlit as st

from chat_research import growth

NAVY = "#17324D"
GOLD = "#B9944A"
GREEN = "#16804B"
RED = "#D64545"    # 국내 관례: 상승 = 빨강
BLUE = "#2F6FD1"   # 하락 = 파랑
GREY = "#BCC3CA"
PAPER = "#FFFDF8"

SAMPLE = "화면 구성 예시 · 샘플"

_CSS = """
<style>
@keyframes pxPulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.72)}}
@keyframes pxRise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
@keyframes pxTape{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@keyframes pxSheen{from{background-position:0% 50%}to{background-position:200% 50%}}

/* ── 헤더 ─────────────────────────────────────────── */
.px-topline{animation:pxRise .5s ease both;padding:2px 2px 14px!important;border-bottom:1px solid rgba(185,148,74,.28)}
.px-topline span{background:linear-gradient(100deg,#6b4a1a,#a07b31 42%,#6b4a1a 74%);background-size:200% auto;-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;animation:pxSheen 6s linear infinite}
.px-topline b{color:#7b6a55}
.px-date i{animation:pxPulse 1.8s ease-in-out infinite;box-shadow:0 0 0 3px rgba(28,154,100,.16)}
.px-topline .px-badge{display:inline-block;margin-left:9px;padding:3px 10px;border-radius:999px;
  font:800 10px/1.6 Pretendard,sans-serif!important;letter-spacing:.06em;-webkit-text-fill-color:#7f6222;color:#7f6222;
  background:linear-gradient(135deg,#f6edda,#efe1c4);border:1px solid #e0cda4;animation:none}

/* ── 티커 테이프 ───────────────────────────────────── */
.px-tape{margin:12px 0 4px;overflow:hidden;border:1px solid #e7ded0;border-radius:10px;
  -webkit-mask-image:linear-gradient(90deg,transparent,#000 3%,#000 97%,transparent);
  mask-image:linear-gradient(90deg,transparent,#000 3%,#000 97%,transparent);
  background:linear-gradient(90deg,#fffdf7,#fbf5e9 50%,#fffdf7);box-shadow:inset 0 1px 0 #fff}
.px-tape-track{display:flex;width:max-content;animation:pxTape 38s linear infinite}
.px-tape-track:hover{animation-play-state:paused}
.px-tape em{font-style:normal;display:inline-flex;align-items:center;gap:7px;padding:9px 18px;font-size:11.5px;font-weight:700;color:#4a5567;white-space:nowrap}
.px-tape em b{font:700 12.5px Georgia,serif;color:#17324D}
.px-tape em:after{content:"";width:4px;height:4px;border-radius:50%;background:#dfd3bd;margin-left:11px}

/* ── 시장 스트립 ───────────────────────────────────── */
.px-market{background:linear-gradient(180deg,rgba(255,255,255,.96),rgba(255,255,255,.74))!important;
  border-color:#e6dcca!important;box-shadow:0 10px 26px rgba(67,52,31,.06);animation:pxRise .55s ease both}
.px-market span{color:#8b7a5e}
.px-market strong{font-size:23px!important;letter-spacing:-.4px}

/* ── 섹션 타이틀 / 탭 ──────────────────────────────── */
.px-title-row h2{font-size:21px!important;letter-spacing:-.3px;background:none!important;padding:0!important}
.px-title-row h2 span{all:unset;font:inherit;color:inherit}
.px-title-row [data-testid="stHeaderActionElements"],.px-section-head [data-testid="stHeaderActionElements"]{display:none!important}
.px-title-row b{box-shadow:0 6px 16px rgba(170,123,46,.32)}
.px-title-row span{border:1px solid #eae3d6}

/* ── 점수 · 시그널 카드 ────────────────────────────── */
.px-score,.px-signal{height:228px!important;background:linear-gradient(180deg,#ffffff,#fffdf8)!important;border-color:#e6dcca!important;
  box-shadow:0 12px 30px rgba(67,52,31,.07);transition:transform .22s ease,box-shadow .22s ease;animation:pxRise .6s ease both}
.px-score:hover,.px-signal:hover{transform:translateY(-3px);box-shadow:0 18px 38px rgba(67,52,31,.12)}
.px-score{background:linear-gradient(165deg,#1f3a57,#17324D 58%,#122a41)!important;border-color:#1b3550!important;color:#f4ece0}
.px-score .px-score-title{color:#e9dcc3}
.px-score .px-score-title b{color:#e8c887}
.px-score .px-score-row{color:#c6d2e0;border-top:1px solid rgba(255,255,255,.07);padding-top:3px;margin-top:3px}
.px-score .px-score-row b{color:#fff}
.px-ring{width:76px!important;height:76px!important;margin:8px auto 10px!important;
  box-shadow:0 0 0 1px rgba(255,255,255,.1),0 12px 26px rgba(0,0,0,.28)}
.px-ring strong{font-size:25px!important}
.px-score .px-score-row{font-size:10.5px!important}
.px-ring:before{background:#17324D!important;inset:9px!important}
.px-ring strong{color:#fff}
.px-ring span{color:#9fb0c4!important}
.px-signal-head b{letter-spacing:-.2px}
.px-bars i{background-image:linear-gradient(180deg,rgba(255,255,255,.45),rgba(255,255,255,0))}

/* ── 종목 헤더 ─────────────────────────────────────── */
.px-section-head{background:linear-gradient(180deg,#fff,#fffdf7)!important;border-color:#e6dcca!important}
.px-section-head strong{letter-spacing:-.5px}

/* ── 패널 공통 ─────────────────────────────────────── */
.px-panel-title{background:linear-gradient(180deg,#fff,#fdfaf3)!important;border-color:#e6dcca!important;letter-spacing:-.2px}
.px-heat{transition:transform .18s ease;cursor:default}
.px-heat:hover{transform:scale(1.05);z-index:2;box-shadow:0 8px 20px rgba(0,0,0,.14)}
.px-heat b{font-weight:750}
.px-watch-row:hover{background:#fdfaf3}
.px-watch-row.sample{opacity:.55}
.px-watch-row em.up{color:#D64545}
.px-watch-row em.down{color:#2F6FD1}
.px-value-line i{background:linear-gradient(90deg,#8fc3a4,#2f8d5e)!important}
.px-brief{background:linear-gradient(160deg,#f7f3ea,#f1ece0)!important}
.px-brief>b{background:linear-gradient(135deg,#c8a159,#8a6428)!important;color:#fff!important;font-weight:800}
.px-education{background:linear-gradient(120deg,#fff,#fdf8ee)!important;border-color:#e6dcca!important}

/* ── 보조 요소 ─────────────────────────────────────── */
.px-note{background:#fff;border:1px solid #e7ded0;border-top:0;border-radius:0 0 9px 9px;
  padding:16px;font-size:11px;line-height:1.7;color:#6b7889}
.px-caption{font-size:10.5px;color:#93866f;margin:6px 2px 0;letter-spacing:.02em}
</style>
"""

_MARKETS = [
    ("KOSPI", "2,482.36", "+0.75%", RED, [42, 44, 43, 47, 46, 50, 49, 53]),
    ("KOSDAQ", "723.61", "+0.89%", RED, [35, 37, 36, 39, 42, 41, 44, 43]),
    ("USD/KRW", "1,386.20", "-0.29%", BLUE, [52, 50, 53, 51, 54, 49, 48, 46]),
    ("WTI", "67.24", "+0.93%", RED, [32, 34, 33, 37, 36, 39, 40, 43]),
    ("GOLD", "2,577.30", "+0.48%", RED, [45, 46, 48, 47, 50, 51, 50, 53]),
]

_TAPE = [
    ("삼성전자", "72,400", "+2.69%"), ("SK하이닉스", "198,500", "+1.53%"),
    ("현대차", "273,000", "-0.36%"), ("LG에너지솔루션", "402,000", "-1.12%"),
    ("NAVER", "215,000", "+1.42%"), ("카카오", "39,850", "+0.76%"),
    ("삼성바이오로직스", "812,000", "+0.61%"), ("기아", "122,400", "+0.82%"),
    ("POSCO홀딩스", "358,500", "-0.44%"), ("셀트리온", "186,300", "+1.05%"),
]


def _spark(values: list[float], color: str) -> alt.Chart:
    low, high = min(values), max(values)
    span = (high - low) or 1
    floor = low - span * 0.45
    frame = pd.DataFrame({"순서": range(len(values)), "값": values, "바닥": floor})
    scale = alt.Scale(domain=[floor, high + span * 0.18])
    x = alt.X("순서:Q", axis=None)
    y = alt.Y("값:Q", axis=None, scale=scale)
    gradient = alt.Gradient(
        gradient="linear",
        stops=[alt.GradientStop(color="#ffffff", offset=0), alt.GradientStop(color=color, offset=1)],
        x1=1, x2=1, y1=1, y2=0,
    )
    base = alt.Chart(frame)
    area = base.mark_area(color=gradient, opacity=0.38).encode(x=x, y=y, y2=alt.Y2("바닥:Q"))
    line = base.mark_line(color=color, strokeWidth=2, interpolate="monotone").encode(x=x, y=y)
    return (area + line).properties(height=44).configure_view(stroke=None)


def _tape() -> None:
    items = "".join(
        f'<em>{html.escape(name)} <b>{price}</b>'
        f'<span style="color:{RED if change.startswith("+") else BLUE}">{change}</span></em>'
        for name, price, change in _TAPE
    )
    st.markdown(f'<div class="px-tape"><div class="px-tape-track">{items}{items}</div></div>', unsafe_allow_html=True)


def _market_strip() -> None:
    for col, (name, value, delta, color, points) in zip(st.columns(5, gap="small"), _MARKETS):
        with col:
            st.markdown(
                f'<div class="px-market"><span>{name}</span><strong>{value}</strong>'
                f'<em style="color:{color}">{delta}</em></div>',
                unsafe_allow_html=True,
            )
            st.altair_chart(_spark(points, color), width="stretch")
    st.markdown(f'<div class="px-caption">{SAMPLE} · 시장 API 연결 전이라 실시간 시세가 아닙니다.</div>', unsafe_allow_html=True)


def _score_panel(score: int, rows: list[tuple[str, int]]) -> None:
    detail = "".join(f'<div class="px-score-row"><span>{html.escape(k)}</span><b>{v}</b></div>' for k, v in rows)
    ring = (
        f"background:conic-gradient(#e8c887 0 {score}%,rgba(255,255,255,.12) {score}% 100%)"
    )
    st.markdown(
        f'<div class="px-score"><div class="px-score-title">종합 투자점수 <b>{score}</b></div>'
        f'<div class="px-ring" style="{ring}"><strong>{score}</strong><span>/100</span></div>'
        f"{detail}</div>",
        unsafe_allow_html=True,
    )


def _signal_card(title: str, icon: str, state: str, headline: str, note: str, bars: list[int], tone: str) -> None:
    columns = "".join(f'<i style="height:{max(10, v)}%;background:{tone}"></i>' for v in bars)
    st.markdown(
        f'<div class="px-signal"><div class="px-signal-head"><b>{icon} {html.escape(title)}</b>'
        f'<span>{html.escape(state)}</span></div>'
        f"<h4>{html.escape(headline)}</h4><p>{html.escape(note)}</p>"
        f'<div class="px-bars">{columns}</div></div>',
        unsafe_allow_html=True,
    )


def _decision_row(score: int, rows: list[tuple[str, int]]) -> None:
    cols = st.columns([1.05, 1, 1, 1, 1, 1], gap="small")
    with cols[0]:
        _score_panel(score, rows)
    cards = [
        ("매크로", "◎", "중립", "안정적인 흐름 지속", "금리와 유동성의 방향을 확인합니다.", [28, 34, 40, 48, 56], GREY),
        ("성장산업", "◒", "긍정", "AI 반도체 수요 확대", "산업 성장과 투자 계획을 함께 봅니다.", [24, 34, 47, 62, 78], GREEN),
        ("수출·수주", "▰", "긍정", "수출 개선세 지속", "수출·수주가 매출로 전환되는지 봅니다.", [26, 38, 49, 63, 82], GREEN),
        ("실적 성장", "▥", "긍정", "견조한 이익 성장", "매출보다 영업이익의 속도를 봅니다.", [32, 42, 50, 61, 79], GREEN),
        ("수급 강도", "↗", "긍정", "매수 우위 지속", "기관과 외국인의 방향을 확인합니다.", [30, 43, 58, 72, 55], BLUE),
    ]
    for col, args in zip(cols[1:], cards):
        with col:
            _signal_card(*args)


def _price_chart(label: str) -> None:
    dates = pd.date_range("2024-01-01", periods=24, freq="MS")
    focus = [100, 103, 106, 105, 110, 113, 111, 116, 120, 119, 124, 128,
             132, 130, 137, 142, 140, 148, 151, 147, 158, 163, 160, 166]
    kospi = [100, 102, 104, 103, 106, 107, 106, 109, 111, 110, 112, 115,
             117, 116, 119, 121, 120, 123, 124, 122, 126, 128, 127, 130]
    sector = [100, 104, 108, 107, 112, 116, 114, 121, 126, 124, 131, 136,
              141, 138, 146, 153, 151, 160, 166, 161, 172, 179, 176, 185]
    frame = pd.DataFrame({
        "날짜": list(dates) * 3,
        "수익률": focus + kospi + sector,
        "구분": [label] * 24 + ["KOSPI"] * 24 + ["반도체"] * 24,
    })
    order = [label, "KOSPI", "반도체"]
    base = alt.Chart(frame).encode(
        x=alt.X("날짜:T", title=None, axis=alt.Axis(format="%y.%m", labelAngle=0, tickCount=6)),
        y=alt.Y("수익률:Q", title="지수화 (시작=100)", scale=alt.Scale(zero=False)),
    )
    area = (
        base.transform_filter(alt.datum["구분"] == label)
        .mark_area(
            opacity=0.22,
            color=alt.Gradient(
                gradient="linear",
                stops=[alt.GradientStop(color="#ffffff", offset=0), alt.GradientStop(color=GREEN, offset=1)],
                x1=1, x2=1, y1=1, y2=0,
            ),
        )
    )
    lines = base.mark_line(strokeWidth=2.4).encode(
        color=alt.Color("구분:N", sort=order,
                        scale=alt.Scale(domain=order, range=[GREEN, BLUE, GOLD]),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("날짜:T", format="%Y-%m"), "구분:N", "수익률:Q"],
    )
    chart = (
        (area + lines)
        .properties(height=295)
        .configure(background=PAPER)
        .configure_view(stroke=None)
        .configure_axis(gridColor="#EEE8DC", labelColor="#617086", titleColor="#617086")
        .configure_legend(labelColor=NAVY, title=None)
    )
    st.altair_chart(chart, width="stretch")


def _heatmap() -> None:
    cells = [
        ("반도체", "+2.8%", "#137747"), ("IT하드웨어", "+1.5%", "#32945F"),
        ("자동차", "+1.2%", "#55A671"), ("2차전지", "-0.8%", "#EAA6A6"),
        ("바이오", "+0.6%", "#ADD7C0"), ("인터넷", "+1.9%", "#27875B"),
        ("금융", "+0.4%", "#C7E3D1"), ("에너지", "-0.3%", "#F2C9C9"),
        ("화학", "-1.1%", "#AFC9EE"), ("기계", "+0.7%", "#9FCFB5"),
        ("건설", "-0.6%", "#E9B2B2"), ("통신", "+0.2%", "#C5DFC9"),
    ]
    blocks = "".join(
        f'<div class="px-heat" style="background:{color}"><b>{name}</b><span>{delta}</span></div>'
        for name, delta, color in cells
    )
    st.markdown(f'<div class="px-heatmap">{blocks}</div>', unsafe_allow_html=True)


def _watchlist() -> None:
    rows = [
        ("삼성전자", "72,400", "+2.69%"), ("SK하이닉스", "198,500", "+1.53%"),
        ("현대차", "273,000", "-0.36%"), ("기아", "122,400", "+0.82%"),
        ("NAVER", "215,000", "+1.42%"), ("카카오", "39,850", "+0.76%"),
    ]
    body = "".join(
        f'<div class="px-watch-row"><span>★ {html.escape(name)}</span><b>{price}</b>'
        f'<em class="{"down" if change.startswith("-") else "up"}">{change}</em></div>'
        for name, price, change in rows
    )
    st.markdown(f'<div class="px-watch">{body}</div>', unsafe_allow_html=True)


def _growth_text(report: dict) -> str:
    f = report.get("financial") or {}
    if not f:
        return "조사 필요"
    return growth(f["operating_profit"], f["prior_operating_profit"])


def _earnings_panel(report: dict | None) -> None:
    st.markdown('<div class="px-panel-title">실적 추이 <span>매출액 · 영업이익</span></div>', unsafe_allow_html=True)
    f = (report or {}).get("financial") or {}
    if f:
        frame = pd.DataFrame({
            "기간": [f.get("prior_period", "이전"), f.get("period", "최근")],
            "매출액": [f["prior_revenue"], f["revenue"]],
            "영업이익": [f["prior_operating_profit"], f["operating_profit"]],
        })
        caption = f'{f.get("basis", "연결")} · 단위 {f.get("unit", "")} · 공식 자료'
    else:
        frame = pd.DataFrame({
            "기간": ["3Q23", "4Q23", "1Q24", "2Q24", "3Q24", "4Q24(E)"],
            "매출액": [67, 72, 72, 74, 79, 84],
            "영업이익": [42, 45, 48, 52, 60, 67],
        })
        caption = SAMPLE
    x = alt.X("기간:N", axis=alt.Axis(labelAngle=0), title=None)
    width = 26 if len(frame) > 3 else 56
    bars = (
        alt.Chart(frame)
        .mark_bar(size=width, cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.85,
                  color=alt.Gradient(
                      gradient="linear",
                      stops=[alt.GradientStop(color="#9DC0EE", offset=0), alt.GradientStop(color=BLUE, offset=1)],
                      x1=1, x2=1, y1=1, y2=0))
        .encode(x=x, y=alt.Y("매출액:Q", title=None, axis=alt.Axis(labels=False, ticks=False, grid=False)),
                tooltip=["기간:N", "매출액:Q", "영업이익:Q"])
    )
    line = (
        alt.Chart(frame)
        .mark_line(color=GOLD, strokeWidth=2.6, point=alt.OverlayMarkDef(color=GOLD, size=52))
        .encode(x=x, y=alt.Y("영업이익:Q", title=None, axis=alt.Axis(labels=False, ticks=False, grid=False),
                             scale=alt.Scale(zero=False, padding=26)))
    )
    chart = (
        (bars + line)
        .resolve_scale(y="independent")
        .properties(height=150)
        .configure_view(stroke=None)
        .configure_axis(grid=False, labelColor="#617086")
    )
    st.altair_chart(chart, width="stretch")
    st.markdown(
        f'<div class="px-caption"><b style="color:{BLUE}">■</b> 매출액 '
        f'<b style="color:{GOLD}">■</b> 영업이익 · {html.escape(caption)}</div>',
        unsafe_allow_html=True,
    )


def _value_panel(report: dict | None) -> None:
    st.markdown('<div class="px-panel-title">적정가치 <span>범위 참고</span></div>', unsafe_allow_html=True)
    v = (report or {}).get("valuation") or {}
    if v:
        low, base, high, now = v["low"], v["base"], v["high"], v["current_price"]
        span = max(high - low, 1)
        mark = min(max((now - low) / span, 0), 1) * 100
        labels = "".join(f"<span>{value:,.0f}</span>" for value in (low, base, high))
        note = html.escape(str(v.get("method", "")))[:42]
        st.markdown(
            f'<div class="px-value"><b>현재 {now:,.0f}원</b>'
            f'<div class="px-value-line"><i></i><strong style="left:{mark:.0f}%"></strong></div>'
            f'<div class="px-value-label">{labels}</div><small>{note} · 목표주가 아님</small></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="px-value"><b>현재 72,400원</b>'
            '<div class="px-value-line"><i></i><strong></strong></div>'
            '<div class="px-value-label"><span>52,000</span><span>68,000</span>'
            '<span>86,000</span><span>102,000</span></div>'
            f"<small>{SAMPLE} · 목표주가 아님</small></div>",
            unsafe_allow_html=True,
        )


def _brief_panel(report: dict | None) -> None:
    st.markdown('<div class="px-panel-title">✦ 조사 브리핑 <span>공식 자료 기준</span></div>', unsafe_allow_html=True)
    lines: list[str] = []
    if report:
        for key in ("summary", "business"):
            text = ((report.get(key) or {}).get("text") or "").strip()
            if text:
                lines.append(text[:110])
        lines += [f"확인 필요 · {g}" for g in (report.get("data_gaps") or [])]
    if not lines:
        lines = [
            "반도체 수요 확대와 영업이익 개선을 함께 확인합니다.",
            "환율과 메모리 가격 변화가 다음 실적의 핵심 변수입니다.",
            "현재 가격은 역사적 범위와 전망치를 구분해 판단해야 합니다.",
        ]
    items = "".join(f"<li>{html.escape(line)}</li>" for line in lines[:3])
    st.markdown(f'<div class="px-brief"><b>AI</b><ul>{items}</ul></div>', unsafe_allow_html=True)


def _score_of(reports: list[dict]) -> tuple[int, list[tuple[str, int]]]:
    """조사 결과가 있으면 규칙 기반 점수, 없으면 샘플 점수를 돌려줍니다."""
    if not reports:
        return 78, [("매크로", 76), ("산업 경쟁력", 82), ("실적", 80), ("밸류에이션", 70)]

    def grade(current, prior, span) -> int:
        if not prior or prior <= 0:
            return 50
        return int(min(max(50 + (current / prior - 1) * 100 * span, 0), 100))

    money = [r.get("financial") or {} for r in reports if r.get("financial")]
    revenue = int(sum(grade(f["revenue"], f["prior_revenue"], 2.0) for f in money) / len(money)) if money else 50
    profit = int(sum(grade(f["operating_profit"], f["prior_operating_profit"], 1.0) for f in money) / len(money)) if money else 50
    gaps = sum(len(r.get("data_gaps") or []) for r in reports)
    quality = int(min(max(100 - gaps * 8, 0), 100))
    peers = int(min(max(60 + sum(1 for r in reports if r.get("peers")) * 10, 0), 100))
    rows = [("매출 성장", revenue), ("이익 성장", profit), ("경쟁 비교", peers), ("자료 충실도", quality)]
    return int(sum(v for _, v in rows) / len(rows)), rows


def render_decision_dashboard(details: dict) -> None:
    """첫 화면 투자판단 콕핏을 그립니다."""
    st.markdown(_CSS, unsafe_allow_html=True)
    reports = sorted((details or {}).values(), key=lambda r: r.get("as_of", ""), reverse=True)
    focus = reports[0] if reports else None

    st.markdown(
        '<div class="px-topline"><div><span>PlanX</span><b>STOCK INTELLIGENCE</b>'
        "<small>더 깊은 분석이, 더 나은 투자를</small></div>"
        f'<div class="px-date">{date.today():%Y년 %m월 %d일} · <i></i> 시장 데이터 샘플'
        '<span class="px-badge">SAMPLE PREVIEW</span></div></div>',
        unsafe_allow_html=True,
    )
    _tape()
    _market_strip()

    st.markdown(
        '<div class="px-title-row"><h2>오늘의 투자판단</h2><div><span>시장</span><i>›</i>'
        "<span>산업</span><i>›</i><span>기업</span><i>›</i><b>투자판단</b></div></div>",
        unsafe_allow_html=True,
    )
    score, rows = _score_of(reports)
    _decision_row(score, rows)

    name = focus.get("name", "삼성전자") if focus else "삼성전자"
    code = focus.get("code", "005930") if focus else "005930"
    headline = _growth_text(focus) if focus else "+2.69%"
    falling = headline.startswith("-") or "적자" in headline
    tone = BLUE if falling else RED
    period = ((focus or {}).get("financial") or {}).get("period", "")
    subtitle = f'영업이익 성장 · 공식 자료 {period}'.strip() if focus else f"현재가 · {SAMPLE}"
    value = f"영업이익 {headline}" if focus else "72,400원"
    arrow = "▼" if falling else "▲"
    st.markdown(
        f'<div class="px-section-head"><div><h3>{html.escape(name)} <small>{html.escape(code)}</small></h3>'
        f'<strong>{html.escape(value)} <em style="color:{tone}">{arrow}</em></strong></div>'
        f"<span>{html.escape(subtitle)}</span></div>",
        unsafe_allow_html=True,
    )

    chart_col, heat_col, watch_col = st.columns([2.45, 1, 1.05], gap="small")
    with chart_col:
        _price_chart(name)
    with heat_col:
        st.markdown('<div class="px-panel-title">섹터별 등락률 <span>1일 · 샘플</span></div>', unsafe_allow_html=True)
        _heatmap()
    with watch_col:
        st.markdown('<div class="px-panel-title">관심종목 <span>샘플 · 더보기 ›</span></div>', unsafe_allow_html=True)
        _watchlist()

    left, middle, right = st.columns([1.08, 1, 1.35], gap="small")
    with left:
        _earnings_panel(focus)
    with middle:
        _value_panel(focus)
    with right:
        _brief_panel(focus)

    st.markdown(
        '<div class="px-education"><div><b>교육자료</b>'
        "<span>차트 기초 · 기술적 분석 · 투자 전략</span></div>"
        '<div class="px-pens"><i></i><i></i><i></i><i></i></div>'
        "<small>차트에 직접 그려보며 학습해보세요.</small></div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="px-live-divider"><span>내 관심종목 실데이터 분석</span></div>', unsafe_allow_html=True)
