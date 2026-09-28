"""확률 검증 화면. 최종 조건(A·B그룹)이 과거에 실제로 맞았는지 보여 줍니다."""
import json
from pathlib import Path

import streamlit as st

from dashboard_ui import close_frame, frame, header, section

FINAL = Path("study") / "final_study.json"
RESULT = Path("study") / "result.json"
CAVEAT = ("그룹별 성적은 수수료·세금을 빼지 않은 값이고, 매매 결과는 한 번 사고팔 때 0.25%를 뺀 값입니다. "
          "배당은 넣지 않았습니다. 오늘 A그룹인 종목은 내일도 대개 A그룹이라 관측이 서로 겹칩니다. "
          "그래서 건수는 서로 다른 기회의 수가 아닙니다. 지난 성적이 앞으로를 보장하지 않습니다.")
TRADE_RULE = ("A그룹 종목을 그날 종가에 삽니다. 자리는 5개, 하루에 새로 사는 것은 2종목까지이고, "
              "180일선 기울기가 가파른 것부터 담습니다. 전날까지 5거래일 동안 외국인·투신이 순매수하고 "
              "개인이 순매도한 종목만 삽니다.<br>"
              "· 추세 규칙으로 들어온 종목: +10%면 익절, −5%면 손절, 아니면 10거래일 뒤 매도<br>"
              "· 정배열 추세로 들어온 종목: 정배열이 깨지는 날 매도, −8%면 손절, 길어도 60거래일<br>"
              "사는 차례를 조금씩 바꿔 여덟 번 돌린 가운데 값입니다.")


@st.cache_data(ttl=600, show_spinner=False)
def load(stamp=None, path=FINAL):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def stamp(path=FINAL):
    try:
        return Path(path).stat().st_mtime
    except OSError:
        return None


def trade_rows(trading):
    """구간마다 한 줄. 연수익과 최대 낙폭을 나란히 둡니다."""
    return [{"구간": label, "매매": t["매매"], "연수익": f'{t["연수익"]:+.1f}%',
             "최대 낙폭": f'{t["최대낙폭"]:.1f}%', "승률": f'{t["승률"]:.1f}%',
             "한 번 평균": f'{t["평균"]:+.2f}%', "보유 중앙": f'{t["보유중앙"]}거래일',
             "자리 채운 비율": f'{t["가동률"]:.0f}%', "최대 연패": t["연패"]}
            for label, t in (trading or {}).items()]


def year_rows(trading):
    years = {}
    for t in (trading or {}).values():
        years.update(t.get("해마다") or {})
    return [{"해": year, "수익": f"{gain:+.1f}%"} for year, gain in sorted(years.items())]


def group_rows(groups):
    names = {"A": "A그룹", "B": "B그룹", "밖": "A·B그룹 밖", "전체": "전체"}
    rows = []
    for group, spans in (groups or {}).items():
        for span, tal in spans.items():
            if not tal:
                continue
            rows.append({"그룹": names.get(group, group.replace("A · ", "A그룹 · ")),
                         "보유": f"{span}거래일", "건수": tal["건수"], "종목수": tal["종목수"],
                         "상승확률": f'{tal["상승확률"]:.1f}%',
                         "평균수익률": f'{tal["평균수익률"]:+.2f}%',
                         "중앙수익률": f'{tal["중앙수익률"]:+.2f}%',
                         "최악": f'{tal["최악"]:+.1f}%', "최고": f'{tal["최고"]:+.1f}%'})
    return rows


def render_study():
    found = load(stamp())
    st.markdown(header() + section("최종 조건이 실제로 맞았는가",
                "2017년부터 날마다 오늘 화면과 같은 잣대로 A·B그룹을 나누고, 그 뒤를 센 결과입니다")
                + close_frame(), unsafe_allow_html=True)
    if not found:
        st.info("아직 계산 결과가 없습니다. 저장소에서 final_study.py를 돌리면 여기에 나옵니다.")
        return

    begin, end = found.get("period", ["", ""])
    st.caption(f'{found["stocks"]}종목 · 관측 {found["observations"]:,}건 · '
               f'{begin}~{end} · 계산한 때 {found.get("made", "")}')

    st.subheader("A그룹을 실제로 매매했다면")
    st.markdown(frame(section("사고파는 방법", TRADE_RULE)), unsafe_allow_html=True)
    trades = trade_rows(found.get("trading"))
    if trades:
        st.dataframe(trades, hide_index=True, width="stretch", height=_fits(len(trades)))
        st.caption("연수익은 매매 수익을 자리 5개로 나눠 해마다 평균한 값이고, 최대 낙폭은 계좌가 "
                   "가장 높던 때에서 가장 깊이 내려간 폭입니다. 두 구간으로 나눈 것은 한 구간에서만 "
                   "좋은 규칙을 걸러 내려는 것입니다.")
        years = year_rows(found.get("trading"))
        if years:
            with st.expander("해마다 수익"):
                st.dataframe(years, hide_index=True, width="stretch", height=_fits(len(years)))
    else:
        st.info("매매가 60건이 안 되어 셈을 보류했습니다.")

    st.subheader("그룹별 성적")
    st.caption("그날 그 그룹이던 종목을 샀다면 5·20·60거래일 뒤 얼마였는지입니다. "
               "A그룹은 두 갈래(추세 규칙 · 정배열 추세)로도 나눠 적었습니다. "
               "'전체'와 견주어 A가 얼마나 나은지 보십시오.")
    groups = group_rows(found.get("groups"))
    st.dataframe(groups, hide_index=True, width="stretch", height=_fits(len(groups)))

    # 아래 두 표는 그룹과 무관한 조사입니다. 'Signal study' 작업이 남긴 것을 그대로 씁니다.
    extra = load(stamp(RESULT), RESULT) or {}
    around = extra.get("around") or {}
    if around:
        st.subheader("좋은 실적은 공시 전에 이미 올라 있었는가")
        st.caption("공시일을 가운데 두고 앞뒤 60거래일 수익률입니다. 공시 전이 뒤보다 크면, "
                   "그 실적은 공시 때 이미 주가에 들어가 있었다고 볼 수 있습니다. "
                   "그러면 공시를 보고 사는 것은 늦은 것이 됩니다.")
        st.dataframe([{"실적": label, "건수": b["건수"],
                       "공시전 중앙": f'{b["공시전 중앙"]:+.2f}%',
                       "공시후 중앙": f'{b["공시후 중앙"]:+.2f}%',
                       "공시전 평균": f'{b["공시전 평균"]:+.2f}%',
                       "공시후 평균": f'{b["공시후 평균"]:+.2f}%'}
                      for label, b in around.items()],
                     hide_index=True, width="stretch", height=_fits(len(around)))

    ahead = extra.get("ahead_of") or {}
    if ahead:
        st.subheader("오르기 전에 무엇이 있었는가")
        st.caption("결과를 먼저 정해 두고 거슬러 셉니다. '적중률'은 그 신호가 있을 때 오른 "
                   "비율, '포착률'은 오른 것 가운데 그 신호가 있던 몫입니다. 오른 것의 "
                   "구 할에 있던 신호라도 오르지 않은 것의 구 할에도 있었다면 미리 알려 준 "
                   "것이 없습니다. 그래서 '차이'로 보십시오.")
        which = st.selectbox("기간과 오름폭", list(ahead), key="px_ahead_pick")
        st.dataframe([{"신호": r["신호"], "적중률": f'{r["적중률"]:.1f}%',
                       "신호 없을 때": (f'{r["신호없을때"]:.1f}%'
                                    if r["신호없을때"] is not None else "—"),
                       "차이": (f'{r["차이"]:+.1f}%p' if r["차이"] is not None else "—"),
                       "포착률": (f'{r["포착률"]:.1f}%' if r["포착률"] is not None else "—"),
                       "해당": r["해당"], "종목수": r["종목수"]} for r in ahead[which]],
                     hide_index=True, width="stretch", height=_fits(len(ahead[which])))

    st.markdown(frame(section("이 숫자를 읽는 법", CAVEAT)), unsafe_allow_html=True)


def _fits(lines, cap=40):
    """표가 잘리지 않을 만큼 높이를 줍니다. 너무 길면 그때만 스크롤합니다."""
    return min(max(lines, 1), cap) * 35 + 42
