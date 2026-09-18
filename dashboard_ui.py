"""PlanX 첫 화면 브리핑.

가짜 샘플 수치 대신, research/ 폴더에 반영된 공식 자료 조사 결과만 보여줍니다.
조사 결과가 없으면 빈 상태 안내만 표시합니다.
"""
from __future__ import annotations

from datetime import date
import html

import streamlit as st

from chat_research import growth

UP = "#D64545"    # 국내 관례: 상승 = 빨강
DOWN = "#2F6FD1"  # 하락 = 파랑

_CSS = """
<style>
.pb-top{display:flex;justify-content:space-between;align-items:center;padding:4px 2px 14px;border-bottom:1px solid #ECE4D6;margin-bottom:18px}
.pb-top b{font:600 26px/1 Georgia,serif;color:#8a6428}
.pb-top span{font-size:12px;color:#6b7889}
.pb-pill{display:inline-block;margin-left:8px;padding:3px 9px;border-radius:999px;background:#F3EEE4;color:#7a6440;font-size:11px}
.pb-head h2{font-size:22px!important;margin:0 0 4px!important}
.pb-head p{font-size:13px!important;color:#6b7889!important;margin:0 0 14px!important}
.pb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.pb-card{background:#fff;border:1px solid #ECE4D6;border-radius:12px;padding:16px 18px}
.pb-card-top{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}
.pb-card-top b{font-size:17px;color:#17324D}
.pb-card-top small{font-size:11px;color:#94a0ae}
.pb-row{margin:10px 0}
.pb-row-label{display:flex;justify-content:space-between;font-size:12px;color:#5d6d82}
.pb-row-label strong{font-size:14px;font-variant-numeric:tabular-nums}
.pb-track{height:6px;background:#F1EEE8;border-radius:6px;margin-top:5px;overflow:hidden}
.pb-track i{display:block;height:100%;border-radius:6px}
.pb-foot{display:flex;justify-content:space-between;margin-top:12px;padding-top:10px;border-top:1px dashed #ECE4D6;font-size:11px;color:#94a0ae}
.pb-gap{color:#B7791F}
.pb-todo{margin-top:12px;background:#FBF8F2;border:1px solid #ECE4D6;border-radius:12px;padding:14px 18px}
.pb-todo b{font-size:13px;color:#17324D}
.pb-todo ul{margin:8px 0 0;padding-left:18px}
.pb-todo li{font-size:12px!important;line-height:1.7!important;color:#5d6d82}
.pb-empty{background:#fff;border:1px dashed #D9CBB5;border-radius:12px;padding:20px;font-size:13px;color:#6b7889}
.pb-divider{display:flex;align-items:center;gap:12px;margin:28px 0 8px;color:#80612f;font-size:11px;font-weight:800;letter-spacing:.08em}
.pb-divider:before,.pb-divider:after{content:"";height:1px;background:#d9cbb5;flex:1}
</style>
"""


def _pct(current, previous):
    try:
        if previous and previous > 0:
            return (current / previous - 1) * 100
    except TypeError:
        pass
    return None


def _metric(label: str, current, previous) -> str:
    text = growth(current, previous)
    pct = _pct(current, previous)
    color = UP if (pct is None and current > 0) or (pct is not None and pct >= 0) else DOWN
    width = min(abs(pct), 100) if pct is not None else 100
    return (
        f'<div class="pb-row"><div class="pb-row-label"><span>{label}</span>'
        f'<strong style="color:{color}">{html.escape(text)}</strong></div>'
        f'<div class="pb-track"><i style="width:{width:.0f}%;background:{color}"></i></div></div>'
    )


def _company_card(report: dict) -> str:
    f = report.get("financial") or {}
    name = html.escape(report.get("name", ""))
    code = html.escape(report.get("code", ""))
    if f:
        body = _metric("매출 성장", f["revenue"], f["prior_revenue"])
        body += _metric("영업이익 성장", f["operating_profit"], f["prior_operating_profit"])
        period = f'{html.escape(f.get("prior_period", ""))} → {html.escape(f.get("period", ""))}'
    else:
        body = '<div class="pb-row-label"><span>실적 자료 조사 필요</span></div>'
        period = "기간 미확인"
    gaps = len(report.get("data_gaps") or [])
    gap_html = f'<span class="pb-gap">확인 필요 {gaps}건</span>' if gaps else "<span>확인 완료</span>"
    return (
        f'<div class="pb-card"><div class="pb-card-top"><b>{name}</b><small>{code}</small></div>'
        f"{body}"
        f'<div class="pb-foot"><span>{period} · 조사일 {html.escape(report.get("as_of", ""))}</span>{gap_html}</div></div>'
    )


def render_decision_dashboard(details: dict) -> None:
    """research/ 조사 결과로 첫 화면 브리핑을 그립니다."""
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="pb-top"><b>PlanX</b><span>{date.today():%Y년 %m월 %d일}'
        '<span class="pb-pill">공식 자료 기준 · 실시간 아님</span></span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pb-head"><h2>조사 브리핑</h2>'
        "<p>공시로 확인한 실적 변화와 아직 확인이 필요한 항목만 모았습니다.</p></div>",
        unsafe_allow_html=True,
    )

    reports = sorted((details or {}).values(), key=lambda r: r.get("as_of", ""), reverse=True)
    if not reports:
        st.markdown(
            '<div class="pb-empty">아직 반영된 조사 결과가 없습니다. 아래에서 종목을 추가하고 조사 요청을 보내면 여기에 요약이 나타납니다.</div>',
            unsafe_allow_html=True,
        )
    else:
        cards = "".join(_company_card(r) for r in reports)
        st.markdown(f'<div class="pb-grid">{cards}</div>', unsafe_allow_html=True)

        todos = [
            f'<li><b>{html.escape(r.get("name", ""))}</b> · {html.escape(g)}</li>'
            for r in reports
            for g in (r.get("data_gaps") or [])
        ][:6]
        if todos:
            st.markdown(
                f'<div class="pb-todo"><b>다음에 확인할 것</b><ul>{"".join(todos)}</ul></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="pb-divider"><span>내 관심종목 실데이터 분석</span></div>', unsafe_allow_html=True)
