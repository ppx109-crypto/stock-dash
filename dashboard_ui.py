"""PlanX 첫 화면 · 다크 인텔리전스 콕핏.

전체 화면을 하나의 HTML/SVG 블록으로 직접 그립니다. Streamlit 기본 컴포넌트를
쓰지 않기 때문에 레이아웃과 차트를 픽셀 단위로 제어할 수 있습니다.

시장 지수·주가는 시장 API 연결 전이라 라벨이 붙은 샘플입니다.
research/ 폴더에 조사 결과가 있으면 점수·실적·브리핑은 실제 조사값으로 채웁니다.
"""
from __future__ import annotations

from datetime import date
import html

import streamlit as st

from chat_research import growth

UP = "#FF6B6B"      # 국내 관례: 상승 = 빨강
DOWN = "#5AA9FF"    # 하락 = 파랑
GOLD = "#E3BC72"
MINT = "#3DD68C"
SAMPLE = "화면 구성 예시 · 샘플"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&display=swap');
@keyframes pxdPulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.25;transform:scale(.6)}}
@keyframes pxdTape{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@keyframes pxdSheen{from{background-position:0% 50%}to{background-position:200% 50%}}
@keyframes pxdRise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes pxdDraw{from{stroke-dashoffset:var(--len)}to{stroke-dashoffset:0}}

.pxd{position:relative;margin:0 0 26px;padding:26px 28px 24px;border-radius:20px;overflow:hidden;
  font-family:Pretendard,"Noto Sans KR","Apple SD Gothic Neo",sans-serif;color:#E8EFF7;
  background:radial-gradient(1200px 520px at 12% -12%,#1C3350 0%,transparent 62%),
             radial-gradient(900px 440px at 96% 8%,#2A2136 0%,transparent 58%),
             linear-gradient(168deg,#0B1420 0%,#0D1A28 52%,#0A121D 100%);
  border:1px solid rgba(227,188,114,.22);
  box-shadow:0 40px 90px rgba(8,16,26,.42),inset 0 1px 0 rgba(255,255,255,.06);
  animation:pxdRise .6s ease both}
.pxd:before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.5;
  background-image:linear-gradient(rgba(255,255,255,.028) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.028) 1px,transparent 1px);
  background-size:46px 46px;mask-image:radial-gradient(900px 420px at 50% 0%,#000,transparent 78%)}
.pxd *{box-sizing:border-box}
.pxd h3,.pxd h4{margin:0;font-weight:700}

/* 헤더 */
.pxd-top{position:relative;display:flex;align-items:flex-end;justify-content:space-between;gap:18px;
  padding-bottom:16px;border-bottom:1px solid rgba(227,188,114,.18)}
.pxd-brand{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.pxd-brand em{font:700 38px/1 "Playfair Display",Georgia,serif;font-style:normal;letter-spacing:-.5px;
  background:linear-gradient(100deg,#C9A24D,#F6E3B4 42%,#C9A24D 76%);background-size:220% auto;
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;
  animation:pxdSheen 7s linear infinite}
.pxd-brand b{font-size:12.5px;letter-spacing:.34em;color:#9FB3C8}
.pxd-brand small{font-size:11.5px;color:#6E839A}
.pxd-meta{display:flex;align-items:center;gap:10px;font-size:12px;color:#9FB3C8;white-space:nowrap}
.pxd-dot{width:7px;height:7px;border-radius:50%;background:#3DD68C;box-shadow:0 0 0 4px rgba(61,214,140,.16);
  animation:pxdPulse 1.9s ease-in-out infinite}
.pxd-chip{padding:4px 11px;border-radius:999px;font-size:10px;font-weight:800;letter-spacing:.1em;
  color:#F0D9A6;border:1px solid rgba(227,188,114,.42);background:rgba(227,188,114,.1)}

/* 티커 */
.pxd-tape{position:relative;margin:14px 0 16px;overflow:hidden;
  mask-image:linear-gradient(90deg,transparent,#000 4%,#000 96%,transparent)}
.pxd-tape-track{display:flex;width:max-content;animation:pxdTape 44s linear infinite}
.pxd-tape span{display:inline-flex;align-items:center;gap:8px;padding:0 20px;font-size:11.5px;color:#93A7BC;
  border-right:1px solid rgba(255,255,255,.06)}
.pxd-tape b{font:600 13px Georgia,serif;color:#E8EFF7}

/* 시장 타일 */
.pxd-markets{display:grid;grid-template-columns:repeat(5,1fr);gap:11px}
.pxd-tile{position:relative;padding:13px 14px 0;border-radius:13px;overflow:hidden;
  background:linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.018));
  border:1px solid rgba(255,255,255,.08);transition:border-color .25s,transform .25s}
.pxd-tile:hover{transform:translateY(-3px);border-color:rgba(227,188,114,.4)}
.pxd-tile-h{display:flex;align-items:center;justify-content:space-between;font-size:10.5px;
  letter-spacing:.12em;font-weight:800;color:#8FA3B8}
.pxd-tile-v{display:flex;align-items:baseline;justify-content:space-between;margin:5px 0 2px}
.pxd-tile-v b{font:700 24px/1 Georgia,serif;letter-spacing:-.6px;color:#F2F7FC}
.pxd-tile-v i{font-style:normal;font-size:11.5px;font-weight:800}
.pxd-tile svg{display:block;width:100%;height:42px;margin:0 -14px;padding:0 0 0 0}

.pxd-note{margin:10px 2px 0;font-size:10.5px;color:#6B7F94;letter-spacing:.01em}

/* 섹션 바 */
.pxd-bar{display:flex;align-items:center;justify-content:space-between;gap:20px;margin:22px 0 13px;flex-wrap:wrap}
.pxd-bar h3{font-size:19px;letter-spacing:-.3px}
.pxd-bar h3 i{font-style:normal;color:#E3BC72}
.pxd-steps{display:flex;align-items:center;gap:7px;font-size:11.5px;color:#8FA3B8}
.pxd-steps span{padding:7px 18px;border-radius:9px;background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.07)}
.pxd-steps b{padding:7px 20px;border-radius:9px;color:#17202B;
  background:linear-gradient(135deg,#F0D08A,#C9A24D);box-shadow:0 8px 20px rgba(201,162,77,.32)}

/* 점수 · 시그널 */
.pxd-grid{display:grid;grid-template-columns:1.22fr repeat(5,1fr);gap:11px}
.pxd-card{position:relative;padding:15px 16px;border-radius:14px;overflow:hidden;min-height:216px;
  background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.08);transition:transform .25s,border-color .25s,box-shadow .25s}
.pxd-card:hover{transform:translateY(-4px);border-color:rgba(227,188,114,.36);
  box-shadow:0 22px 44px rgba(5,10,18,.5)}
.pxd-score{background:linear-gradient(165deg,rgba(227,188,114,.16),rgba(255,255,255,.03) 46%,rgba(255,255,255,.02));
  border-color:rgba(227,188,114,.32);display:flex;flex-direction:column}
.pxd-score-h{display:flex;align-items:baseline;justify-content:space-between;font-size:12px;
  letter-spacing:.06em;color:#CBD8E6;font-weight:700}
.pxd-score-h em{font-style:normal;font-size:10px;color:#93A7BC}
.pxd-gaugewrap{display:flex;align-items:center;gap:14px;margin:8px 0 10px}
.pxd-gauge{width:104px;height:104px;flex:none}
.pxd-gauge-v{font:700 30px "Playfair Display",Georgia,serif;fill:#F6E3B4}
.pxd-gauge-u{font-size:9px;fill:#8FA3B8;letter-spacing:.1em}
.pxd-verdict b{display:block;font:700 17px/1.3 Pretendard,sans-serif;color:#F2F7FC}
.pxd-verdict span{display:block;margin-top:5px;font-size:10.5px;line-height:1.6;color:#8FA3B8}
.pxd-rows{margin-top:auto;display:flex;flex-direction:column;gap:6px}
.pxd-row{display:grid;grid-template-columns:62px 1fr 26px;align-items:center;gap:9px;font-size:10.5px;color:#9FB3C8}
.pxd-row i{height:4px;border-radius:4px;background:rgba(255,255,255,.08);overflow:hidden;font-style:normal;display:block}
.pxd-row i u{display:block;height:100%;border-radius:4px;text-decoration:none;
  background:linear-gradient(90deg,#C9A24D,#F0D08A)}
.pxd-row b{text-align:right;color:#E8EFF7;font-variant-numeric:tabular-nums}

.pxd-sig-h{display:flex;align-items:center;justify-content:space-between;gap:8px}
.pxd-sig-h b{font-size:13px;color:#EAF1F8}
.pxd-sig-h span{font-size:9.5px;font-weight:800;padding:3px 9px;border-radius:999px;white-space:nowrap}
.pxd-card h4{margin:15px 0 6px;font-size:14.5px;color:#F2F7FC;letter-spacing:-.2px}
.pxd-card p{margin:0;font-size:11px;line-height:1.6;color:#8093A8;min-height:52px}
.pxd-bars{display:flex;align-items:flex-end;gap:6px;height:52px;margin-top:6px}
.pxd-bars i{flex:1;border-radius:3px 3px 0 0;display:block;opacity:.92}

/* 메인 */
.pxd-main{display:grid;grid-template-columns:2.4fr 1fr 1.05fr;gap:11px;margin-top:14px;align-items:stretch}
.pxd-panel{position:relative;border-radius:14px;overflow:hidden;
  background:linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.018));
  border:1px solid rgba(255,255,255,.08)}
.pxd-panel-h{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 15px;
  border-bottom:1px solid rgba(255,255,255,.06);font-size:12px;font-weight:800;color:#DCE7F2}
.pxd-panel-h span{font-size:9.5px;font-weight:600;color:#7B8FA5;letter-spacing:.04em}
.pxd-focus{display:flex;align-items:baseline;gap:13px;flex-wrap:wrap}
.pxd-focus b{font:700 21px "Playfair Display",Georgia,serif;color:#F5FAFF}
.pxd-focus small{font-size:10px;color:#7B8FA5;letter-spacing:.08em}
.pxd-focus em{font-style:normal;font:700 19px Georgia,serif}
.pxd-legend{display:flex;gap:14px;padding:12px 16px 0;font-size:10.5px;color:#93A7BC}
.pxd-legend i{display:inline-block;width:14px;height:3px;border-radius:3px;margin-right:6px;vertical-align:middle}
.pxd-chart{display:block;width:100%;height:268px}
.pxd-chart text{fill:#7B8FA5;font-size:10px}
.pxd-chart .grid{stroke:rgba(255,255,255,.06)}

.pxd-heat{display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:1fr;gap:1px;
  height:calc(100% - 45px);background:rgba(255,255,255,.05)}
.pxd-heat div{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;
  padding:14px 4px;font-size:10.5px;color:#0C1620;font-weight:700;transition:transform .2s}
.pxd-heat div:hover{transform:scale(1.06);z-index:2}
.pxd-heat b{font:700 12.5px Georgia,serif}

.pxd-watch{display:flex;flex-direction:column;justify-content:space-between;
  height:calc(100% - 45px);padding:2px 14px 6px}
.pxd-watch-row{display:grid;grid-template-columns:1fr auto 58px;align-items:center;gap:8px;
  padding:10.5px 2px;border-bottom:1px solid rgba(255,255,255,.055);font-size:11px;color:#C4D3E2}
.pxd-watch-row:last-child{border-bottom:0}
.pxd-watch-row b{font:600 11.5px Georgia,serif;color:#E8EFF7}
.pxd-watch-row em{font-style:normal;font-weight:800;text-align:right;font-size:11px}
.pxd-star{color:#E3BC72;margin-right:6px}

/* 하단 */
.pxd-bottom{display:grid;grid-template-columns:1.1fr 1fr 1.32fr;gap:11px;margin-top:11px}
.pxd-mini{display:block;width:100%;height:150px}
.pxd-mini text{fill:#7B8FA5;font-size:9.5px}
.pxd-val{padding:20px 18px 16px;text-align:center}
.pxd-val b{font:700 17px Georgia,serif;color:#F5FAFF}
.pxd-val-line{position:relative;height:8px;border-radius:8px;margin:26px 6px 9px;background:rgba(255,255,255,.08)}
.pxd-val-line u{position:absolute;top:0;bottom:0;border-radius:8px;text-decoration:none;
  background:linear-gradient(90deg,rgba(61,214,140,.5),#3DD68C)}
.pxd-val-line i{position:absolute;top:-5px;width:16px;height:16px;border-radius:50%;margin-left:-8px;
  background:linear-gradient(135deg,#F6E3B4,#C9A24D);border:2px solid #0D1A28;
  box-shadow:0 0 0 4px rgba(227,188,114,.18)}
.pxd-val-lab{display:flex;justify-content:space-between;font-size:9.5px;color:#7B8FA5}
.pxd-val small{display:block;margin-top:14px;font-size:9.5px;color:#6B7F94}
.pxd-brief{display:flex;gap:12px;padding:15px 16px}
.pxd-ai{flex:none;width:32px;height:32px;border-radius:9px;display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:800;color:#17202B;background:linear-gradient(135deg,#F0D08A,#C9A24D)}
.pxd-brief ul{margin:0;padding-left:16px}
.pxd-brief li{font-size:11px;line-height:1.75;color:#A9BACD;margin-bottom:5px}

.pxd-edu{display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin-top:11px;padding:13px 17px;
  border-radius:13px;border:1px solid rgba(255,255,255,.07);
  background:linear-gradient(120deg,rgba(255,255,255,.055),rgba(255,255,255,.015));font-size:11.5px;color:#93A7BC}
.pxd-edu b{color:#EAF1F8}
.pxd-pens{display:flex;gap:9px;margin-left:auto}
.pxd-pens i{width:19px;height:5px;border-radius:5px;transform:rotate(-42deg);background:#FF6B6B}
.pxd-pens i:nth-child(2){background:#5AA9FF}.pxd-pens i:nth-child(3){background:#3DD68C}
.pxd-pens i:nth-child(4){background:#E3BC72}

.px-live-divider{display:flex;align-items:center;gap:12px;margin:26px 0 8px;color:#80612f;
  font-size:11px;font-weight:800;letter-spacing:.08em}
.px-live-divider:before,.px-live-divider:after{content:"";height:1px;background:#d9cbb5;flex:1}

@media(max-width:1280px){
  .pxd-grid{grid-template-columns:repeat(3,1fr)}
  .pxd-main,.pxd-bottom{grid-template-columns:1fr 1fr}
  .pxd-main>.pxd-panel:first-child{grid-column:1/-1}
  .pxd-bottom>.pxd-panel:last-child{grid-column:1/-1}
}
@media(max-width:820px){
  .pxd{padding:20px 16px}
  .pxd-markets{grid-template-columns:repeat(2,1fr)}
  .pxd-grid,.pxd-main,.pxd-bottom{grid-template-columns:1fr}
  .pxd-main>.pxd-panel:first-child,.pxd-bottom>.pxd-panel:last-child{grid-column:auto}
  .pxd-brand em{font-size:30px}
}
</style>
"""

_MARKETS = [
    ("KOSPI", "2,482.36", "+0.75%", UP, [42, 44, 43, 47, 46, 50, 49, 53, 51, 56]),
    ("KOSDAQ", "723.61", "+0.89%", UP, [35, 37, 36, 39, 42, 41, 44, 43, 46, 48]),
    ("USD/KRW", "1,386.20", "-0.29%", DOWN, [52, 50, 53, 51, 54, 49, 48, 46, 47, 44]),
    ("WTI", "67.24", "+0.93%", UP, [32, 34, 33, 37, 36, 39, 40, 43, 41, 45]),
    ("GOLD", "2,577.30", "+0.48%", UP, [45, 46, 48, 47, 50, 51, 50, 53, 52, 56]),
]

_TAPE = [
    ("삼성전자", "72,400", "+2.69%"), ("SK하이닉스", "198,500", "+1.53%"),
    ("현대차", "273,000", "-0.36%"), ("LG에너지솔루션", "402,000", "-1.12%"),
    ("NAVER", "215,000", "+1.42%"), ("카카오", "39,850", "+0.76%"),
    ("삼성바이오로직스", "812,000", "+0.61%"), ("기아", "122,400", "+0.82%"),
    ("POSCO홀딩스", "358,500", "-0.44%"), ("셀트리온", "186,300", "+1.05%"),
]

_SIGNALS = [
    ("매크로", "◎", "중립", "#B7C6D6", "안정적인 흐름 지속", "금리와 유동성의 방향을 확인합니다.", [28, 34, 40, 48, 56]),
    ("성장산업", "◒", "긍정", MINT, "AI 반도체 수요 확대", "산업 성장과 투자 계획을 함께 봅니다.", [24, 34, 47, 62, 82]),
    ("수출·수주", "▰", "긍정", MINT, "수출 개선세 지속", "수출·수주가 매출로 전환되는지 봅니다.", [26, 38, 49, 63, 86]),
    ("실적 성장", "▥", "긍정", MINT, "견조한 이익 성장", "매출보다 영업이익의 속도를 봅니다.", [32, 42, 50, 61, 84]),
    ("수급 강도", "↗", "긍정", DOWN, "매수 우위 지속", "기관과 외국인의 방향을 확인합니다.", [30, 43, 58, 76, 60]),
]

_SECTORS = [
    ("반도체", "+2.8%", "#2FCB84"), ("IT하드웨어", "+1.5%", "#54D19A"),
    ("자동차", "+1.2%", "#6FD8AB"), ("2차전지", "-0.8%", "#F3A6A6"),
    ("바이오", "+0.6%", "#9EE2C2"), ("인터넷", "+1.9%", "#42CE8F"),
    ("금융", "+0.4%", "#BDEBD6"), ("에너지", "-0.3%", "#F7C7C7"),
    ("화학", "-1.1%", "#EE9B9B"), ("기계", "+0.7%", "#ACE5CC"),
    ("건설", "-0.6%", "#F5BDBD"), ("통신", "+0.2%", "#CFEFE0"),
]

_WATCH = [
    ("삼성전자", "72,400", "+2.69%"), ("SK하이닉스", "198,500", "+1.53%"),
    ("현대차", "273,000", "-0.36%"), ("기아", "122,400", "+0.82%"),
    ("NAVER", "215,000", "+1.42%"), ("카카오", "39,850", "+0.76%"),
]

_FOCUS = [100, 103, 106, 105, 110, 113, 111, 116, 120, 119, 124, 128,
          132, 130, 137, 142, 140, 148, 151, 147, 158, 163, 160, 166]
_KOSPI = [100, 102, 104, 103, 106, 107, 106, 109, 111, 110, 112, 115,
          117, 116, 119, 121, 120, 123, 124, 122, 126, 128, 127, 130]
_SECTOR = [100, 104, 108, 107, 112, 116, 114, 121, 126, 124, 131, 136,
           141, 138, 146, 153, 151, 160, 166, 161, 172, 179, 176, 185]


def _e(value) -> str:
    return html.escape(str(value))


def _points(values: list[float], width: float, height: float, pad: float = 0.0) -> list[tuple[float, float]]:
    low, high = min(values), max(values)
    span = (high - low) or 1
    step = width / max(len(values) - 1, 1)
    usable = height - pad * 2
    return [(i * step, pad + usable - (v - low) / span * usable) for i, v in enumerate(values)]


def _spark_svg(values: list[float], color: str, key: str) -> str:
    w, h = 240.0, 46.0
    pts = _points(values, w, h, pad=7)
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"M0,{h} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" L{w},{h} Z"
    return (
        f'<svg viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none">'
        f'<defs><linearGradient id="sg{key}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{color}" stop-opacity=".3"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
        f'<path d="{area}" fill="url(#sg{key})"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2"'
        f' stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def _gauge_svg(score: int) -> str:
    dash = 314.16 * min(max(score, 0), 100) / 100
    return (
        '<svg class="pxd-gauge" viewBox="0 0 120 120">'
        '<defs><linearGradient id="gaugeGold" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#F6E3B4"/><stop offset="1" stop-color="#C9A24D"/></linearGradient>'
        '<filter id="gaugeGlow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="3.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        '<circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="9"/>'
        f'<circle cx="60" cy="60" r="50" fill="none" stroke="url(#gaugeGold)" stroke-width="9"'
        f' stroke-linecap="round" stroke-dasharray="{dash:.1f} 314.16" transform="rotate(-90 60 60)"'
        f' filter="url(#gaugeGlow)" style="--len:{dash:.1f};animation:pxdDraw 1.1s ease-out both"/>'
        f'<text class="pxd-gauge-v" x="60" y="62" text-anchor="middle">{score}</text>'
        '<text class="pxd-gauge-u" x="60" y="79" text-anchor="middle">SCORE /100</text></svg>'
    )


def _line_chart_svg(label: str) -> str:
    w, h = 880.0, 268.0
    left, right, top, bottom = 40.0, 14.0, 16.0, 30.0
    plot_w, plot_h = w - left - right, h - top - bottom
    pool = _FOCUS + _KOSPI + _SECTOR
    low, high = min(pool), max(pool)
    span = (high - low) or 1
    step = plot_w / (len(_FOCUS) - 1)

    def coords(values):
        return [(left + i * step, top + plot_h - (v - low) / span * plot_h) for i, v in enumerate(values)]

    grid = "".join(
        f'<line class="grid" x1="{left}" y1="{top + plot_h * f:.1f}" x2="{w - right}" y2="{top + plot_h * f:.1f}"/>'
        f'<text x="{left - 8}" y="{top + plot_h * f + 3.5:.1f}" text-anchor="end">{high - span * f:.0f}</text>'
        for f in (0, 0.25, 0.5, 0.75, 1)
    )
    ticks = "".join(
        f'<text x="{left + i * step:.1f}" y="{h - 9:.0f}" text-anchor="middle">{24 + i // 12}.{i % 12 + 1:02d}</text>'
        for i in range(0, len(_FOCUS), 4)
    )
    focus = coords(_FOCUS)
    area = (f'M{left},{top + plot_h} L' + " L".join(f"{x:.1f},{y:.1f}" for x, y in focus)
            + f" L{w - right},{top + plot_h} Z")
    series = ""
    for values, color, width in ((_SECTOR, GOLD, 2.0), (_KOSPI, DOWN, 2.0), (_FOCUS, MINT, 2.8)):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords(values))
        glow = ' filter="url(#lineGlow)"' if color == MINT else ""
        series += (f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"'
                   f' stroke-linejoin="round" stroke-linecap="round"{glow}/>')
    tip_x, tip_y = focus[-1]
    return (
        f'<svg class="pxd-chart" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none">'
        '<defs><linearGradient id="focusFill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{MINT}" stop-opacity=".32"/>'
        f'<stop offset="1" stop-color="{MINT}" stop-opacity="0"/></linearGradient>'
        '<filter id="lineGlow" x="-20%" y="-40%" width="140%" height="180%">'
        '<feGaussianBlur stdDeviation="3.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        f"{grid}{ticks}"
        f'<path d="{area}" fill="url(#focusFill)"/>{series}'
        f'<circle cx="{tip_x:.1f}" cy="{tip_y:.1f}" r="4.5" fill="{MINT}" filter="url(#lineGlow)"/>'
        f'<circle cx="{tip_x:.1f}" cy="{tip_y:.1f}" r="9" fill="none" stroke="{MINT}" stroke-opacity=".35"/>'
        "</svg>"
    )


def _earnings_svg(labels: list[str], revenue: list[float], profit: list[float]) -> str:
    w, h = 420.0, 150.0
    top, bottom, side = 16.0, 26.0, 18.0
    plot_h = h - top - bottom
    slot = (w - side * 2) / max(len(labels), 1)
    bar_w = min(38.0, slot * 0.42)
    peak_r = max(revenue) or 1
    low_p, high_p = min(profit), max(profit)
    span_p = (high_p - low_p) or 1
    bars, line_pts, labs = "", [], ""
    for i, name in enumerate(labels):
        cx = side + slot * (i + 0.5)
        height = revenue[i] / peak_r * plot_h * 0.86
        bars += (f'<rect x="{cx - bar_w / 2:.1f}" y="{top + plot_h - height:.1f}" width="{bar_w:.1f}"'
                 f' height="{height:.1f}" rx="5" fill="url(#barFill)"/>')
        line_pts.append((cx, top + plot_h - ((profit[i] - low_p) / span_p * 0.56 + 0.22) * plot_h))
        labs += f'<text x="{cx:.1f}" y="{h - 8:.0f}" text-anchor="middle">{_e(name)}</text>'
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in line_pts)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{GOLD}"/>' for x, y in line_pts)
    return (
        f'<svg class="pxd-mini" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none">'
        '<defs><linearGradient id="barFill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{DOWN}" stop-opacity=".95"/>'
        f'<stop offset="1" stop-color="{DOWN}" stop-opacity=".25"/></linearGradient></defs>'
        f'{bars}<polyline points="{poly}" fill="none" stroke="{GOLD}" stroke-width="2.4"'
        f' stroke-linejoin="round"/>{dots}{labs}</svg>'
    )


def _score_of(reports: list[dict]) -> tuple[int, list[tuple[str, int]], str, str]:
    """조사 결과가 있으면 규칙 기반 점수, 없으면 샘플 점수를 돌려줍니다."""
    if not reports:
        rows = [("매크로", 76), ("산업 경쟁력", 82), ("실적", 80), ("밸류에이션", 70)]
        return 78, rows, "관망 우위", "조사 결과가 쌓이면 실제 값으로 바뀝니다"

    def grade(current, prior, weight) -> int:
        if not prior or prior <= 0:
            return 50
        return int(min(max(50 + (current / prior - 1) * 100 * weight, 0), 100))

    money = [r["financial"] for r in reports if r.get("financial")]
    revenue = int(sum(grade(f["revenue"], f["prior_revenue"], 2.0) for f in money) / len(money)) if money else 50
    profit = int(sum(grade(f["operating_profit"], f["prior_operating_profit"], 1.0) for f in money) / len(money)) if money else 50
    gaps = sum(len(r.get("data_gaps") or []) for r in reports)
    quality = int(min(max(100 - gaps * 8, 0), 100))
    peers = int(min(60 + sum(1 for r in reports if r.get("peers")) * 10, 100))
    rows = [("매출 성장", revenue), ("이익 성장", profit), ("경쟁 비교", peers), ("자료 충실도", quality)]
    total = int(sum(v for _, v in rows) / len(rows))
    verdict = "이익 성장 우위" if profit >= 70 else ("점검 필요" if profit < 45 else "중립 구간")
    note = f"공식 자료 {len(reports)}건 · 확인 필요 {gaps}건 반영"
    return total, rows, verdict, note


def _growth_text(report: dict) -> str:
    f = report.get("financial") or {}
    return growth(f["operating_profit"], f["prior_operating_profit"]) if f else "조사 필요"


def _brief_lines(report: dict | None) -> list[str]:
    lines: list[str] = []
    if report:
        for key in ("summary", "business"):
            text = ((report.get(key) or {}).get("text") or "").strip()
            if text:
                lines.append(text[:118])
        lines += [f"확인 필요 · {g}" for g in (report.get("data_gaps") or [])]
    return lines[:3] or [
        "반도체 수요 확대와 영업이익 개선을 함께 확인합니다.",
        "환율과 메모리 가격 변화가 다음 실적의 핵심 변수입니다.",
        "현재 가격은 역사적 범위와 전망치를 구분해 판단해야 합니다.",
    ]


def render_decision_dashboard(details: dict) -> None:
    """첫 화면 다크 콕핏을 하나의 HTML 블록으로 그립니다."""
    st.markdown(_CSS, unsafe_allow_html=True)
    reports = sorted((details or {}).values(), key=lambda r: r.get("as_of", ""), reverse=True)
    focus = reports[0] if reports else None
    score, rows, verdict, score_note = _score_of(reports)

    tape = "".join(
        f'<span>{_e(name)} <b>{price}</b>'
        f'<i style="font-style:normal;color:{UP if change.startswith("+") else DOWN}">{change}</i></span>'
        for name, price, change in _TAPE
    )
    tiles = "".join(
        f'<div class="pxd-tile"><div class="pxd-tile-h"><span>{_e(name)}</span></div>'
        f'<div class="pxd-tile-v"><b>{value}</b><i style="color:{color}">{delta}</i></div>'
        f"{_spark_svg(points, color, str(index))}</div>"
        for index, (name, value, delta, color, points) in enumerate(_MARKETS)
    )
    score_rows = "".join(
        f'<div class="pxd-row"><span>{_e(label)}</span><i><u style="width:{value}%"></u></i>'
        f"<b>{value}</b></div>"
        for label, value in rows
    )
    signals = "".join(
        f'<div class="pxd-card"><div class="pxd-sig-h"><b>{icon} {_e(title)}</b>'
        f'<span style="color:{color};background:{color}1f">{_e(state)}</span></div>'
        f"<h4>{_e(headline)}</h4><p>{_e(note)}</p>"
        + '<div class="pxd-bars">'
        + "".join(f'<i style="height:{v}%;background:linear-gradient(180deg,{color},{color}55)"></i>' for v in bars)
        + "</div></div>"
        for title, icon, state, color, headline, note, bars in _SIGNALS
    )
    heat = "".join(
        f'<div style="background:{color}"><span>{_e(name)}</span><b>{delta}</b></div>'
        for name, delta, color in _SECTORS
    )
    watch = "".join(
        f'<div class="pxd-watch-row"><span><i class="pxd-star">★</i>{_e(name)}</span><b>{price}</b>'
        f'<em style="color:{UP if change.startswith("+") else DOWN}">{change}</em></div>'
        for name, price, change in _WATCH
    )

    name = focus.get("name", "삼성전자") if focus else "삼성전자"
    code = focus.get("code", "005930") if focus else "005930"
    if focus:
        change_text = _growth_text(focus)
        falling = change_text.startswith("-") or "적자" in change_text
        headline = f"영업이익 {change_text}"
        focus_note = f'공식 자료 {_e((focus.get("financial") or {}).get("period", ""))}'
    else:
        headline, falling, focus_note = "72,400원 +2.69%", False, SAMPLE
    focus_color = DOWN if falling else UP

    money = (focus or {}).get("financial") or {}
    if money:
        earnings = _earnings_svg(
            [money.get("prior_period", "이전"), money.get("period", "최근")],
            [money["prior_revenue"], money["revenue"]],
            [money["prior_operating_profit"], money["operating_profit"]],
        )
        earnings_note = f'{money.get("basis", "연결")} · 단위 {money.get("unit", "")} · 공식 자료'
    else:
        earnings = _earnings_svg(["3Q23", "4Q23", "1Q24", "2Q24", "3Q24", "4Q24(E)"],
                                 [67, 72, 72, 74, 79, 84], [42, 45, 48, 52, 60, 67])
        earnings_note = SAMPLE

    value = (focus or {}).get("valuation") or {}
    if value:
        low, base, high, now = value["low"], value["base"], value["high"], value["current_price"]
        mark = min(max((now - low) / max(high - low, 1), 0), 1) * 100
        val_labels = "".join(f"<span>{v:,.0f}</span>" for v in (low, base, high))
        val_html = (f'<b>현재 {now:,.0f}원</b><div class="pxd-val-line"><u style="left:26%;right:24%"></u>'
                    f'<i style="left:{mark:.0f}%"></i></div><div class="pxd-val-lab">{val_labels}</div>'
                    f'<small>{_e(str(value.get("method", "")))[:46]} · 목표주가 아님</small>')
    else:
        val_html = ('<b>현재 72,400원</b><div class="pxd-val-line"><u style="left:26%;right:24%"></u>'
                    '<i style="left:51%"></i></div><div class="pxd-val-lab"><span>52,000</span>'
                    f'<span>68,000</span><span>86,000</span><span>102,000</span></div><small>{SAMPLE} · 목표주가 아님</small>')

    brief = "".join(f"<li>{_e(line)}</li>" for line in _brief_lines(focus))

    st.markdown(
        '<div class="pxd">'
        '<div class="pxd-top"><div class="pxd-brand"><em>PlanX</em><b>STOCK INTELLIGENCE</b>'
        "<small>더 깊은 분석이, 더 나은 투자를</small></div>"
        f'<div class="pxd-meta"><i class="pxd-dot"></i>{date.today():%Y년 %m월 %d일}'
        '<span class="pxd-chip">SAMPLE PREVIEW</span></div></div>'
        f'<div class="pxd-tape"><div class="pxd-tape-track">{tape}{tape}</div></div>'
        f'<div class="pxd-markets">{tiles}</div>'
        '<div class="pxd-bar"><h3>오늘의 <i>투자판단</i></h3>'
        '<div class="pxd-steps"><span>시장</span>›<span>산업</span>›<span>기업</span>›<b>투자판단</b></div></div>'
        '<div class="pxd-grid"><div class="pxd-card pxd-score">'
        '<div class="pxd-score-h"><span>종합 투자점수</span><em>RULE BASED</em></div>'
        f'<div class="pxd-gaugewrap">{_gauge_svg(score)}'
        f'<div class="pxd-verdict"><b>{_e(verdict)}</b><span>{_e(score_note)}</span></div></div>'
        f'<div class="pxd-rows">{score_rows}</div></div>'
        f"{signals}</div>"
        '<div class="pxd-main"><div class="pxd-panel">'
        f'<div class="pxd-panel-h"><div class="pxd-focus"><b>{_e(name)}</b><small>{_e(code)}</small>'
        f'<em style="color:{focus_color}">{_e(headline)} {"▼" if falling else "▲"}</em></div>'
        f"<span>{_e(focus_note)}</span></div>"
        f'<div class="pxd-legend"><span><i style="background:{MINT}"></i>{_e(name)}</span>'
        f'<span><i style="background:{DOWN}"></i>KOSPI</span>'
        f'<span><i style="background:{GOLD}"></i>반도체</span>'
        f'<span style="margin-left:auto;color:#6B7F94">지수화 · 시작=100 · 샘플</span></div>'
        f"{_line_chart_svg(name)}</div>"
        '<div class="pxd-panel"><div class="pxd-panel-h">섹터별 등락률<span>1일 · 샘플</span></div>'
        f'<div class="pxd-heat">{heat}</div></div>'
        '<div class="pxd-panel"><div class="pxd-panel-h">관심종목<span>샘플 · 더보기 ›</span></div>'
        f'<div class="pxd-watch">{watch}</div></div></div>'
        '<div class="pxd-bottom"><div class="pxd-panel">'
        f'<div class="pxd-panel-h">실적 추이<span>{_e(earnings_note)}</span></div>{earnings}</div>'
        '<div class="pxd-panel"><div class="pxd-panel-h">적정가치<span>범위 참고</span></div>'
        f'<div class="pxd-val">{val_html}</div></div>'
        '<div class="pxd-panel"><div class="pxd-panel-h">✦ 조사 브리핑<span>공식 자료 기준</span></div>'
        f'<div class="pxd-brief"><div class="pxd-ai">AI</div><ul>{brief}</ul></div></div></div>'
        '<div class="pxd-edu"><b>교육자료</b><span>차트 기초 · 기술적 분석 · 투자 전략</span>'
        '<div class="pxd-pens"><i></i><i></i><i></i><i></i></div>'
        "<small>차트에 직접 그려보며 학습해보세요.</small></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="px-live-divider"><span>내 관심종목 실데이터 분석</span></div>', unsafe_allow_html=True)
