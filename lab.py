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
import statistics
from pathlib import Path

import study

# 단기·중기·중장기·장기 네 축입니다. 같은 이동평균이라도 길이에 따라
# 말하는 것이 다릅니다. 짧은 것은 며칠의 흔들림을, 긴 것은 몇 달의 흐름을
# 봅니다. 네 축을 함께 두면 '무엇이 어긋났는지'가 읽힙니다.
AXES = {"단기": 5, "중기": 20, "중장기": 60, "장기": 120}
SPANS = tuple(sorted(set(AXES.values()) | {10, 40}))
SLOPE_STEP = 5      # 기울기를 잴 간격. 한 주입니다.
BAND_WINDOW = 120   # 이격이 이례적인지 볼 때 견줄 지난 구간.
HORIZON = 20            # 기본으로 보는 앞날. 스무 거래일입니다.
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


def build(prices=None, horizons=(5, 20, 60), warmup=120):
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
            if move >= take:
                done = (take, step); break
            if move <= -stop:
                done = (-stop, step); break
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
