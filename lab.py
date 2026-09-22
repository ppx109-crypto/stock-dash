"""조합 실험실. 한 번 계산한 것을 다시 계산하지 않습니다.

기존 조사는 날마다 이동평균을 처음부터 다시 셌습니다. 종목당 칠천 일이면
이천오백만 번의 덧셈이 되어, 한 번 돌리는 데 이십 분이 넘었습니다. 그러면
스무 분마다 무언가를 고쳐 볼 수가 없습니다.

여기서는 이동평균을 한 번만 훑어 만들고(앞 값에서 다음 값이 바로 나옵니다),
각 날의 특징을 표 하나로 굳혀 둡니다. 그 뒤로는 조건을 바꿔 가며 세는 일만
남습니다. 익절·손절을 넣은 매매도 같은 표 위에서 돌립니다.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from datetime import datetime, timedelta
from pathlib import Path

import study

# 단기·중기·중장기·장기 네 축입니다. 같은 이동평균이라도 길이에 따라
# 말하는 것이 다릅니다. 짧은 것은 며칠의 흔들림을, 긴 것은 몇 달의 흐름을
# 봅니다. 네 축을 함께 두면 '무엇이 어긋났는지'가 읽힙니다.
AXES = {"단기": 5, "중기": 20, "중장기": 60, "장기": 120}
SPANS = tuple(sorted(set(AXES.values()) | {10, 40}))
SLOPE_STEP = 5      # 기울기를 잴 간격. 한 주입니다.
BAND_WINDOW = 120   # 이격이 이례적인지 볼 때 견줄 지난 구간.
HORIZON = 10            # 기본으로 보는 앞날. 두 주, 열 거래일입니다.
RISE = 5.0              # 무엇을 '성공'으로 볼지. 오 퍼센트입니다.
COST = 0.25             # 왕복 비용 어림값(%).
CACHE = Path("study") / "features.json"


def ema_series(closes, span):
    """이동평균을 한 번만 훑어 만듭니다. 길이는 closes와 같고 앞은 None입니다."""
    if len(closes) < span:
        return [None] * len(closes)
    alpha = 2 / (span + 1)
    out = [None] * (span - 1)
    value = sum(closes[:span]) / span
    out.append(value)
    for close in closes[span:]:
        value = close * alpha + value * (1 - alpha)
        out.append(value)
    return out


def slope_series(line, step=SLOPE_STEP):
    """이동평균선 자체가 오르고 있는지. 며칠 전 같은 선과 견줍니다."""
    out = [None] * len(line)
    for i in range(step, len(line)):
        now, before = line[i], line[i - step]
        if now is not None and before:
            out[i] = (now / before - 1) * 100
    return out


def speed_series(slopes, step=SLOPE_STEP):
    """기울기가 더 가팔라지는지 눕는지. 기울기의 변화입니다."""
    out = [None] * len(slopes)
    for i in range(step, len(slopes)):
        now, before = slopes[i], slopes[i - step]
        if now is not None and before is not None:
            out[i] = now - before
    return out


def band_series(gaps, window=BAND_WINDOW):
    """이격이 그 종목치고 이례적인지. 지난 구간의 이격과 견줍니다.

    같은 -15%라도 늘 출렁이는 종목에는 흔한 일이고, 조용한 종목에는 큰
    일입니다. 고정된 값으로 자르면 출렁이는 종목만 잔뜩 걸립니다.
    """
    out = [None] * len(gaps)
    for i in range(window, len(gaps)):
        chunk = [g for g in gaps[i - window:i] if g is not None]
        if len(chunk) < window // 2 or gaps[i] is None:
            continue
        mean = sum(chunk) / len(chunk)
        var = sum((g - mean) ** 2 for g in chunk) / (len(chunk) - 1)
        if var > 0:
            out[i] = (gaps[i] - mean) / math.sqrt(var)
    return out


def rolling_std(closes, window=20):
    """최근 구간 일간 등락의 표준편차. 변동성 잣대입니다."""
    moves = [None]
    for i in range(1, len(closes)):
        moves.append((closes[i] / closes[i - 1] - 1) * 100 if closes[i - 1] else None)
    out = [None] * len(closes)
    for i in range(window, len(closes)):
        chunk = [m for m in moves[i - window + 1:i + 1] if m is not None]
        if len(chunk) >= window // 2:
            mean = sum(chunk) / len(chunk)
            out[i] = math.sqrt(sum((m - mean) ** 2 for m in chunk) / (len(chunk) - 1))
    return out


def build(prices=None, horizons=(5, 10, 20, 60), warmup=120):
    """종목마다 하루치 특징을 만들어 한 표로 모읍니다."""
    prices = prices if prices is not None else study.load_prices()
    rows = []
    for code, block in prices.items():
        days = [d for d, _ in block["rows"]]
        closes = [c for _, c in block["rows"]]
        if len(closes) <= warmup + max(horizons):
            continue
        emas = {span: ema_series(closes, span) for span in SPANS}
        vol = rolling_std(closes)
        # 축마다 이격도·기울기·가속도·이격밴드를 미리 만들어 둡니다.
        gaps, slopes, speeds, bands = {}, {}, {}, {}
        for name, span in AXES.items():
            line = emas[span]
            gaps[name] = [(closes[k] / line[k] - 1) * 100 if line[k] else None
                          for k in range(len(closes))]
            slopes[name] = slope_series(line)
            speeds[name] = speed_series(slopes[name])
            bands[name] = band_series(gaps[name])
        money = study.money_timeline(code)
        targets = study.target_timeline(code)
        money_at, target_at = {}, {}
        for i in range(warmup, len(closes) - min(horizons)):
            day, price = days[i], closes[i]
            now = {span: emas[span][i] for span in SPANS}
            if any(now[span] is None for span in (5, 20, 40, 60)):
                continue
            above = {span: price > now[span] for span in SPANS if now[span] is not None}
            met = sum(1 for span in (5, 20, 40, 60) if above.get(span))
            ahead = {}
            for span in horizons:
                if i + span < len(closes):
                    ahead[span] = (closes[i + span] / price - 1) * 100
            if not ahead:
                continue
            row = {
                "code": code, "date": day, "price": price, "i": i,
                "met": met,
                "group": ("A" if met == 4 else
                          "B" if all(above.get(s) for s in (20, 40, 60)) else "C"),
                "ahead": ahead,
                # 이평선에서 얼마나 떨어져 있는지. 눌림과 과열을 가릅니다.
                "EMA20 이격": (price / now[20] - 1) * 100 if now[20] else None,
                "EMA60 이격": (price / now[60] - 1) * 100 if now[60] else None,
                # 중기선이 장기선 위에 있는지. 추세의 방향입니다.
                "정배열폭": ((now[20] / now[60] - 1) * 100
                          if now[20] and now[60] else None),
                "변동성": vol[i],
                # 네 축을 한꺼번에. 이름이 길어도 무엇인지 바로 읽힙니다.
                **{f"{name} 이격": gaps[name][i] for name in AXES},
                **{f"{name} 기울기": slopes[name][i] for name in AXES},
                **{f"{name} 가속도": speeds[name][i] for name in AXES},
                **{f"{name} 이격밴드": bands[name][i] for name in AXES},
                # 짧은 선이 긴 선 위에 차례로 놓였는지. 넷이 줄을 서면 4입니다.
                "배열": sum(1 for a, b in (("단기", "중기"), ("중기", "중장기"),
                                          ("중장기", "장기"))
                          if emas[AXES[a]][i] and emas[AXES[b]][i]
                          and emas[AXES[a]][i] > emas[AXES[b]][i]),
                "20일 전 대비": ((price / closes[i - 20] - 1) * 100
                             if i >= 20 and closes[i - 20] else None),
                "60일 전 대비": ((price / closes[i - 60] - 1) * 100
                             if i >= 60 and closes[i - 60] else None),
            }
            row.update(study.known_by(money, day))
            block_t = study.known_by(targets, day)
            if block_t.get("목표가") and price:
                row["목표가괴리"] = (block_t["목표가"] / price - 1) * 100
                row["목표가곳수"] = block_t.get("목표가곳수")
            rows.append(row)
    return rows


def trade(rows, prices, take, stop, limit=60, cost=COST):
    """익절·손절을 넣고 실제로 빠져나온 자리를 셉니다.

    앞날 수익률만 보면 '가는 동안 얼마나 흔들렸는지'가 사라집니다. 20% 올랐다
    해도 도중에 15% 빠졌다면 대개 그 전에 팔고 나옵니다. 그래서 하루하루
    따라가며 먼저 닿는 쪽에서 끝냅니다. 종가만 있으므로 그날 종가 기준입니다.
    """
    series = {code: [c for _, c in block["rows"]] for code, block in prices.items()}
    ends, days_held, wins = [], [], 0
    for row in rows:
        closes = series.get(row["code"])
        if not closes:
            continue
        start, begin = row["price"], row["i"]
        done = None
        for step in range(1, limit + 1):
            spot = begin + step
            if spot >= len(closes):
                break
            move = (closes[spot] / start - 1) * 100
            if move >= take or move <= -stop:
                done = (move, step); break
        if done is None:
            spot = min(begin + limit, len(closes) - 1)
            if spot <= begin:
                continue
            done = ((closes[spot] / start - 1) * 100, spot - begin)
        ends.append(done[0] - cost)
        days_held.append(done[1])
        wins += 1 if done[0] > 0 else 0
    if len(ends) < 60:
        return None
    ends_sorted = sorted(ends)
    cut = max(1, len(ends_sorted) // 10)
    return {"건수": len(ends), "승률": round(wins / len(ends) * 100, 1),
            "평균": round(statistics.fmean(ends), 3),
            "중앙": round(statistics.median(ends), 3),
            "하위10%": round(statistics.fmean(ends_sorted[:cut]), 2),
            "평균보유일": round(statistics.fmean(days_held), 1),
            "연환산": round(statistics.fmean(ends) * (250 / statistics.fmean(days_held)), 2)}


def score(rows, horizon=HORIZON, rise=RISE, cost=COST):
    """한 무리를 재는 기본 잣대. 빈도와 수익을 함께 봅니다."""
    moves = [r["ahead"][horizon] for r in rows if horizon in r["ahead"]]
    if len(moves) < 60:
        return None
    ordered = sorted(moves)
    cut = max(1, len(ordered) // 10)
    return {"건수": len(moves), "종목수": len({r["code"] for r in rows}),
            f"{rise:g}%↑": round(sum(1 for m in moves if m >= rise) / len(moves) * 100, 1),
            "승률": round(sum(1 for m in moves if m > cost) / len(moves) * 100, 1),
            "평균": round(statistics.fmean(moves) - cost, 2),
            "중앙": round(statistics.median(moves) - cost, 2),
            "하위10%": round(statistics.fmean(ordered[:cut]), 1)}


def market_relative(rows):
    """그날 시장이 함께 밀린 것인지, 그 종목만 밀린 것인지 가릅니다.

    시장이 통째로 5% 빠진 날에는 거의 모든 종목이 이동평균 아래로 벌어집니다.
    그때의 -15%와, 시장은 멀쩡한데 혼자 -15%인 것은 전혀 다른 일입니다.
    앞은 시장을 사는 것이고 뒤는 그 회사에 무슨 일이 난 것입니다.

    그날 모든 종목의 이격 중앙값을 시장 몫으로 보고, 거기서 뺀 나머지를
    그 종목 몫으로 둡니다. 그날 자료만 쓰므로 뒷날을 보지 않습니다.
    """
    by_day = {}
    for row in rows:
        gap = row.get("중기 이격")
        if gap is not None:
            by_day.setdefault(row["date"], []).append(gap)
    middle = {}
    for day, gaps in by_day.items():
        gaps.sort()
        middle[day] = gaps[len(gaps) // 2]
    # 시장이 요즘 얼마나 출렁였는지. 그날까지의 시장 이격 스무 날만 봅니다.
    order = sorted(middle)
    spot = {day: k for k, day in enumerate(order)}
    swing = {}
    for k, day in enumerate(order):
        window = [middle[one] for one in order[max(0, k - 19):k + 1]]
        if len(window) < 10:
            continue
        mean = sum(window) / len(window)
        swing[day] = (sum((x - mean) ** 2 for x in window) / len(window)) ** 0.5
    for row in rows:
        gap = row.get("중기 이격")
        if gap is None:
            continue
        row["시장 이격"] = round(middle[row["date"]], 3)
        row["상대 이격"] = round(gap - middle[row["date"]], 3)
        if row["date"] in swing:
            row["시장 출렁임"] = round(swing[row["date"]], 3)
    return rows


def save(rows, path=CACHE):
    path.parent.mkdir(exist_ok=True)
    slim = [{k: v for k, v in r.items() if k != "i"} | {"i": r["i"]} for r in rows]
    path.write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")
    return len(rows)


def load(path=CACHE):
    try:
        rows = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    for row in rows:
        row["ahead"] = {int(k): v for k, v in row["ahead"].items()}
    return rows


# 규칙을 찾을 때 쓰는 구간과, 찾은 뒤 확인할 구간을 갈라 둡니다.
# 같은 자료로 찾고 같은 자료로 확인하면 어떤 규칙이든 좋아 보입니다.
SPLIT = "20160101"


def split(rows, edge=SPLIT):
    """앞은 찾는 데, 뒤는 확인하는 데 씁니다."""
    return ([r for r in rows if r["date"] < edge],
            [r for r in rows if r["date"] >= edge])


def both(rows, holds, edge=SPLIT, horizon=HORIZON):
    """앞뒤 두 구간의 성적을 함께 냅니다.

    앞에서만 좋고 뒤에서 무너지면 과거에 맞춘 규칙입니다. 그런 규칙은
    숫자가 아무리 좋아도 버려야 합니다.
    """
    early, late = split(rows, edge)
    found = {}
    for name, part in (("탐색", early), ("확인", late)):
        base = score(part, horizon)
        kept = score([r for r in part if holds(r)], horizon)
        if not base or not kept:
            found[name] = None
            continue
        found[name] = {**kept, "중앙덧셈": round(kept["중앙"] - base["중앙"], 2),
                       "5%↑덧셈": round(kept[f"{RISE:g}%↑"] - base[f"{RISE:g}%↑"], 1)}
    return found


def portfolio(rows, prices, holds, slots=10, take=10.0, stop=7.0, limit=60,
              cost=COST, rank=None, since=None, per_day=None, apart=None,
              realistic=False):
    """자금을 나눠 담고 실제로 굴려 봅니다. 앱 화면이 읽는 수치입니다.

    한 종목씩 따로 재면 '같은 날 후보가 쉰 개면 쉰 개를 다 산다'는 셈이
    됩니다. 실제로는 자리가 정해져 있고, 자리가 차면 다음 후보는 놓칩니다.
    놓친 기회까지 세어야 실제에 가까운 수치가 나옵니다.

    한때 이 함수가 run과 따로 같은 일을 하고 있었습니다. 두 벌이 있으면
    한쪽만 고쳐지고, 실제로 17회차에 그 일이 났습니다. 지금은 run 하나를
    부르고 이름만 옛 화면에 맞춰 돌려줍니다.
    """
    got = run(rows, prices, holds, exit_fixed(take, stop, limit), slots=slots,
              rank=rank, since=since, cost=cost, per_day=per_day,
              apart=apart, realistic=realistic)
    if not got:
        return None
    years = max(len({row["date"][:4] for row in rows
                     if holds(row) and (since is None or row["date"] >= since)}), 1)
    return {**got, "자리": slots, "보유일중앙": got["보유중앙"],
            "연매매": round(got["매매"] / years, 1)}


def lanes(prices):
    """종목마다 종가·중기선·변동성을 한 번만 만들어 둡니다. 청산 판정에 씁니다."""
    found = {}
    for code, block in prices.items():
        closes = [c for _, c in block["rows"]]
        found[code] = {"closes": closes,
                       "날": [d for d, _ in block["rows"]],
                       "중기선": ema_series(closes, AXES["중기"]),
                       "변동성": rolling_std(closes)}
    return found


# 청산 방법들. 모두 (길, 진입자리, 진입가, 지난 거래일, 그동안 최고가, 산 날의
# 한 줄)을 받고 나갈지 말지를 돌려줍니다. 나가는 값은 늘 그날 종가입니다.
# 마지막 것은 층마다 다르게 나가고 싶을 때만 씁니다.
def exit_fixed(take, stop, limit):
    """고정 익절·손절. 견줄 자리로 둡니다."""
    def go(lane, start, price, step, peak, row=None):
        move = (lane["closes"][start + step] / price - 1) * 100
        return move >= take or move <= -stop or step >= limit
    return go


def exit_back_to_line(limit, cushion=0.0):
    """중기선으로 돌아오면 나갑니다. 벌어진 것이 메워지면 할 일이 끝납니다."""
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        line = lane["중기선"][spot]
        if line and lane["closes"][spot] >= line * (1 + cushion / 100):
            return True
        return step >= limit
    return go


def exit_volatility(take_mult, stop_mult, limit):
    """그 종목의 변동성에 맞춰 익절·손절을 잡습니다.

    하루에 1%씩 움직이는 종목과 5%씩 움직이는 종목에 같은 7%를 걸면, 앞의
    종목은 거의 걸리지 않고 뒤의 종목은 하루 만에 걸립니다.
    """
    def go(lane, start, price, step, peak, row=None):
        sigma = lane["변동성"][start] or 2.0
        move = (lane["closes"][start + step] / price - 1) * 100
        return move >= sigma * take_mult or move <= -sigma * stop_mult or step >= limit
    return go


def exit_trailing(give_back, arm, limit):
    """오른 뒤 되돌리면 나갑니다. 먼저 arm%만큼 올라야 작동합니다."""
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        move = (lane["closes"][spot] / price - 1) * 100
        top = (peak / price - 1) * 100
        if top >= arm and move <= top - give_back:
            return True
        return move <= -arm or step >= limit
    return go


def exit_trailing_vol(give_mult, arm_mult, limit):
    """되돌림 폭을 그 종목의 변동성으로 잽니다."""
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        sigma = lane["변동성"][start] or 2.0
        move = (lane["closes"][spot] / price - 1) * 100
        top = (peak / price - 1) * 100
        if top >= sigma * arm_mult and move <= top - sigma * give_mult:
            return True
        return move <= -sigma * arm_mult or step >= limit
    return go


def deepest(gains, slots):
    """나간 차례대로 쌓아 가장 깊은 골을 잽니다.

    한 번에 얼마를 잃느냐보다, 잃는 것이 이어질 때 얼마나 파이느냐가 사람을
    그만두게 만듭니다.

    여기서는 **지갑에 견준 비율**로 잽니다. 자리 하나에 그때 지갑의 1/slots을
    넣는 셈이므로, 매매마다 지갑이 (1 + 손익/100/slots)배가 됩니다. 더해 가는
    셈으로 재면 골이 실제보다 깊게 나옵니다. 원금이 불어난 뒤의 −7%와 처음의
    −7%를 같은 크기로 세기 때문입니다.

    한 번도 꼭대기 아래로 내려가지 않았으면 0입니다.
    """
    purse = top = 1.0
    dip = 0.0
    for gain in gains:
        purse *= 1 + gain / 100 / slots
        top = max(top, purse)
        dip = min(dip, purse / top - 1)
    return dip * 100


def streak(gains):
    """가장 길게 이어진 연패. 사람이 그만두는 것은 이 숫자 때문입니다."""
    run = most = 0
    for gain in gains:
        run = run + 1 if gain <= 0 else 0
        most = max(most, run)
    return most


def run(rows, prices, holds, exit_at, slots=3, rank=None, since=None, cost=COST,
        cap=90, detail=False, cooldown=0, cooldown_after="모두", size=None,
        greedy=False, per_day=None, delay=0, busy_cap=None,
        per_window=None, apart=None, realistic=False, brake=None):
    """청산 방법을 갈아 끼우며 같은 판에서 굴려 봅니다.

    cooldown을 두면 한 번 나간 종목을 그 종목 기준 며칠 동안 다시 사지
    않습니다. cooldown_after가 "손실"이면 잃고 나온 경우에만 막습니다.

    greedy=True면 빈 자리를 그날 후보로 끝까지 채웁니다. 기본은 아닙니다.
    자리 수만큼만 위에서부터 보고, 그중 이미 들고 있는 종목이 있으면 그
    자리는 비워 둡니다. 지난 회차들이 모두 이 셈으로 나온 수치입니다.

    size는 한 종목에 자리를 몇 개 쓸지 돌려주는 함수입니다. 기본은 하나씩
    입니다. 둘을 쓰면 그만큼 자리가 줄고, 손익도 두 몫으로 셉니다. 승률과
    매매당 수익은 자리 수와 상관없는 값이므로 그대로 한 번씩 셉니다.

    brake=(깊이, 남길 몫)을 두면 지갑이 꼭대기에서 그만큼 파인 동안 자리를
    그 몫만큼만 씁니다. 끝난 매매만으로 지갑을 세므로 뒷날을 보지 않습니다.
    파인 뒤에 줄이는 것이라 회복 구간의 수익도 함께 깎입니다. 그 값을 치르고
    골을 줄이려는 것입니다.

    realistic=True면 실제로 할 수 없는 매매를 뺍니다. 상한가에 붙은 날은
    사려는 사람만 있어 종가에 살 수 없고, 하한가에 붙은 날은 팔 수 없습니다.
    사는 쪽은 그날을 건너뛰고, 파는 쪽은 팔 수 있는 날까지 미룹니다.

    per_window=(수, 날)을 두면 최근 그 날수 안에 그만큼까지만 새로 담습니다
    (하루 제한을 며칠로 늘린 것입니다). apart는 (후보, 지금 들고 있는 줄들)을
    받아 함께 담아도 되는지 돌려주는 함수입니다. 같이 물릴 만한 것을 한꺼번에
    담지 않으려는 것입니다.

    per_day를 두면 하루에 그만큼만 새로 담습니다. busy_cap을 두면 자리가
    남아 있어도 그만큼까지만 채우고 나머지는 현금으로 둡니다. 둘 다 그날의
    한 줄을 받아 수를 돌려주는 함수여도 됩니다(그날 형편에 따라 달리 할 때). delay를 두면 걸린 날
    바로 사지 않고 그 종목 기준 며칠 뒤 종가에 삽니다. 판단은 걸린 날에
    끝나 있으므로 뒷날을 보는 것이 아닙니다.
    """
    lane = lanes(prices)
    picks = {}
    for row in rows:
        if holds(row) and (since is None or row["date"] >= since):
            picks.setdefault(row["date"], []).append(row)
    days = sorted(picks)
    if not days:
        return None
    rank = rank or (lambda r: r.get("중기 이격밴드") or 0)
    size = size or (lambda r: 1)
    open_slots, trades, missed, held_days = {}, [], 0, []
    rest = {}                # 종목별로 '이 자리 뒤에야 다시 산다'는 자리입니다.
    opened_on = []           # 새로 담은 날들. per_window가 이것을 셉니다.
    ledger = []              # detail=True일 때만. 매매 하나하나를 적어 둡니다.
    busy, seen, year_gains = 0, 0, {}
    weighted = []            # 자리 수를 곱한 손익. 연수익은 이것으로 냅니다.
    purse = crest = 1.0      # 끝난 매매만으로 센 지갑. brake가 이것을 봅니다.
    for day in days:
        for code in list(open_slots):
            spot = open_slots[code]
            closes = lane[code]["closes"]
            step = spot["step"] + 1
            index = spot["i"] + step
            if index >= len(closes) or step > cap:
                del open_slots[code]
                continue
            spot["peak"] = max(spot["peak"], closes[index])
            one = lane[code]
            if realistic and locked(closes, one["날"], index, -1):
                # 하한가에 붙은 날은 팔 수 없습니다. 팔 수 있는 날까지 갑니다.
                spot["step"] = step
                continue
            if exit_at(one, spot["i"], spot["price"], step, spot["peak"],
                       spot["row"]):
                gain = (closes[index] / spot["price"] - 1) * 100 - cost
                trades.append(gain)
                weighted.append(gain * spot["자리"])
                purse *= 1 + gain * spot["자리"] / 100 / slots
                crest = max(crest, purse)
                year_gains.setdefault(day[:4], []).append(gain * spot["자리"])
                held_days.append(step)
                if cooldown and (cooldown_after != "손실" or gain <= 0):
                    rest[code] = index + cooldown
                if detail:
                    ledger.append({"code": code, "산 날": spot["row"]["date"],
                                   "판 날": day, "들고": step, "자리": spot["자리"],
                                   "손익": round(gain, 2), "행": spot["row"]})
                del open_slots[code]
            else:
                spot["step"] = step
        seen += 1
        used = sum(spot["자리"] for spot in open_slots.values())
        busy += used
        top = slots
        if brake:
            deep, share = brake
            if purse / crest - 1 <= -deep / 100:
                top = max(1, int(slots * share))
        if busy_cap is not None:
            want = busy_cap(picks[day][0]) if callable(busy_cap) else busy_cap
            top = min(top, max(int(want), 0))
        room = top - used
        ready = [row for row in sorted(picks[day], key=rank)
                 if row["i"] >= rest.get(row["code"], 0)]
        # 빈 자리 수만큼만 위에서부터 봅니다. 그중 이미 들고 있는 종목이 있으면
        # 그 자리는 그날 비워 둡니다. greedy=True면 다음 후보로 마저 채웁니다.
        bought = 0
        if per_window:
            span, back = per_window
            edge = (datetime.strptime(day, "%Y%m%d")
                    - timedelta(days=back)).strftime("%Y%m%d")
            lately = [when for when in opened_on if when >= edge]
        for row in (ready if greedy else ready[:max(room, 0)]):
            allowed = (per_day(row) if callable(per_day) else per_day) \
                if per_day is not None else None
            if used >= top or (allowed is not None and bought >= allowed):
                break
            if per_window and len(lately) + bought >= per_window[0]:
                break
            if row["code"] in open_slots:
                continue
            if apart is not None and not apart(
                    row, [spot["row"] for spot in open_slots.values()]):
                continue
            spot = row["i"] + delay
            one = lane[row["code"]]
            if spot >= len(one["closes"]):
                continue
            if realistic and locked(one["closes"], one["날"], spot, 1):
                continue        # 상한가에 붙은 날은 종가에 살 수 없습니다.
            # 자리가 모자라면 그 종목이 원하는 만큼만 줄여 담습니다.
            want = min(max(int(size(row)), 1), top - used)
            open_slots[row["code"]] = {"i": spot, "price": one["closes"][spot],
                                       "step": 0, "peak": one["closes"][spot],
                                       "row": row, "자리": want}
            used += want
            bought += 1
            opened_on.append(day)
        missed += max(0, len(ready) - max(room, 0))
    if len(trades) < 60:
        return None
    ordered = sorted(trades)
    cut = max(1, len(ordered) // 10)
    years = int(days[-1][:4]) - int(days[0][:4]) + 1
    dip = deepest(weighted, slots)
    return {"매매": len(trades), "놓침": missed,
            "승률": round(sum(1 for t in trades if t > 0) / len(trades) * 100, 1),
            "평균": round(sum(trades) / len(trades), 2),
            "중앙": round(ordered[len(ordered) // 2], 2),
            "하위10%": round(sum(ordered[:cut]) / cut, 1), "최악": round(ordered[0], 1),
            "보유중앙": sorted(held_days)[len(held_days) // 2],
            "가동률": round(busy / (seen * slots) * 100, 1),
            "최대낙폭": round(dip, 1), "연패": streak(trades),
            "연수익": round(sum(weighted) / slots / max(years, 1), 2),
            "해마다": {y: round(sum(v) / slots, 1) for y, v in sorted(year_gains.items())},
            **({"매매목록": ledger} if detail else {})}


def exit_mixed(take, stop, give_back, arm, limit):
    """익절은 고정, 지키는 것은 되돌림으로.

    고정 익절은 큰 상승을 끝까지 받아 내고, 되돌림은 오르다 꺾인 것을
    이익이 남아 있을 때 내보냅니다. 손절은 그대로 두어 바닥을 막습니다.
    """
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        move = (lane["closes"][spot] / price - 1) * 100
        if move >= take or move <= -stop or step >= limit:
            return True
        top = (peak / price - 1) * 100
        return top >= arm and move <= top - give_back
    return go


def exit_per_tier(tier_of, exits, fallback=None):
    """층마다 다른 청산을 씁니다.

    깊이 벌어져 산 것과 얕게 벌어져 산 것은 되돌아오는 속도가 다릅니다.
    센 층은 길게 들고 큰 폭을 노리고, 약한 층은 짧게 끊는 식으로 나눠
    보기 위한 껍데기입니다. 층을 알 수 없으면 fallback으로 보냅니다.
    """
    def go(lane, start, price, step, peak, row=None):
        tier = tier_of(row) if row is not None else None
        pick = exits.get(tier, fallback or exits[min(exits)])
        return pick(lane, start, price, step, peak, row)
    return go


def jitter(rank, size=0.05, seed=0):
    """거의 같은 후보들의 차례만 아주 조금 흔듭니다.

    같은 층 안에서 이격밴드가 0.01σ 차이로 갈린 둘 중 누구를 먼저 담는지는
    실력이 아닙니다. 그런 것을 흔들어 보면 결과가 얼마나 흔들리는지 알 수
    있고, 그것이 두 방법을 견줄 때 쓸 자가 됩니다.
    """
    picker = random.Random(seed)
    noise = {}

    def key(row):
        spot = (row["code"], row["date"])
        if spot not in noise:
            noise[spot] = picker.uniform(-size, size)
        got = rank(row)
        if isinstance(got, tuple):
            return got[:-1] + (got[-1] + noise[spot],)
        return got + noise[spot]
    return key


def wobble(rows, prices, holds, exit_at, tries=6, size=0.05, rank=None, **kw):
    """같은 방법을 여러 번, 차례만 조금씩 달리해 돌려 봅니다.

    한 번 돌려 나온 수치 하나로는 두 방법을 견줄 수 없습니다. 15회차에서
    재어 보니 건드리면 안 되는 것을 건드려도 연수익이 4%p 안팎 흔들렸습니다.
    그래서 가운데 값과 폭을 함께 냅니다. 폭보다 작은 차이는 차이가 아닙니다.
    """
    rank = rank or (lambda r: r.get("중기 이격밴드") or 0)
    found = [run(rows, prices, holds, exit_at, rank=rank, **kw)]
    found += [run(rows, prices, holds, exit_at, rank=jitter(rank, size, seed), **kw)
              for seed in range(1, tries)]
    got = [one for one in found if one]
    if not got:
        return None
    gains = sorted(one["연수익"] for one in got)
    dips = sorted(one["최대낙폭"] for one in got)
    base = found[0]
    return {**(base or got[0]), "연수익": gains[len(gains) // 2],
            "그대로": base["연수익"] if base else None,
            "가장 낮음": gains[0], "가장 높음": gains[-1],
            "폭": round(gains[-1] - gains[0], 2),
            # 골에도 자를 대야 합니다. 골의 폭보다 작은 차이는 차이가 아닙니다.
            "최대낙폭": dips[len(dips) // 2],
            "골 폭": round(dips[-1] - dips[0], 2), "돌린 수": len(gains)}


def walk(lane_one, row, exit_at, cap=60):
    """신호 하나를 이 청산으로 끝까지 끌고 갑니다. 자리 다툼은 없습니다.

    자리를 나눠 굴리면 청산을 바꾸는 순간 들고 있는 날이 바뀌고, 그러면 그
    뒤의 자리를 누가 차지하는지가 통째로 바뀝니다. 그때 재는 것은 '청산의
    값'이 아니라 '다른 후보 묶음의 값'입니다. 그래서 청산끼리 견줄 때는
    같은 신호를 놓고 청산만 갈아 끼웁니다.
    """
    closes = lane_one["closes"]
    start = row["i"]
    if start + 1 >= len(closes):
        return None
    price = peak = closes[start]
    for step in range(1, cap + 1):
        spot = start + step
        if spot >= len(closes):
            return None
        peak = max(peak, closes[spot])
        if exit_at(lane_one, start, price, step, peak, row):
            return ((closes[spot] / price - 1) * 100 - COST, step)
    return None


def paired(rows, prices, ways, cap=60, floor=60):
    """같은 신호를 여러 청산으로 끌고 가 나란히 견줍니다.

    하루당은 평균을 들고 있던 날로 나눈 값입니다. 자리가 정해져 있으면
    '한 번에 얼마를 버느냐'보다 '하루에 얼마를 버느냐'가 중요합니다.
    """
    lane = lanes(prices)
    # 끝자락의 신호는 느린 청산이 끝을 못 봅니다. 그런 신호는 통째로 뺍니다.
    # 하나라도 값이 없는 신호를 남겨 두면 청산마다 모집단이 달라집니다.
    walked = {}
    for row in rows:
        if row["code"] not in lane:
            continue
        got = {tag: walk(lane[row["code"]], row, exit_at, cap)
               for tag, exit_at in ways.items()}
        if all(one is not None for one in got.values()):
            walked[(row["code"], row["date"])] = (row, got)
    if len(walked) < floor:         # 표본이 모자라면 숫자를 내지 않습니다.
        return {}
    codes = len({code for code, _ in walked})
    found = {}
    for tag in ways:
        gains = sorted(got[tag][0] for _, got in walked.values())
        hold = sum(got[tag][1] for _, got in walked.values()) / len(walked)
        cut = max(1, len(gains) // 10)
        mean = round(sum(gains) / len(gains), 2)
        days = round(hold, 1) or 1.0
        found[tag] = {
            "건수": len(gains), "종목": codes,
            "승률": round(sum(1 for g in gains if g > 0) / len(gains) * 100, 1),
            "평균": mean, "중앙": round(gains[len(gains) // 2], 2),
            "하위10%": round(sum(gains[:cut]) / cut, 1),
            "보유": days, "하루당": round(mean / days, 3)}
    return found


def moves(prices):
    """종목마다 하루 수익률을 미리 만들어 둡니다. 닮은 정도를 잴 때 씁니다."""
    found = {}
    for code, block in prices.items():
        closes = [c for _, c in block["rows"]]
        found[code] = [0.0] + [(closes[k] / closes[k - 1] - 1) if closes[k - 1]
                               else 0.0 for k in range(1, len(closes))]
    return found


def kinship(steps, row, other, back=60):
    """두 종목이 최근 back일 동안 얼마나 같이 움직였는지(-1~1).

    그날까지의 수익률만 봅니다(…, i-1, i). 뒷날은 쓰지 않습니다. 자리 다툼과
    상관없이, 같이 물릴 만한 것을 한꺼번에 담지 않으려고 잽니다.
    """
    one = steps.get(row["code"])
    two = steps.get(other["code"])
    if one is None or two is None:
        return 0.0
    i, j = row["i"], other["i"]
    if i < back or j < back:
        return 0.0
    left, right = one[i - back + 1:i + 1], two[j - back + 1:j + 1]
    n = len(left)
    if n < back:
        return 0.0
    ma, mb = sum(left) / n, sum(right) / n
    top = sum((x - ma) * (y - mb) for x, y in zip(left, right))
    wide = (sum((x - ma) ** 2 for x in left) ** 0.5
            * sum((y - mb) ** 2 for y in right) ** 0.5)
    return top / wide if wide else 0.0


def unlike(steps, edge=0.6, back=60):
    """이미 들고 있는 것과 너무 같이 움직이는 종목은 담지 않습니다."""
    def ok(row, held):
        return all(kinship(steps, row, one, back) < edge for one in held)
    return ok


# 가격제한폭. 2015년 6월 15일부터 ±30%, 그 전에는 ±15%입니다. 더 옛날에는
# 더 좁았지만(±12%, ±8%…) 여기서는 두 마디로만 나눕니다. 정확히 문턱에
# 닿았는지 세는 것이 아니라 '문턱에 붙어 거래가 막혔을 만한 날'을 거르는
# 것이 목적이라, 문턱보다 조금 안쪽(0.95배)에서 잡습니다.
WIDENED = "20150615"


def limit_of(day):
    return 0.30 if day >= WIDENED else 0.15


def locked(closes, days, i, side):
    """그날이 상한가(위) 또는 하한가(아래)에 붙어 있었는지.

    상한가에 붙은 날은 사려는 사람만 있고 파는 사람이 없어 종가에 살 수
    없습니다. 하한가에 붙은 날은 그 반대로 팔 수 없습니다. 지나간 자료로
    시늉만 하는 시뮬레이션에서 이런 날을 그냥 사고파는 것으로 세면, 실제로는
    할 수 없는 매매가 성적에 섞입니다.

    시가·고가·저가가 없어 종가 변동폭으로만 가립니다. 어림이며, 문턱 가까이
    올랐다가 풀린 날까지 함께 걸립니다. 덜 세는 쪽보다 더 세는 쪽이 안전합니다.
    """
    if i <= 0 or i >= len(closes) or not closes[i - 1]:
        return False
    move = closes[i] / closes[i - 1] - 1
    edge = limit_of(days[i]) * 0.95
    return move >= edge if side > 0 else move <= -edge
