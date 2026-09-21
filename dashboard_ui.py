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

# 색은 눈으로 고르지 않고 검증기로 확인했습니다.
# validate_palette.js "#C2503F,#36699E,#178F63,#B8730A" --mode light
#   명도대역 PASS · 채도 PASS · 정상시력 ΔE 17.0 PASS · 대비 3:1 전부 PASS
#   색각 구분 ΔE 7.8은 6~8 구간이라 직접 라벨을 함께 답니다.
UP = "#C2503F"     # 국내 관례: 상승 = 빨강
DOWN = "#36699E"   # 하락 = 파랑
LINE = "#178F63"   # 가격선
AMBER = "#B8730A"  # 영업이익선
INK = "#2E2822"
GOLD = "#B08343"
# 그룹은 색만으로 뜻을 전하지 않도록 이름·기호를 항상 함께 답니다.
STATUS = {"A": "#0CA30C", "B": "#FAB219", "C": "#7B7465"}
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

.pxb-frame{padding:26px 28px 24px;border-radius:24px;border:1px solid #E7DCC7;
  background:linear-gradient(180deg,#FFFEFA,#FCF8F0);box-shadow:0 18px 44px rgba(90,72,44,.07)}
.pxb-top{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;flex-wrap:wrap;
  padding:2px 2px 18px;border-bottom:2px solid #E7DCC7}
.pxb-section{margin-top:26px}
.pxb-section-h{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.pxb-section-h b{font-size:12px;font-weight:800;letter-spacing:.14em;color:#946E38;white-space:nowrap}
.pxb-section-h span{font-size:11.5px;color:#7E7463;white-space:nowrap}
.pxb-section-h:after{content:"";flex:1;height:1px;background:linear-gradient(90deg,#E7DCC7,transparent)}
.pxb-num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}
.pxb-title em{display:block;font:600 40px/1.15 "Playfair Display",Georgia,serif;font-style:normal;
  letter-spacing:-.6px;color:#2E2822}
.pxb-title em i{font-style:normal;color:#946E38}
.pxb-title span{display:block;margin-top:9px;font-size:13px;color:#7B7465}
.pxb-meta{text-align:right;font-size:12px;color:#7B7465;line-height:1.9}
.pxb-meta b{display:block;font-size:11px;letter-spacing:.22em;color:#946E38}

.pxb-board{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:20px}
.pxb-slot{position:relative;padding:18px 18px 16px;border-radius:18px;overflow:hidden;min-height:150px;
  border:1px solid #EDE3D2;background:linear-gradient(170deg,#FFFDF8,#FBF6EC);
  box-shadow:0 10px 26px rgba(90,72,44,.06);animation:pxbRise .5s ease both}
.pxb-slot.a{border-color:#BFD8C4;background:linear-gradient(170deg,#FBFEFB,#F1F7F0)}
.pxb-slot.c{border-color:#E2D6BD;background:linear-gradient(170deg,#FFFDF6,#F8F3E6)}
.pxb-slot-h{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.pxb-slot-h b{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:800;color:#2E2822}
.pxb-dot{width:9px;height:9px;border-radius:50%;flex:none;box-shadow:0 0 0 3px rgba(255,255,255,.7)}
.pxb-slot-h i{font-style:normal;font:650 24px Pretendard,"Noto Sans KR",sans-serif;color:#2E2822;
  letter-spacing:-.5px}
.pxb-slot small{display:block;margin-top:6px;font-size:11px;color:#7B7465;line-height:1.55}
.pxb-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.pxb-chip{display:inline-block;padding:4px 10px;border-radius:999px;font-size:11px;
  background:#FFFFFFAA;border:1px solid #E7DCC7;color:#5F584B;text-decoration:none;
  cursor:pointer;transition:border-color .15s,background .15s,transform .15s}
a.pxb-chip:hover{border-color:#B08343;background:#FFFFFF;transform:translateY(-1px);
  box-shadow:0 4px 10px rgba(90,72,44,.12)}
a.pxb-chip,a.pxb-chip:visited,a.pxb-chip em{color:#5F584B;text-decoration:none}
.pxb-slot-note{display:block;margin:6px 0 2px;font-size:11px;color:#7B7465;line-height:1.55}
/* 그룹 칸의 종목은 Streamlit 단추입니다. 링크로 두면 화면을 새로 열어
   로그인 상태가 풀리므로, 같은 화면 안에서 처리되는 단추를 씁니다. */
[class*="st-key-pxgrp-"] [data-testid="stButton"] button{
  width:100%;justify-content:flex-start;text-align:left;padding:5px 11px;min-height:0;
  border-radius:999px;font-size:11.5px;font-weight:500;color:#5F584B;
  background:#FFFFFFAA;border:1px solid #E7DCC7;white-space:normal;line-height:1.45}
[class*="st-key-pxgrp-"] [data-testid="stButton"] button:hover{
  border-color:#B08343;background:#FFFFFF;color:#2E2822}
[class*="st-key-pxgrp-"] [data-testid="stButton"]{margin-bottom:-6px}
.st-key-pxgrp-a [data-testid="stButton"] button{border-color:#CFE2D2}
.st-key-pxgrp-a [data-testid="stButton"] button:hover{border-color:#5E9B6B}
.st-key-pxgrp-c [data-testid="stButton"] button{border-color:#E2D6BD}
[class*="st-key-pxgrp-"] [data-testid="stExpander"] summary{font-size:11px;color:#946E38}
.pxb-more{margin-top:8px}
.pxb-more>summary{list-style:none;cursor:pointer;display:inline-block;padding:4px 12px;
  border-radius:999px;font-size:11px;font-weight:700;color:#946E38;
  background:#FFFFFFAA;border:1px dashed #DCC9A5}
.pxb-more>summary::-webkit-details-marker{display:none}
.pxb-more>summary:hover{border-style:solid;border-color:#B08343;background:#FFFFFF}
.pxb-more[open]>summary{margin-bottom:4px}
.pxb-chip em{font-style:normal;color:#7E7463;margin-left:4px;font-size:10px}
.pxb-slot.a .pxb-chip{border-color:#CFE2D2}
.pxb-empty{margin-top:12px;font-size:11px;color:#7E7463}
.pxb-note{font-size:11px;color:#7B7465;line-height:1.6}
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

.pxb-label{font-size:11px;font-weight:800;letter-spacing:.16em;color:#946E38}
.pxb-value{margin:14px 0 0;font:650 42px/1 Pretendard,"Noto Sans KR",sans-serif;letter-spacing:-1.4px}
.pxb-value small{font-size:16px;font-weight:600;margin-left:4px}
.pxb-sub{margin:11px 0 0;font-size:12.5px;line-height:1.7;color:#7C7361;max-width:78%}
.pxb-tag{display:inline-block;margin-top:14px;padding:4px 11px;border-radius:999px;font-size:10.5px;
  font-weight:800;letter-spacing:.04em}

.pxb-meter{margin-top:16px;display:flex;flex-direction:column;gap:9px}
.pxb-meter div{display:grid;grid-template-columns:60px 1fr 28px;align-items:center;gap:10px;
  font-size:11px;color:#7B7465}
.pxb-meter i{display:block;height:5px;border-radius:5px;background:#EFE7D8;overflow:hidden;font-style:normal}
.pxb-meter i u{display:block;height:100%;border-radius:5px;text-decoration:none;
  background:linear-gradient(90deg,#DCC08A,#B08343)}
.pxb-meter b{text-align:right;color:#2E2822;font-variant-numeric:tabular-nums}
.pxb-list em,.pxb-list b{font-variant-numeric:tabular-nums}

.pxb-chart{display:block;width:100%;height:104px;margin-top:18px}
.pxb-chart.mini{height:62px;margin-top:20px;opacity:.95}
.pxb-chart text{fill:#7E7463;font-size:9.5px}
.pxb-range{margin-top:26px}
.pxb-range-line{position:relative;height:7px;border-radius:7px;background:#EFE7D8}
.pxb-range-line u{position:absolute;top:0;bottom:0;border-radius:7px;text-decoration:none;
  background:linear-gradient(90deg,#CBD9C4,#7FA98B)}
.pxb-range-line i{position:absolute;top:-5px;width:17px;height:17px;margin-left:-8px;max-width:17px;border-radius:50%;
  background:linear-gradient(140deg,#F3DFA9,#B08343);border:3px solid #FFFDF8;
  box-shadow:0 3px 8px rgba(90,72,44,.25)}
.pxb-range-lab{display:flex;justify-content:space-between;margin-top:10px;font-size:10px;color:#7E7463}

.pxb-list{margin:16px 0 0;padding:0;list-style:none}
.pxb-list li{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 0;
  border-bottom:1px solid #F0E8D9;font-size:12px;color:#5F584B}
.pxb-list li:last-child{border-bottom:0}
.pxb-list b{font:600 13px Pretendard,"Noto Sans KR",sans-serif;color:#2E2822;
  font-variant-numeric:tabular-nums}
.pxb-list em{font-style:normal;font-weight:800;font-size:11.5px}
.pxb-notes{margin:16px 0 0;padding-left:16px}
.pxb-notes li{font-size:12px;line-height:1.85;color:#6B6353;margin-bottom:6px}
.pxb-pens{display:flex;gap:10px;margin-top:20px}
.pxb-pens i{width:22px;height:6px;border-radius:6px;transform:rotate(-40deg);background:#D9846F}
.pxb-pens i:nth-child(2){background:#6F9BC4}.pxb-pens i:nth-child(3){background:#7FA98B}
.pxb-pens i:nth-child(4){background:#C9A24D}


@media(max-width:1080px){.pxb-grid,.pxb-board{grid-template-columns:repeat(2,1fr)}}
@media(max-width:720px){
  .pxb-grid,.pxb-board{grid-template-columns:1fr;gap:14px}
  /* 규칙 설명이 길어 좁은 창에서는 줄바꿈해야 화면 밖으로 나가지 않습니다. */
  .pxb-section-h{flex-wrap:wrap;gap:4px 10px}
  .pxb-section-h span{white-space:normal;flex:1 1 100%}
  .pxb-section-h:after{display:none}
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
    """한 계열의 흐름. 값은 마우스오버로만 읽게 두지 않고 끝값과 범위를 적습니다."""
    w, h, pad = 300.0, (62.0 if mini else 104.0), (8.0 if mini else 16.0)
    low, high = min(values), max(values)
    span = (high - low) or 1
    step = w / max(len(values) - 1, 1)
    pts = [(i * step, pad + (h - pad * 2) * (1 - (v - low) / span)) for i, v in enumerate(values)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"M0,{h} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" L{w},{h} Z"
    tip_x, tip_y = pts[-1]
    labels = ""
    if not mini:
        last = values[-1]
        labels = (f'<text x="{w - 2:.0f}" y="{max(tip_y - 7, 11):.0f}" text-anchor="end"'
                  f' fill="{color}" font-size="10" font-weight="700">{last:,.0f}</text>')
        # 끝값이 최고·최저와 같으면 같은 숫자를 두 번 적지 않습니다.
        if high != last:
            labels += f'<text x="2" y="11" fill="#7E7463" font-size="9">{high:,.0f}</text>'
        if low != last:
            labels += f'<text x="2" y="{h - 3:.0f}" fill="#7E7463" font-size="9">{low:,.0f}</text>' 
    return (
        f'<svg class="pxb-chart{" mini" if mini else ""}" viewBox="0 0 {w:.0f} {h:.0f}"'
        ' preserveAspectRatio="none" role="img">'
        f'<defs><linearGradient id="pxb{key}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{color}" stop-opacity=".3"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
        f'<path d="{area}" fill="url(#pxb{key})"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2.4"'
        f' stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{tip_x:.1f}" cy="{tip_y:.1f}" r="4" fill="{color}"/>{labels}'
        f'<title>{low:,.0f} ~ {high:,.0f} · 마지막 {values[-1]:,.0f}</title></svg>'
    )


def _bars(labels: list[str], revenue: list[float], profit: list[float]) -> str:
    """매출액과 영업이익을 같은 축의 묶음 막대로 그립니다.

    두 값 모두 억원이라 축을 나눌 이유가 없습니다. 축을 둘로 두면 둘의 높이 관계가
    임의로 정해져 없는 상관을 만들어 내므로, 한 축에 두고 값을 직접 적습니다.
    """
    w, h, base = 300.0, 104.0, 74.0
    slot = w / max(len(labels), 1)
    width = min(15.0, slot * 0.2)
    peak = max(max(revenue, default=0), max(profit, default=0), 1)
    floor = min(min(profit, default=0), 0)
    span = peak - floor or 1
    zero = base - (0 - floor) / span * (base - 14)

    def top(value):
        return base - (value - floor) / span * (base - 14)

    marks, labs = "", ""
    for index, name in enumerate(labels):
        center = slot * (index + 0.5)
        for offset, value, fill, series in ((-width * 0.55, revenue[index], "url(#pxbRev)", "매출액"),
                                            (width * 0.55, profit[index], "url(#pxbProfit)", "영업이익")):
            y, height = min(top(value), zero), abs(zero - top(value))
            marks += (f'<rect x="{center + offset - width / 2:.1f}" y="{y:.1f}" width="{width:.1f}"'
                      f' height="{max(height, 1.5):.1f}" rx="3" fill="{fill}">'
                      f'<title>{_e(name)} {series} {value:,.0f}</title></rect>')
        labs += f'<text x="{center:.1f}" y="{h - 4:.0f}" text-anchor="middle">{_e(name)}</text>'
    top_value = max(max(revenue, default=0), max(profit, default=0))
    return (
        f'<svg class="pxb-chart" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none" role="img">'
        '<defs><linearGradient id="pxbRev" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{DOWN}"/><stop offset="1" stop-color="{DOWN}" stop-opacity=".45"/>'
        '</linearGradient><linearGradient id="pxbProfit" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{AMBER}"/><stop offset="1" stop-color="{AMBER}" stop-opacity=".45"/>'
        "</linearGradient></defs>"
        f'<line x1="0" y1="{zero:.1f}" x2="{w:.0f}" y2="{zero:.1f}" stroke="#E7DCC7"/>'
        f'<text x="2" y="12" fill="#7E7463">{top_value:,.0f}</text>'
        f"{marks}{labs}</svg>"
    )


def _bar_value(center: float, top: float, value: float, color: str) -> str:
    """막대 값을 눈에 보이게 적습니다. 막대가 높으면 위가 좁아 안쪽에 흰 글씨로 둡니다."""
    inside = top < 14
    return (f'<text x="{center:.1f}" y="{(top + 12) if inside else (top - 4):.1f}"'
            f' text-anchor="middle" fill="{"#FFFFFF" if inside else color}"'
            f' font-size="10" font-weight="700">{value:,.0f}</text>')


def _pair(prior: float, now: float, color: str, labels=("전년", "올해")) -> str:
    """값이 둘뿐인 비교. 선을 그으면 사이를 추세로 읽게 되므로 막대로 둡니다."""
    # 값을 막대 위에 적으므로 위쪽에 글자 자리를 남겨 둡니다. 자리를 안 남기면
    # 가장 높은 막대의 값이 막대 안으로 들어가 읽기 어려워집니다.
    w, h, base, headroom = 300.0, 62.0, 46.0, 20.0
    peak = max(abs(prior), abs(now), 1)
    floor = min(prior, now, 0)
    span = peak - floor or 1
    zero = base - (0 - floor) / span * (base - headroom)
    marks = ""
    for index, (value, label) in enumerate(zip((prior, now), labels)):
        center = w * (0.3 + index * 0.4)
        top = base - (value - floor) / span * (base - headroom)
        y, height = min(top, zero), abs(zero - top)
        marks += (f'<rect x="{center - 26:.1f}" y="{y:.1f}" width="52" height="{max(height, 2):.1f}"'
                  f' rx="4" fill="{color}" opacity="{0.45 if index == 0 else 0.95}">'
                  f'<title>{label} {value:,.0f}</title></rect>'
                  + _bar_value(center, y, value, color)
                  + f'<text x="{center:.1f}" y="{h - 3:.0f}" text-anchor="middle" fill="#7E7463"'
                    f' font-size="9">{label}</text>')
    return (f'<svg class="pxb-chart mini" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none">'
            f'<line x1="0" y1="{zero:.1f}" x2="{w:.0f}" y2="{zero:.1f}" stroke="#EFE7D8"/>{marks}</svg>')


def legend_mark(color: str, label: str) -> str:
    """색 옆에 이름을 붙여, 색만으로 계열을 구분하지 않게 합니다."""
    return ('<span style="display:inline-flex;align-items:center;gap:5px">'
            f'<i style="width:9px;height:9px;border-radius:2px;background:{color};'
            'display:inline-block"></i>' + _e(label) + "</span>")


def _card(index: int, label: str, body: str, wide_bloom: bool = False) -> str:
    petal = _bloom(index + 3, 150, "pxb-petal") if wide_bloom else ""
    return (
        f'<div class="pxb-card">{_bloom(index)}{petal}'
        f'<div class="pxb-label">{_e(label)}</div>{body}</div>'
    )




def section(label: str, note: str = "") -> str:
    """구획 제목. 어디까지가 한 묶음인지 눈으로 보이게 합니다."""
    return (f'<div class="pxb-section-h"><b>{_e(label)}</b>'
            + (f"<span>{_e(note)}</span>" if note else "") + "</div>")



GROUP_TITLES = {"A": ("A그룹 · 투자적기", "종가가 EMA 5·20·40·60 모두 위", "a"),
                "B": ("B그룹 · 투자보류", "EMA 20·40·60 위 · 단기선만 미달", "b"),
                "C": ("C그룹 · 아직보류", "중기선 아래 · 충족 2개 이하 포함", "c")}


EARNINGS_ORDER = {"양호": 0, "보통": 1, "부진": 2, "미확인": 3}


def rank_rows(rows: list) -> list:
    """같은 그룹 안에서 먼저 볼 순서.

    그룹은 이평선만으로 나누므로 한 그룹 안에서는 EMA 충족 수가 대개 같습니다.
    그래서 그 다음 잣대로 영업이익을 봅니다. 실적이 좋은 쪽을 위로 올립니다.
    """
    def key(row):
        money = row.get("earnings") or {}
        return (-row.get("met", 0), EARNINGS_ORDER.get(money.get("grade"), 3),
                -(money.get("met") or 0), row.get("name", ""))
    return sorted(rows, key=key)


SHOWN_PER_GROUP = 8      # 칸 안에 바로 보일 종목 수. 나머지는 '더 보기'로 접습니다.


def chip_label(row: dict) -> str:
    """그룹판에 적을 종목 한 줄. 이름 뒤에 판단 근거를 짧게 답니다."""
    money = (row.get("earnings") or {}).get("grade")
    note = f'EMA {row.get("met", 0)}/{row.get("total", 4)}'
    # 실적이 빠진 자리를 비워 두면 좋은 실적처럼 읽힙니다. 없다고 적되, 아직 못
    # 받은 것과 애초에 같은 잣대로 잴 수 없는 것을 나눠 적습니다.
    if money and money != "미확인":
        note += f" · 실적 {money}"
    elif any("금융업" in str(gap) for gap in row.get("gaps") or []):
        note += " · 금융업 · 기준 다름"
    else:
        note += " · 실적 미수집"
    return f'{row["name"]}  ·  {note}'


def group_buckets(graded: list) -> tuple[dict, list]:
    """그룹별로 나누고, 판정하지 못한 종목은 따로 돌려줍니다."""
    buckets = {key: [] for key in GROUP_TITLES}
    pending = []
    for row in graded or []:
        if row.get("group") in buckets:
            buckets[row["group"]].append(row)
        else:
            pending.append(row)
    return {key: rank_rows(rows) for key, rows in buckets.items()}, pending


def slot_head(key: str, count: int) -> str:
    """그룹 칸의 머리글. 색점·이름·개수·설명을 한 덩어리로 그립니다."""
    title, note, _klass = GROUP_TITLES[key]
    return (f'<div class="pxb"><div class="pxb-slot-h">'
            f'<b><i class="pxb-dot" style="background:{STATUS[key]}"></i>{title}</b>'
            f'<i>{count}</i></div><small class="pxb-slot-note">{note}</small></div>')


def board_basis(graded: list | None, pending: list | None = None) -> str:
    """그룹판 아래 한 줄. 어느 날 종가인지, 무엇을 못 셌는지 적습니다."""
    if not graded:
        return ""
    days = sorted({row.get("as_of") for row in graded if row.get("as_of")})
    periods = sorted({row.get("money_period") for row in graded if row.get("money_period")})
    basis = "종가 기준일 " + (_e(as_day(days[-1])) if days else "미확인") + " · 공공데이터포털"
    if periods:
        span = _e(periods[0]) if periods[0] == periods[-1] else f"{_e(periods[0])}~{_e(periods[-1])}"
        basis += f" · 실적 {span} 누적 · DART"
    counted = sum(1 for row in graded if (row.get("earnings") or {}).get("checks"))
    finance = sum(1 for row in graded
                  if not (row.get("earnings") or {}).get("checks")
                  and any("금융업" in str(gap) for gap in row.get("gaps") or []))
    if counted + finance < len(graded):
        basis += f" · 실적 미수집 {len(graded) - counted - finance}종목"
    if finance:
        basis += f" · 금융업 {finance}종목은 비교 기준이 달라 제외"
    note = f'<div class="pxb"><div class="pxb-note">{basis}</div></div>'
    if pending:
        reason = _e(pending[0].get("note") or pending[0].get("reason") or "자료 부족")
        note += (f'<div class="pxb"><div class="pxb-note" style="margin-top:6px">'
                 f'판정 보류 {len(pending)}종목 · {reason}</div></div>')
    return note



def stock_score(grade: dict | None) -> tuple[int, list[tuple[str, int]], str]:
    """한 종목의 판단점수. 그룹과 같은 잣대인 EMA 충족 비율만 씁니다."""
    if not grade or not grade.get("trend"):
        return 0, [], "판정 자료 부족"
    axis = grade["trend"]
    total = axis.get("total") or 4
    score = round(axis.get("met", 0) / total * 100)
    return score, [("추세 EMA", score)], grade.get("reason", "")


def frame(body: str) -> str:
    """위젯 사이에 끼워 넣는 판 하나. 스타일은 header가 이미 실었습니다."""
    return f'<div class="pxb"><div class="pxb-frame">{body}</div></div>'


def header() -> str:
    """화면 맨 위 제목 줄. 판을 열어 두므로 close_frame으로 닫습니다."""
    return (
        _CSS + '<div class="pxb"><div class="pxb-frame"><div class="pxb-top">'
        '<div class="pxb-title"><em>오늘의 <i>투자판단</i></em>'
        "<span>공식 자료로 확인한 변화와, 아직 확인이 필요한 것만 담았습니다.</span></div>"
        f'<div class="pxb-meta"><b>PLANX · STOCK INTELLIGENCE</b>{date.today():%Y년 %m월 %d일}</div>'
        "</div>"
    )


def settled(official: dict | None) -> dict:
    """확정 결산 리포트에서 판단 근거를 꺼냅니다. 자료가 모자라면 빈 칸입니다."""
    years = (official or {}).get("years") or []
    if len(years) < 2:
        return {}
    try:
        from automatic import brief
        result = brief(official)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, IndexError):
        return {}
    last, prior = years[-1], years[-2]
    prior_margin = (prior["profit"] / prior["revenue"] * 100
                    if prior.get("revenue") and prior["revenue"] > 0
                    and prior.get("profit") is not None else None)
    return {**result, "years": years[-4:], "last": last, "prior_margin": prior_margin,
            "price": official.get("price"), "price_date": official.get("price_date"),
            "basis": official.get("basis", "")}


def as_day(value) -> str:
    """20260917처럼 붙어 있는 날짜를 2026-09-17로 적습니다."""
    text = str(value or "")
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}" if len(text) == 8 and text.isdigit() else text


def price_now(grade: dict | None, official: dict | None) -> tuple[float | None, str]:
    """화면에 적을 주가 하나와 그 기준일. 종가이지 실시간 시세가 아닙니다."""
    closes = (grade or {}).get("closes") or []
    if closes:
        day = as_day((grade or {}).get("as_of"))
        return closes[-1], (f"{day} 종가" if day else "최근 거래일 종가")
    price = (official or {}).get("price")
    return (price, f'{as_day(official.get("price_date"))} 종가') if price else (None, "")


def stock_cards(report: dict | None, grade: dict | None, official: dict | None = None) -> str:
    """고른 종목 하나를 판단 카드로 보여줍니다. 확정 결산이 있으면 근거 칸이 늘어납니다."""
    report = report or {}
    book = settled(official)
    money = report.get("financial") or {}
    closes = (grade or {}).get("closes") or []
    name = report.get("name") or (grade or {}).get("name") or "종목"
    axis = (grade or {}).get("trend") or {}

    score, _rows, verdict = stock_score(grade)
    checks = axis.get("checks") or {}
    check_list = ""
    if checks:
        check_list = '<ul class="pxb-list">' + "".join(
            f'<li>{_e(name)}<em style="color:{LINE if ok else DOWN}">'
            f'{"충족" if ok else "미충족"}</em></li>' for name, ok in checks.items()) + "</ul>"
    # 규칙이 바뀌어 사라진 그룹 이름이 남아 있어도 화면이 멈추지 않게 합니다.
    group = (grade or {}).get("group")
    tone = STATUS.get(group)
    badge = (f'<span class="pxb-tag" style="color:{tone};background:{tone}1f">'
             f'{group}그룹</span>') if tone else ""
    card_score = _card(
        0, "판단점수",
        f'<div class="pxb-value">{score}<small>/100</small></div>'
        f'<p class="pxb-sub">{_e(verdict)}</p>{check_list}{badge}', wide_bloom=True)

    if money:
        profit_text = growth(money["operating_profit"], money["prior_operating_profit"])
        revenue_text = growth(money["revenue"], money["prior_revenue"])
        period = f'{_e(money.get("prior_period", ""))} → {_e(money.get("period", ""))}'
        basis = " · ".join(x for x in (money.get("basis"), money.get("currency"),
                                       money.get("unit")) if x)
        if basis:
            period += f' · {_e(basis)} 누적'
        unit = _e(money.get("unit", ""))
        # 증감률만 적으면 흑자 전환처럼 %로 말할 수 없는 변화의 크기를 알 수 없습니다.
        profit_amount = (f'<p class="pxb-sub" style="margin-top:4px">'
                         f'{money["prior_operating_profit"]:,.0f} → '
                         f'{money["operating_profit"]:,.0f} {unit}</p>')
        revenue_amount = (f'<p class="pxb-sub" style="margin-top:4px">'
                          f'{money["prior_revenue"]:,.0f} → {money["revenue"]:,.0f} {unit}</p>')
    else:
        profit_text = revenue_text = "조사 필요"
        period = "실적 미수집"
        profit_amount = revenue_amount = ""
    profit_color = DOWN if profit_text.startswith("-") or "적자" in profit_text else UP
    revenue_color = DOWN if revenue_text.startswith("-") or "적자" in revenue_text else UP

    card_profit = _card(
        1, "영업이익 성장",
        f'<div class="pxb-value" style="color:{profit_color}">{_e(profit_text)}</div>'
        f'<p class="pxb-sub">{period}</p>{profit_amount}'
        + (_pair(money["prior_operating_profit"], money["operating_profit"], profit_color,
                 (money.get("prior_period", "전년"), money.get("period", "올해"))) if money else ""))
    card_revenue = _card(
        2, "매출 성장",
        f'<div class="pxb-value" style="color:{revenue_color}">{_e(revenue_text)}</div>'
        f'<p class="pxb-sub">{period}</p>{revenue_amount}'
        + (_pair(money["prior_revenue"], money["revenue"], revenue_color,
                 (money.get("prior_period", "전년"), money.get("period", "올해"))) if money else ""))

    if len(closes) >= 20:
        lines = axis.get("ema") or {}
        span = " ~ ".join(x for x in (as_day((grade or {}).get("from_date")),
                                      as_day((grade or {}).get("as_of"))) if x)
        note = f'{_e(name)} · {_e(span) or f"최근 {len(closes)}거래일"}'
        note += f' · {len(closes)}거래일 · 이평선 {axis.get("grade") or "판정 전"}'
        if lines:
            note += ('<br><span style="font-size:11px;color:#7E7463">'
                     + " · ".join(f"{k} {v:,.0f}" for k, v in lines.items()) + "</span>")
        if axis.get("checks"):
            below = [k.replace("종가 > ", "") for k, ok in axis["checks"].items() if not ok]
            note += ('<br><span style="font-size:11px;color:#7E7463">'
                     + ("종가가 네 이평선 모두 위" if not below
                        else "종가가 아래에 둔 선 · " + ", ".join(below)) + "</span>")
        flow = f'<p class="pxb-sub" style="margin-top:12px">{note}</p>' + _spark(closes, LINE, "t")
    else:
        flow = ('<p class="pxb-sub" style="margin-top:12px">일별 종가를 모으는 중입니다. '
                '이동평균 60일선에는 62거래일이 필요합니다.</p>')
    card_trend = _card(3, "성장 흐름", flow)

    if book:
        years = book["years"]
        chart = _bars([str(y["year"]) for y in years],
                      [y["revenue"] for y in years], [y["profit"] for y in years])
        note = f'단위 억원 · 확정 결산 · {years[0]["year"]}~{years[-1]["year"]}'
    elif money:
        chart = _bars([money.get("prior_period", "이전"), money.get("period", "최근")],
                      [money["prior_revenue"], money["revenue"]],
                      [money["prior_operating_profit"], money["operating_profit"]])
        note = f'단위 {_e(money.get("unit", ""))} · 같은 축'
    else:
        chart, note = "", "실적이 모이면 표시합니다."
    swatches = legend_mark(DOWN, "매출액") + "&nbsp;&nbsp;" + legend_mark(AMBER, "영업이익")
    card_earnings = _card(4, "실적 추이",
                          f'<p class="pxb-sub" style="margin-top:12px">{swatches} · {note}</p>{chart}')

    price, price_note = price_now(grade, official)
    extra = ""
    if book:
        extra = _settled_cards(book, price)

    value = report.get("valuation") or {}
    if value:
        low, high, now = value["low"], value["high"], value["current_price"]
        mark = min(max((now - low) / max(high - low, 1), 0), 1) * 100
        labels = "".join(f"<span>{v:,.0f}</span>" for v in (low, value["base"], high))
        value_note = _e(str(value.get("method", "")))[:40]
        head_text, value_title = f"{now:,.0f}원", "적정가치 범위"
    elif len(closes) >= 20:
        low, high, now = min(closes), max(closes), closes[-1]
        mark = min(max((now - low) / (high - low) * 100, 2), 98) if high > low else 50
        labels = "".join(f"<span>{v:,.0f}</span>" for v in (low, (low + high) / 2, high))
        move = ""
        if len(closes) >= 2 and closes[-2]:
            gap = now - closes[-2]
            tone = DOWN if gap < 0 else UP
            move = (f' <small style="font-size:14px;color:{tone}">{gap:+,.0f}'
                    f' ({gap / closes[-2] * 100:+.2f}%)</small>')
        value_note = (f"{_e(price_note)} · 최근 {len(closes)}거래일 범위의 {mark:.0f}% 지점 · "
                      "적정주가가 아닙니다.")
        head_text, value_title = f"{now:,.0f}원{move}", "주가 · 가격 범위 속 위치"
    else:
        mark, head_text, value_title = 50, "자료 대기", "가격 범위 속 위치"
        value_note, labels = "일별 종가가 모이면 표시합니다.", "<span>-</span><span>-</span><span>-</span>"
    card_value = _card(
        5, value_title,
        f'<div class="pxb-value" style="font-size:32px">{head_text}</div>'
        f'<div class="pxb-range"><div class="pxb-range-line"><u style="left:0;right:0"></u>'
        f'<i style="left:{mark:.0f}%"></i></div><div class="pxb-range-lab">{labels}</div></div>'
        f'<p class="pxb-sub" style="margin-top:14px">{value_note}</p>')

    return (f'<div class="pxb-grid">{card_score}{card_profit}{card_revenue}'
            f"{card_trend}{card_earnings}{card_value}{extra}</div>")


def _settled_cards(book: dict, price: float | None) -> str:
    """확정 결산에서 나온 판단 근거 세 칸: 성장률·영업이익률·역사적 참고가."""
    rows = ""
    for label, value in (("매출 성장률", book.get("revenue_growth")),
                         ("영업이익 성장률", book.get("profit_growth"))):
        if value is None:
            rows += f'<li>{label}<b>자료 부족</b></li>'
        else:
            rows += (f'<li>{label}<b style="color:{DOWN if value < 0 else UP}">'
                     f'{value:+.1f}%</b></li>')
    last = book.get("last") or {}
    rows += (f'<li>{last.get("year", "")}년 매출<b>{last.get("revenue", 0):,.0f} 억원</b></li>'
             f'<li>{last.get("year", "")}년 영업이익<b>{last.get("profit", 0):,.0f} 억원</b></li>')
    card_growth = _card(6, "확정 결산 성장률",
                        f'<p class="pxb-sub" style="margin-top:12px">'
                        f'{_e(book.get("basis", ""))} · 단위 억원</p><ul class="pxb-list">{rows}</ul>')

    margin, prior = book.get("margin"), book.get("prior_margin")
    if margin is None:
        card_margin = _card(7, "영업이익률",
                            '<div class="pxb-value">자료 부족</div>'
                            '<p class="pxb-sub">확정 결산 매출과 영업이익이 필요합니다.</p>')
    else:
        year = (book.get("last") or {}).get("year")
        step = "" if prior is None else f"{prior:.1f}% → {margin:.1f}%"
        if step and year:
            step += f" · {year}년 확정 결산"
        card_margin = _card(
            7, "영업이익률",
            f'<div class="pxb-value">{margin:.1f}<small>%</small></div>'
            f'<p class="pxb-sub">{_e(step) or "최근 확정 결산 기준"}</p>'
            + (_pair(prior, margin, LINE, ("전년", "최근")) if prior is not None else ""))

    fair = book.get("fair")
    if not fair:
        card_fair = _card(8, "역사적 참고가",
                          '<div class="pxb-value" style="font-size:26px">산출 보류</div>'
                          f'<p class="pxb-sub">{_e(book.get("fair_reason", ""))}</p>')
    else:
        low, base, high = fair["low"], fair["base"], fair["high"]
        here = price or base
        mark = min(max((here - low) / (high - low) * 100, 2), 98) if high > low else 50
        labels = "".join(f"<span>{v:,.0f}</span>" for v in (low, base, high))
        card_fair = _card(
            8, "역사적 참고가",
            f'<div class="pxb-value" style="font-size:30px">{base:,.0f}<small>원</small></div>'
            f'<p class="pxb-sub">중간 참고값 · 주가와 {fair["gap"]:+.1f}% 차이</p>'
            f'<div class="pxb-range"><div class="pxb-range-line"><u style="left:0;right:0"></u>'
            f'<i style="left:{mark:.0f}%"></i></div><div class="pxb-range-lab">{labels}</div></div>'
            '<p class="pxb-sub" style="margin-top:12px">과거 시가총액/영업이익 배수를 최근 결산 '
            '이익에 적용한 참고 가격 · 매수·매도 신호가 아닙니다.</p>')
    return card_growth + card_margin + card_fair


RULE_TEXT = ("일봉 종가가 EMA 5·20·40·60 각각의 위에 있는지 네 가지를 셉니다 · "
             "넷 다 충족 A · 20·40·60만 충족 B · 그 밖 C · "
             "같은 그룹 안에서는 영업이익이 좋은 순서 · 매수·매도 신호가 아닙니다")


def close_frame() -> str:
    """열어 둔 판을 닫습니다."""
    return "</div></div>"
