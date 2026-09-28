"""종목 탭 네 개가 진짜 자료로 채워지는지 확인합니다(GitHub Actions에서 수동으로 돌림).

앱과 같은 함수(latest_company · latest_results · latest_prices · latest_price_check)를
streamlit 시험 도구로 그려 보고, 화면에 나온 글과 숫자 칸만 적습니다. 키나 응답 본문은
적지 않습니다. 조회 전용이며 주문과 무관합니다.
"""
import re
import sys

from streamlit.testing.v1 import AppTest

CODES = [c for c in sys.argv[1:] if re.fullmatch(r"[0-9]{6}", c)] or ["005930", "000660", "247540"]


def page(code):
    import research_ui as R
    R.latest_company(code)
    R.latest_results(code)
    R.latest_prices(code)
    R.latest_price_check(code)


def main():
    bad = 0
    for code in CODES:
        at = AppTest.from_function(page, args=(code,), default_timeout=300).run()
        print(f"\n===== {code} =====")
        if at.exception:
            bad += 1
            print("  오류:", [str(e.value)[:120] for e in at.exception])
            continue
        for c in at.caption:
            print("  [글]", str(c.value)[:140])
        for m in at.metric:
            print("  [칸]", m.label, "=", m.value)
        print("  [표]", len(at.dataframe), "개 · [그래프]", len(at.get("vega_lite_chart")),
              "개 · [본문]", sum(len(str(t.value)) for t in at.markdown), "자")
        failed = [str(c.value) for c in at.caption
                  if any(word in str(c.value) for word in ("받지 못했습니다", "실패", "중단", "오류", "HTTP"))]
        if failed:
            bad += 1
            print("  → 받지 못한 칸", len(failed), "개")
    print("\n끝 · 문제 있는 종목", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
