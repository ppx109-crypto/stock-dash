"""조사 결과 화면. 과거 일봉으로 잰 것을 그대로 보여 줍니다."""
import json
from pathlib import Path

import streamlit as st

from dashboard_ui import GROUP_TITLES, close_frame, frame, header, section

RESULT = Path("study") / "result.json"
CAVEAT = ("수수료·세금·체결 미끄러짐·배당을 넣지 않은 값입니다. 실제 손익이 아니라 "
          "신호가 어느 쪽으로 얼마나 기울었는지 보는 눈금입니다. 또 오늘 A그룹이면 "
          "내일도 대개 A그룹이라 관측이 서로 겹칩니다. 그래서 건수는 서로 다른 "
          "기회의 수가 아닙니다. 매수·매도 신호가 아닙니다.")


@st.cache_data(ttl=600, show_spinner=False)
def load(stamp=None):
    try:
        return json.loads(RESULT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def stamp():
    try:
        return RESULT.stat().st_mtime
    except OSError:
        return None


def render_study():
    found = load(stamp())
    st.markdown(header() + section("그룹이 실제로 맞았는가",
                "과거 일봉으로 그날그날 그룹을 판정하고, 그 뒤 5·20·60거래일 수익률을 센 결과입니다")
                + close_frame(), unsafe_allow_html=True)
    if not found:
        st.info("아직 조사 결과가 없습니다. 일봉을 모은 뒤 조사를 돌리면 여기에 나옵니다.")
        st.caption("GitHub Actions의 'Daily price history'로 일봉을 모으고, "
                   "'Signal study'로 조사를 돌립니다.")
        return

    begin, end = found.get("period", ["", ""])
    st.caption(f'{found["stocks"]}종목 · 관측 {found["observations"]:,}건 · '
               f'{begin}~{end} · 만든 때 {found.get("made", "")}')

    st.subheader("그룹별 성적")
    rows = []
    for group, spans in found["groups"].items():
        for span, tal in spans.items():
            if not tal:
                continue
            rows.append({"그룹": group, "보유": f"{span}거래일", "건수": tal["건수"],
                         "상승확률": f'{tal["상승확률"]:.1f}%',
                         "평균수익률": f'{tal["평균수익률"]:+.2f}%',
                         "중앙수익률": f'{tal["중앙수익률"]:+.2f}%',
                         "최악": f'{tal["최악"]:+.1f}%', "최고": f'{tal["최고"]:+.1f}%'})
    # 줄 수만큼 높이를 줍니다. 기본 높이로 두면 아래 몇 줄이 잘려 보입니다.
    st.dataframe(rows, hide_index=True, width="stretch", height=_fits(len(rows)))

    st.subheader("A그룹에 조건을 하나 더 얹으면")
    st.caption("A그룹만 놓고, 그 조건까지 맞을 때 상승확률이 몇 %포인트 달라지는지입니다. "
               "건수가 30건 미만인 조합은 뺐습니다.")
    lifts = found.get("lifts") or []
    if lifts:
        st.dataframe([{"조건": r["잣대"], "보유": f'{r["기간"]}거래일',
                       "A그룹만": f'{r["기준 상승확률"]:.1f}%',
                       "조건까지": f'{r["더한 뒤"]:.1f}%',
                       "차이": f'{r["차이"]:+.1f}%p', "건수": r["건수"]} for r in lifts],
                     hide_index=True, width="stretch", height=_fits(len(lifts)))
    else:
        st.info("아직 조건을 나눠 볼 만큼 자료가 모이지 않았습니다.")

    best = found.get("best") or {}
    if best:
        st.subheader("어떤 조합이 돈이 되었는가")
        st.caption(f'왕복 비용 {found.get("cost", 0.25)}%를 뺀 기대수익이 큰 순서입니다. '
                   "이기는 횟수가 많아도 이기는 폭이 작고 지는 폭이 크면 계좌는 줄어듭니다. "
                   "그래서 상승확률이 아니라 기대수익으로 줄을 세웠습니다. "
                   "'전체대비'는 같은 기간 모든 관측과 견준 차이입니다. 이 값이 0에 가까우면 "
                   "그 조합이 따로 보탠 것이 없다는 뜻입니다.")
        picked = st.selectbox("그룹과 보유 기간", list(best), key="px_best_pick")
        st.dataframe([{"조건": r["조건"], "건수": r["건수"],
                       "순기대수익": f'{r["순기대수익"]:+.2f}%',
                       "전체대비": (f'{r["초과"]:+.2f}%p' if r.get("초과") is not None else "—"),
                       "상승확률": f'{r["상승확률"]:.1f}%',
                       "중앙수익률": f'{r["중앙수익률"]:+.2f}%',
                       "하위10%": f'{r["하위10%"]:+.1f}%',
                       "최악": f'{r["최악"]:+.1f}%'} for r in best[picked]],
                     hide_index=True, width="stretch", height=_fits(len(best[picked])))

    money = found.get("with_money")
    if money is not None and found.get("a_total"):
        st.caption(f'A그룹 관측 {found["a_total"]:,}건 가운데 실적이 이미 공시돼 있던 것은 '
                   f'{money:,}건입니다. 나머지 구간은 그룹 판정만 보고 센 것입니다.')

    st.subheader("오늘 기준 종목")
    today = found.get("today") or []
    st.dataframe([{"종목": r["name"], "그룹": r.get("group") or "판정 보류",
                   "충족": f'{r.get("met", 0)}/4',
                   "매출성장": _pct(r.get("매출성장")),
                   "영업이익성장": _pct(r.get("영업이익성장")),
                   "영업이익률": _pct(r.get("영업이익률")),
                   "기준일": r.get("as_of", "")} for r in today],
                 hide_index=True, width="stretch", height=_fits(len(today), cap=24))

    st.markdown(frame(section("이 숫자를 읽는 법", CAVEAT)), unsafe_allow_html=True)


def _fits(lines, cap=40):
    """표가 잘리지 않을 만큼 높이를 줍니다. 너무 길면 그때만 스크롤합니다."""
    return min(max(lines, 1), cap) * 35 + 42


def _pct(value):
    return f"{value:+.1f}%" if isinstance(value, (int, float)) else "—"
