"""KMF-0013 합성 시험."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf13 as M  # noqa: E402
import kmf as K  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def mk(prices, d0=20260105):
    """5분봉을 바로 만듦(날마다 76봉 · 09:04 ~ 15:19 이름)."""
    rows, k = [], 0
    for di in range(len(prices) // 76 + 1):
        for j in range(76):
            if k >= len(prices):
                break
            p = prices[k]; rows.append((str(d0 + di), 544 + 5 * j, p, p + 0.1, p - 0.1, p, 1)); k += 1
    return rows


pick = M.grid()[0]
up = [100 + 0.2 * i for i in range(300)]
w = M.signals(mk(up), pick)
first = next(i for i, x in enumerate(w) if x is not None)
chk("1 꾸준히 오르면 삼으로 들고(정배열 + 기울기) 판 신호는 없음", w[first] == 1 and -1 not in w)
dn = [200 - 0.2 * i for i in range(300)]
w = M.signals(mk(dn), pick)
chk("2 꾸준히 내리면 팖", next(x for x in w if x is not None) == -1 and 1 not in w)
turn = [100 + 0.2 * i for i in range(120)] + [124 - 0.6 * i for i in range(100)]   # 둘째 날 안에서 꺾임
w = M.signals(mk(turn), pick)
k1 = next(i for i, x in enumerate(w) if x == 1)
chk("3 오르다 꺾이면 정리(0)가 뒤에 나옴", any(x == 0 for x in w[k1 + 1:]))
w2 = M.signals(mk(turn)[:180], pick)
chk("4 앞 180봉만 줘도 그 앞 신호가 같음(미래 안 봄)", w2 == w[:180])
chk("5 선 길이 4 · 15 · 45 · 90봉", M.spans_for(0.75) == (4, 15, 45, 90))
chk("6 하루 멈춤 −25p", K.DAY_STOP == -25.0)
chk("7 고른 칸 + 이웃 8 · 이름 겹침 없음", len(M.grid()) == 9 and len({M.name(c) for c in M.grid()}) == 9)
chk("8 잠금 통과", bool(M.verify_inputs()))
# 아침 관망: 셋째 날(봉 152부터)은 첫 봉에 이미 정배열 → 그날 오름이 이어지는 동안 들기 신호 없음
w = M.signals(mk([100 + 0.2 * i for i in range(228)]), pick)
chk("4b 아침 관망: 첫 봉에 이미 배열이면 그날 새로 안 듦(밤사이 추세 따라 들지 않음)", all(x is None for x in w[152:228]) and 1 in w[76:152])
# 9 완전한 거래일 판별(가짜 줄)
full = [("20261013", m, 1, 1, 1, 1, 1) for m in range(540, 935)]
holey = [("20261014", m, 1, 1, 1, 1, 1) for m in range(540, 935) if not 700 <= m < 710]
short = [("20261015", m, 1, 1, 1, 1, 1) for m in range(540, 700)]
g, bad = M.complete_days(full + holey + short)
chk("9 완전한 날만 셈(빈 분 5분 넘음 · 줄 모자람은 뺌)", g == ["20261013"] and set(bad) == {"20261014", "20261015"})
chk("10 시험 2는 잠금 동의 파일 없으면 멈춤", not M.TEST2_OK.exists() and M.TEST2_N == 20)
print(f"모두 통과 {ok}개")
