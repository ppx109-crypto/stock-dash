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


RULE = Path("study") / "rule.json"


@st.cache_data(ttl=600, show_spinner=False)
def load_rule(stamp=None):
    try:
        return json.loads(RULE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def rule_stamp():
    try:
        return RULE.stat().st_mtime
    except OSError:
        return None


def render_rule():
    """조사에서 가장 단단했던 규칙 하나와, 오늘 그 규칙에 걸리는 종목."""
    book = load_rule(rule_stamp())
    if not book:
        return
    st.subheader(book["name"])
    st.caption(book["why"])
    kept, base = book.get("규칙") or {}, book.get("기준") or {}
    trade = book.get("굴림") or {}
    left, mid, right = st.columns(3)
    left.metric("20일 안 5%↑", f'{kept.get("5%↑", 0):.1f}%',
                f'{kept.get("5%↑", 0) - base.get("5%↑", 0):+.1f}%p')
    mid.metric("중앙 수익률", f'{kept.get("중앙", 0):+.2f}%',
               f'{kept.get("중앙", 0) - base.get("중앙", 0):+.2f}%p')
    right.metric("하위 10%", f'{kept.get("하위10%", 0):+.1f}%',
                 f'{kept.get("하위10%", 0) - base.get("하위10%", 0):+.1f}%p')
    if trade:
        st.caption(f'익절 {book["take"]:g}% · 손절 {book["stop"]:g}% · 최대 {book["limit"]}거래일 · '
                   f'자리 {book["slots"]}개로 실제로 굴리면 매매 {trade["매매"]:,}회 · '
                   f'승률 {trade["승률"]:.1f}% · 매매당 {trade["평균"]:+.2f}% · '
                   f'보유 중앙 {trade["보유일중앙"]}거래일 · 자리 가동률 {trade["가동률"]:.1f}% · '
                   f'연수익 {trade["연수익"]:+.2f}%. 자리가 차면 그날 나온 다음 후보는 '
                   f'놓칩니다({trade["놓침"]:,}회). 그것까지 세어 낸 수치입니다.')
    hit = [r for r in (book.get("오늘") or []) if r.get("해당")]
    st.markdown(f'**오늘 이 규칙에 걸리는 종목 · {len(hit)}개** '
                f'({(book.get("오늘") or [{}])[0].get("date", "")} 기준)')
    if hit:
        st.dataframe([{"종목": r["name"], "60일 전 대비": f'{r["60일 전 대비"]:+.1f}%',
                       "층": f'{r["층"]}층' if r.get("층") else "—",
                       "중기선 이격": f'{r["중기 이격"]:+.1f}%',
                       "이례도": (f'{r["중기 이격밴드"]:+.1f}σ'
                               if r.get("중기 이격밴드") is not None else "—"),
                       "영업이익성장": (f'{r["영업이익성장"]:+.0f}%'
                                   if r.get("영업이익성장") is not None else "—"),
                       "매출성장": (f'{r["매출성장"]:+.1f}%'
                                if r.get("매출성장") is not None else "—"),
                       "목표가 괴리": (f'{r["목표가괴리"]:+.1f}%'
                                  if r.get("목표가괴리") is not None else "—")}
                      for r in hit], hide_index=True, width="stretch",
                     height=_fits(len(hit), cap=20))
    else:
        st.info("오늘은 걸리는 종목이 없습니다. 조건을 낮추지 말고 기다리는 자리입니다.")
    top = [r for r in hit if r.get("층") == 1]
    if top:
        st.success("오늘 1층이 " + ", ".join(r["name"] for r in top) +
                   " 있습니다. 1층은 2주 안에 5% 오른 적이 열에 일곱이고 "
                   "중앙 수익률도 가장 높습니다. 다만 열흘에 한 번꼴로만 나옵니다.")
    tiers = book.get("층별") or []
    if tiers:
        st.markdown("**층마다 재료가 다릅니다** (2016년 이후 · 2주 뒤 · 비용 뺀 값)")
        st.dataframe([{"층": f'{t["층"]}층',
                       "조건": f'이격 {t["이격"]:g}% 아래 · 밴드 {t["밴드"]:g}σ 아래',
                       "2주 5%↑": f'{t["5%↑"]:.1f}%',
                       "평균": f'{t["평균"]:+.2f}%', "중앙": f'{t["중앙"]:+.2f}%',
                       "하위 10%": f'{t["하위10%"]:+.1f}%',
                       "건수": f'{t["건수"]:,}건 · {t["날"]:,}일'}
                      for t in tiers], hide_index=True, width="stretch",
                     height=_fits(len(tiers), cap=6))
        st.caption("같은 −15%라도 1층과 4층은 전혀 다른 재료입니다. 4층은 좋아서 "
                   "담는 것이 아니라 자리를 비워 두는 것보다 나아서 담습니다. "
                   "1층만 노리면 재료는 가장 좋지만 열 해에 백 번밖에 오지 않아 "
                   "자금이 놉니다. 건수 옆의 날짜 수도 함께 보십시오. 폭락은 하루에 "
                   "여러 종목이 한꺼번에 걸리므로, 건수보다 날 수가 실제 기회 수에 "
                   "가깝습니다.")
    ways = book.get("청산 견주기") or {}
    if len(ways) >= 2:
        st.markdown("**언제 파느냐가 승률을 바꿉니다** "
                    "(2016년 이후 · 실제로 산 신호만 · 비용 뺀 값)")
        st.dataframe([{"파는 법": tag, "승률": f'{got["승률"]:.1f}%',
                       "평균": f'{got["평균"]:+.2f}%', "중앙": f'{got["중앙"]:+.2f}%',
                       "하위 10%": f'{got["하위10%"]:+.1f}%',
                       "들고 있는 날": f'{got["보유"]:.1f}일',
                       "하루당": f'{got["하루당"]:+.3f}%'}
                      for tag, got in ways.items()], hide_index=True,
                     width="stretch", height=_fits(len(ways), cap=4))
        st.caption("같은 종목을 같은 날 사고 파는 법만 바꿔 본 것입니다. "
                   "중기선으로 돌아올 때까지 들고 가면 열에 일곱이 이기고 "
                   "중앙 수익률도 훨씬 높습니다. 대신 나쁠 때는 더 나쁘고"
                   "(하위 10%), 두 배 가까이 오래 들고 있어야 합니다. "
                   "자리를 셋으로 나눠 쉬지 않고 굴린다면 자리가 묶이는 값이 "
                   "더 커서 고정 익절·손절이 한 해로는 앞섭니다. "
                   "한 번에 한 종목만 든다면 그 값이 없으므로 중기선 회복이 "
                   "낫습니다. 어느 쪽인지는 본인이 아십니다.")
    st.warning(book["caveat"])
    st.divider()


def render_study():
    render_rule()
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
        st.caption(f'{found.get("since", "")}부터의 관측만 씁니다. 실적은 공시된 뒤에야 '
                   "알 수 있어, 그 앞 구간과 섞으면 조건이 좋아서인지 시기가 좋아서인지 "
                   "갈리지 않기 때문입니다. "
                   f'왕복 비용 {found.get("cost", 0.25)}%를 뺀 기대수익이 큰 순서입니다. '
                   "이기는 횟수가 많아도 이기는 폭이 작고 지는 폭이 크면 계좌는 줄어듭니다. "
                   "그래서 상승확률이 아니라 기대수익으로 줄을 세웠습니다. "
                   "'그룹대비'가 실적 조건이 따로 보탠 몫입니다. '전체대비'에는 그룹을 고른 "
                   "효과가 함께 섞여 있어, 그것만 보면 실적의 공으로 잘못 돌리게 됩니다. "
                   "두 값이 크게 다르면 차이의 대부분은 그룹에서 온 것입니다. "
                   "종목수를 꼭 함께 보십시오. 천 건이라도 두세 종목에서 나온 숫자라면 "
                   "그 종목들의 사정일 뿐입니다.")
        picked = st.selectbox("그룹과 보유 기간", list(best), key="px_best_pick")
        st.dataframe([{"조건": r["조건"], "건수": r["건수"],
                       "종목수": r.get("종목수", 0),
                       "순기대수익": f'{r["순기대수익"]:+.2f}%',
                       "그룹대비": (f'{r["그룹대비"]:+.2f}%p' if r.get("그룹대비") is not None else "—"),
                       "전체대비": (f'{r["전체대비"]:+.2f}%p' if r.get("전체대비") is not None else "—"),
                       "상승확률": f'{r["상승확률"]:.1f}%',
                       "중앙수익률": f'{r["중앙수익률"]:+.2f}%',
                       "하위10%": f'{r["하위10%"]:+.1f}%',
                       "최악": f'{r["최악"]:+.1f}%'} for r in best[picked]],
                     hide_index=True, width="stretch", height=_fits(len(best[picked])))

    money = found.get("with_money")
    if money is not None and found.get("a_total"):
        st.caption(f'A그룹 관측 {found["a_total"]:,}건 가운데 실적이 이미 공시돼 있던 것은 '
                   f'{money:,}건입니다. 나머지 구간은 그룹 판정만 보고 센 것입니다.')

    targets = found.get("target_best") or {}
    if targets:
        st.subheader("증권사 목표가가 붙은 구간만")
        st.caption(f'{found.get("target_since", "")}부터의 {found.get("target_rows", 0):,}건입니다. '
                   "목표가는 증권사 API가 한 해치만 주므로, 실적과 같은 자리에 놓고 비교하면 "
                   "겹치는 날이 모자라 늘 탈락합니다. 그래서 목표가가 붙은 구간만 따로 떼어 "
                   "그 안에서 견줍니다. 다른 표보다 기간이 훨씬 짧으니 그만큼 덜 믿으십시오.")
        pick = st.selectbox("그룹과 보유 기간", list(targets), key="px_target_pick")
        st.dataframe([{"조건": r["조건"], "건수": r["건수"], "종목수": r.get("종목수", 0),
                       "순기대수익": f'{r["순기대수익"]:+.2f}%',
                       "그룹대비": (f'{r["그룹대비"]:+.2f}%p' if r.get("그룹대비") is not None else "—"),
                       "전체대비": (f'{r["전체대비"]:+.2f}%p' if r.get("전체대비") is not None else "—"),
                       "상승확률": f'{r["상승확률"]:.1f}%',
                       "중앙수익률": f'{r["중앙수익률"]:+.2f}%',
                       "하위10%": f'{r["하위10%"]:+.1f}%'} for r in targets[pick]],
                     hide_index=True, width="stretch", height=_fits(len(targets[pick])))

    around = found.get("around") or {}
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

    ahead = found.get("ahead_of") or {}
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
