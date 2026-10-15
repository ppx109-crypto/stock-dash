"""키움 개발실(사용자 2026-10-12): 키움 미니 코스피200 선물 연구 가운데 의미 있는 것만 올리는 화면.
자료는 kiwoom-lab/summary.json 하나(연구가 끝날 때 클로드가 고침). 한투 모의투자와 별개."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUMMARY = "kiwoom-lab/summary.json"
TRIO = "kiwoom-lab/trio.json"            # 세 버전 날별 손익(매일 16:30 백테스트 뒤 클로드가 고침 · 규칙 값은 안 담음)
PR_URL = "https://github.com/ppx109-crypto/stock-dash/pull/"


def _e(x):
    return html.escape(str(x if x is not None else ""))


def _p(x):
    """포인트 값 · 음수는 긴 빼기표."""
    return (f"{x:+.1f}p").replace("-", "−") if isinstance(x, (int, float)) else _e(x)


def _d(day):
    return f"{day[4:6]}-{day[6:8]}" if len(str(day)) == 8 else _e(day)


def trio_stats(days: dict, start: str, skip=()) -> dict:
    """독립 창(start부터 · 불완전한 날 skip은 뺌) 날별 손익 → 합 · 가장 나쁜 날 · 고점 대비 낙폭 · 날 수."""
    vals = [v for d, v in sorted(days.items()) if d >= start and d not in skip]
    peak = cum = mdd = 0.0
    for v in vals:
        cum += v
        peak = max(peak, cum)
        mdd = min(mdd, cum - peak)
    return {"n": len(vals), "sum": cum, "worst": min(vals) if vals else 0.0, "mdd": mdd}


def trio_html(t: dict | None) -> str:
    """세 버전 카드 + 날별 표(독립 창 · 참고 날 나눔)."""
    t = t or {}
    boards = t.get("boards") or []
    if not boards:
        return ""
    start, need = str(t.get("test_start", "")), int(t.get("need", 20))
    days = t.get("days") or {}
    skip = set(t.get("incomplete") or [])
    cards = []
    for b in boards:
        st = trio_stats(days.get(b["name"], {}), start, skip)
        ok = st["n"] and st["sum"] > 0 and st["worst"] >= -15 and st["mdd"] >= -15
        light = "⏳" if st["n"] < need else ("✅" if ok else "❌")
        cards.append(
            f'<div style="flex:1 1 230px;border:1px solid #E4DCCB;border-radius:10px;padding:10px 12px;background:#FFFDF8">'
            f'<div style="font-weight:700">{_e(b.get("emoji"))} {_e(b["name"])} <small style="color:#7B7465">{_e(b.get("tag"))}</small></div>'
            f'<div style="font-size:12px;color:#5C5547;margin:4px 0">{_e(b.get("parts"))}<br>{_e(b.get("why"))}</div>'
            + (f'<div style="font-size:13px">시험 2 {light} <b>{_p(st["sum"])}</b> · {st["n"]}/{need}일 · 나쁜 날 {_p(st["worst"])} · 낙폭 {_p(st["mdd"])}</div>'
               if st["n"] else f'<div style="font-size:13px">시험 2 ⏳ 0/{need}일 · 첫 시험 날 셈 기다림</div>')
            + f'<div style="font-size:12px;color:#7B7465;margin-top:4px">연구 {_p(b.get("sum"))} · 낙폭 {_p(b.get("mdd"))}'
            + (f' · {_e(b["months"])}' if b.get("months") else "") + f' · 최근({_e(t.get("recent_span"))}) {_p(b.get("recent"))}</div></div>')
    out = [f'<h4 style="margin:0 0 6px">{_e(t.get("title"))}</h4>',
           f'<p style="font-size:12px;color:#5C5547;margin:0 0 8px">{_e(t.get("note"))}<br>{_e(t.get("pass_rule"))}</p>',
           '<div style="display:flex;flex-wrap:wrap;gap:8px">' + "".join(cards) + "</div>"]
    all_days = sorted({d for s in days.values() for d in s}, reverse=True)
    if all_days:
        blocked = set(t.get("blocked") or [])
        head = "".join(f"<th>{_e(b['name'])}</th>" for b in boards)
        rows = []
        for d in all_days:
            halt = (t.get("halt") or {}).get(d)
            kind = "참고" if d < start else ("⚠️ 불완전(셈 뺌)" if d in skip else ("시험 · ⛔ 거래 멈춤" if halt else "시험"))
            cells = "".join(f"<td>{_p(days.get(b['name'], {}).get(d))}</td>" if d in days.get(b["name"], {}) else "<td>—</td>" for b in boards)
            rows.append(f"<tr><td>{_d(d)}{' 🚧' if d in blocked else ''}</td><td>{kind}</td>{cells}</tr>")
        out.append('<table style="width:100%;font-size:13px;margin-top:10px"><tr><th>날</th><th>구분</th>' + head + "</tr>"
                   + "".join(rows) + "</table>")
        out.append('<p style="font-size:12px;color:#7B7465">🚧 막힌 날(09:45에 추세 날이 아니라고 본 날) · ⚠️ 불완전 = 1분봉이 400줄 미만 등 잠금 규칙상 빠진 날(독립 창 20일에 안 셈) · ⛔ 거래 멈춤 = 서킷브레이커로 약 30분 빈 날(덧붙임 1 · 사용자 2026-10-15 승인 · 시험 날로 셈) · 연구 숫자는 '
                   f'{_e(t.get("research_span"))} 같은 자료로 고른 값이라 실제는 더 낮을 수 있음</p>')
    if t.get("updated"):
        out.append(f'<p style="color:#7B7465;font-size:12px">고친 때 {_e(t["updated"])}(한국 시각)</p>')
    return '<div class="pxb"><div class="pxb-note" style="line-height:1.7">' + "".join(out) + "</div></div>"


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


def load_summary(path=SUMMARY):
    """저장소 최신 파일을 먼저(5분 캐시) · 못 받으면 앱 안 파일."""
    try:
        from research_ui import repo_json
        got = repo_json(path)
        if got:
            return got
    except Exception:
        pass
    try:
        return json.loads((ROOT / path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def render_kiwoom():
    import streamlit as st
    st.header("키움 개발실")
    st.caption("키움 미니 코스피200 선물 연구 · 지피티와 함께 · 한투 모의투자와 별개 · 의미 있는 결과만 올림")
    st.markdown(trio_html(load_summary(TRIO)), unsafe_allow_html=True)
    with st.expander("연구 기록 · 정한 틀 · 지난 연구", expanded=False):
        st.markdown(lab_html(load_summary()), unsafe_allow_html=True)
