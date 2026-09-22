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
              cost=COST, rank=None, since=None):
    """자금을 나눠 담고 실제로 굴려 봅니다.

    한 종목씩 따로 재면 '같은 날 후보가 쉰 개면 쉰 개를 다 산다'는 셈이
    됩니다. 실제로는 자리가 정해져 있고, 자리가 차면 다음 후보는 놓칩니다.
    놓친 기회까지 세어야 실제에 가까운 수치가 나옵니다.

    자리 하나에 자금의 1/slots을 넣고, 먼저 닿는 쪽(익절·손절·기한)에서
    끝냅니다. 같은 종목을 겹쳐 담지 않습니다.
    """
    series = {code: [c for _, c in block["rows"]] for code, block in prices.items()}
    picks = {}
    for row in rows:
        if holds(row) and (since is None or row["date"] >= since):
            picks.setdefault(row["date"], []).append(row)
    days = sorted(picks)
    if not days:
        return None
    rank = rank or (lambda r: r.get("중기 이격밴드") or 0)

    open_slots, trades, missed = {}, [], 0
    held, days_seen, year_gains, held_days = {}, set(), {}, []
    for day in days:
        # 먼저 정리할 자리를 정리합니다.
        for code in list(open_slots):
            spot = open_slots[code]
            closes = series[code]
            step = spot["step"] + 1
            index = spot["i"] + step
            if index >= len(closes):
                del open_slots[code]
                continue
            move = (closes[index] / spot["price"] - 1) * 100
            done = None
            if move >= take:
                done = take
            elif move <= -stop:
                done = -stop
            elif step >= limit:
                done = move
            if done is None:
                spot["step"] = step
                continue
            trades.append(done - cost)
            year_gains.setdefault(day[:4], []).append(done - cost)
            held_days.append(step)
            del open_slots[code]
        days_seen.add(day)
        held[day] = len(open_slots)
        room = slots - len(open_slots)
        today = sorted(picks[day], key=rank)
        for row in today[:max(room, 0)]:
            if row["code"] in open_slots:
                continue
            open_slots[row["code"]] = {"i": row["i"], "price": row["price"], "step": 0}
        missed += max(0, len(today) - max(room, 0))
    if len(trades) < 60:
        return None
    ordered = sorted(trades)
    cut = max(1, len(ordered) // 10)
    wins = sum(1 for t in trades if t > 0)
    # 자리가 실제로 얼마나 차 있었는지. 비어 있는 동안 그 몫은 놀았습니다.
    # 이것을 모르면 '연 8%'가 어디서 왔는지 알 수 없습니다.
    filled = sum(held.values())
    span = len(days_seen)
    busy = filled / (span * slots) * 100 if span else 0
    by_year = {}
    for year, gains in year_gains.items():
        by_year[year] = round(sum(gains) / slots, 2)
    # 자리가 slots개이므로 한 번의 매매에는 자금의 1/slots이 들어갑니다.
    # 자리가 비어 있는 동안 그 몫은 놀고 있으므로, 거기까지 넣어 잽니다.
    years = (int(days[-1][:4]) - int(days[0][:4])) + 1
    yearly = sum(trades) / slots / max(years, 1)
    return {"자리": slots, "매매": len(trades), "놓침": missed,
            "연수익": round(yearly, 2), "연매매": round(len(trades) / max(years, 1), 1),
            "가동률": round(busy, 1), "해마다": dict(sorted(by_year.items())),
            "보유일중앙": sorted(held_days)[len(held_days) // 2] if held_days else 0,
            "승률": round(wins / len(trades) * 100, 1),
            "평균": round(sum(trades) / len(trades), 2),
            "중앙": round(sorted(trades)[len(trades) // 2], 2),
            "하위10%": round(sum(ordered[:cut]) / cut, 1),
            "최악": round(ordered[0], 1)}
