"""키움 개발실(사용자 2026-10-12): 키움 미니 코스피200 선물 연구 가운데 의미 있는 것만 올리는 화면.
자료는 kiwoom-lab/summary.json 하나(연구가 끝날 때 클로드가 고침). 한투 모의투자와 별개."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUMMARY = "kiwoom-lab/summary.json"
PR_URL = "https://github.com/ppx109-crypto/stock-dash/pull/"


def _e(x):
    return html.escape(str(x if x is not None else ""))


def _p(x):
    """포인트 값 · 음수는 긴 빼기표."""
    return (f"{x:+.1f}p").replace("-", "−") if isinstance(x, (int, float)) else _e(x)


def lab_html(s: dict | None) -> str:
    """요약 → 화면 글(HTML). 결과 칸은 지피티와 함께 인정한 것만 들어 있음."""
    s = s or {}
    out = [f'<p style="margin:0 0 8px">{_e(s.get("goal"))}</p>']
    if s.get("limits"):
        out.append("<p><b>정한 틀</b> · " + " · ".join(_e(x) for x in s["limits"]) + "</p>")
    if s.get("plan"):
        out.append(f'<p><b>개발 순서</b> · {_e(s["plan"])}</p>')
    res = s.get("results") or []
    out.append("<h4 style=\"margin:14px 0 6px\">올릴 만한 결과</h4>")
    if res:
        rows = "".join(f'<tr><td>{_e(r.get("bot"))}</td><td>{_e(r.get("rule"))}</td><td>{_p(r.get("total"))}</td>'
                       f'<td>{_p(r.get("per_day"))}</td><td>{_p(r.get("worst_day"))}</td><td>{_e(r.get("test"))}</td></tr>' for r in res)
        out.append('<table style="width:100%;font-size:13px"><tr><th>봇</th><th>규칙</th><th>합</th><th>하루 평균</th>'
                   f'<th>가장 나쁜 날</th><th>마지막 시험</th></tr>{rows}</table>')
    else:
        out.append("<p>아직 없음 · 확인 기간과 마지막 시험을 통과하고 지피티가 인정한 것만 여기에 올립니다.</p>")
    out.append("<h4 style=\"margin:14px 0 6px\">진행 중인 연구</h4><ul>")
    for t in s.get("studies") or []:
        link = f' · <a href="{PR_URL}{int(t["pr"])}" target="_blank">PR #{int(t["pr"])}</a>' if t.get("pr") else ""
        out.append(f'<li><b>{_e(t.get("id"))}</b> {_e(t.get("title"))} · {_e(t.get("status"))}{link}'
                   + (f'<br><small>{_e(t["result"])}</small>' if t.get("result") else "") + "</li>")
    out.append("</ul>")
    per = s.get("periods") or {}
    if per:
        out.append(f'<p><b>기간</b> · 개발 {_e(per.get("dev"))} · 확인 {_e(per.get("val"))} · 마지막 시험 {_e(per.get("test"))}</p>')
    if s.get("data"):
        out.append("<p><b>자료</b></p><ul>" + "".join(
            f'<li>{_e(d.get("name"))} · {_e(d.get("span"))} · {_e(d.get("days"))}일 · {_e(d.get("note"))}</li>' for d in s["data"]) + "</ul>")
    if s.get("updated"):
        out.append(f'<p style="color:#7B7465;font-size:12px">고친 때 {_e(s["updated"])}(한국 시각)</p>')
    return '<div class="pxb"><div class="pxb-note" style="line-height:1.75">' + "".join(out) + "</div></div>"


def load_summary():
    """저장소 최신 파일을 먼저(5분 캐시) · 못 받으면 앱 안 파일."""
    try:
        from research_ui import repo_json
        got = repo_json(SUMMARY)
        if got:
            return got
    except Exception:
        pass
    try:
        return json.loads((ROOT / SUMMARY).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def render_kiwoom():
    import streamlit as st
    st.header("키움 개발실")
    st.caption("키움 미니 코스피200 선물 연구 · 지피티와 함께 · 한투 모의투자와 별개 · 의미 있는 결과만 올림")
    st.markdown(lab_html(load_summary()), unsafe_allow_html=True)
