"""미래를 본 값이 하나라도 있으면 멈춥니다.

과거 자료로 규칙을 시험할 때 가장 크고 가장 흔한 잘못은, 그날 알 수 없던
것을 그날의 판단에 쓰는 일입니다. 한 번 섞이면 어떤 규칙이든 좋아 보이고,
숫자만 봐서는 알아챌 수 없습니다. 실제로 이 저장소에서도 한 번 있었습니다.
오늘의 실적으로 몇 해 전의 날을 판정하고 있었습니다.

그래서 일곱 겹으로 막습니다.

1. **더럽히기** — 그날 뒤의 값을 엉뚱한 수로 바꿔 다시 계산합니다. 특징이
   조금이라도 달라지면 그 값은 뒷날을 본 것입니다. '안 쓴 척'이 아니라
   '조금 쓴 것'까지 잡힙니다.
2. **잘라내기** — 그날까지만 남기고 다시 계산합니다. 뒷날 자료가 아예 없어도
   같은 값이 나와야 합니다.
3. **날짜 확인** — 실적과 목표가는 발표일이 그날보다 뒤면 쓰지 않았는지
   하나씩 짚습니다.
4. **공시·시가총액 검사** — 신호에 붙인 공시가 하나라도 그날보다 뒤에 접수된 것이면
   멈춥니다. 공시는 접수일에 공개되므로, 그 뒤의 것을 쓰면 그대로
   미래참조입니다. 붙이는 쪽(events.py)에서 한 번 거르고 여기서 다시
   짚습니다.
5. **가로줄 검사** — 그날 온 종목을 가로로 견주어 만든 값(시장 이격 같은
   것)은 한 종목만 떼어 다시 만들 수가 없어 1·2번이 닿지 않습니다. 대신
   그날 뒤의 줄을 통째로 더럽히거나 잘라 낸 뒤 다시 만들어, 그날 값이
   그대로인지 봅니다. 이 검사가 닿지 않은 가로줄 값이 하나라도 있으면
   그대로 멈춥니다. 빼먹어도 지나가는 일이 없도록 열어 두지 않습니다.

일곱 겹 모두 통과해야 조사를 돌립니다. 하나라도 어긋나면 멈추고 어느 값이
어긋났는지 말합니다.
"""
from __future__ import annotations

import random

import caps
import events
import lab
import money
import study

# 앞날 수익률은 뒷날을 보라고 만든 값입니다. 검사에서 뺍니다.
LABELS = {"ahead"}
# 종목·날짜·자리는 값이 아니라 이름표입니다.
KEYS = {"code", "date", "i"}
# 그날 온 종목을 가로로 견주어 만든 값입니다. 한 종목만 떼어 내면 만들 수가
# 없으므로 1·2번 검사에서 빼고, 대신 check_cross_section이 따로 맡습니다.
# 여기에 이름을 올리면 1·2번을 면제받는 것이므로, verify가 이 이름들이
# 정말 4번 검사를 지났는지 되짚습니다.
CROSS = {"시장 이격", "상대 이격", "시장 출렁임"}
# 시가총액과 그날 순위. 주식수(접수일)와 가로줄이 함께 들어간 값이라 1·2번이
# 닿지 않습니다. check_caps가 둘 다 맡습니다.
CAPPED = {caps.RANK, caps.SIZE}
# 거래대금에서 온 값. 한 종목의 일봉만으로는 만들 수 없어 1·2번이 닿지
# 않습니다. check_money가 맡습니다.
TRADED = {money.MONEY, money.SHARE}
# 공시에서 온 값입니다. 가로줄과 같은 까닭으로 1·2번이 닿지 않습니다(한 종목의
# 일봉만으로는 다시 만들 수 없습니다). check_filings가 따로 맡고, verify가
# 정말 그 검사를 지났는지 되짚습니다.
FILED = {events.MARK, events.AGE}


class LookaheadError(AssertionError):
    """미래를 본 값이 있습니다. 결과를 믿을 수 없으니 멈춥니다."""


class ShallowPoolError(AssertionError):
    """문턱이 자료가 모자라 조용히 느슨해져 있습니다.

    미래를 본 것은 아니지만, 재고 있는 것이 적어 둔 것과 다릅니다. 그대로
    두면 수치가 실제보다 좋게 나오므로 같은 무게로 멈춥니다.
    """


POOL_FLOOR = 0.8        # 순위를 매긴 종목이 그날 값이 있는 종목의 이만큼은 돼야


def _one(code, block):
    return {code: block}


def _pick(rows, code, day):
    return next((r for r in rows if r["code"] == code and r["date"] == day), None)


def _compare(clean, dirty, code, day, how, skip=frozenset()):
    gaps = []
    for key, value in clean.items():
        if key in LABELS or key in KEYS or key in skip:
            continue
        other = dirty.get(key)
        if isinstance(value, float) and isinstance(other, float):
            if abs(value - other) > 1e-9:
                gaps.append(f"{key}: {value!r} → {other!r}")
        elif value != other:
            gaps.append(f"{key}: {value!r} → {other!r}")
    if gaps:
        raise LookaheadError(
            f"{code} {day} · {how} 뒤에 값이 달라졌습니다. 그날 알 수 없던 것을 "
            f"쓰고 있습니다 → " + " / ".join(gaps[:5]))


def check_corruption(prices, rows, samples=40, seed=7, warmup=120):
    """그날 뒤의 값을 엉뚱하게 바꿔도 특징이 그대로인지 봅니다."""
    picker = random.Random(seed)
    usable = [r for r in rows if r["i"] > warmup + 5]
    if not usable:
        return 0
    done = 0
    for row in picker.sample(usable, min(samples, len(usable))):
        code, day, spot = row["code"], row["date"], row["i"]
        block = prices[code]
        broken = list(block["rows"])
        for k in range(spot + 1, len(broken)):
            # 뒤쪽을 알아볼 수 없는 값으로 바꿉니다. 부호도 크기도 뒤집습니다.
            broken[k] = (broken[k][0], broken[k][1] * (7.0 if k % 2 else 0.11))
        again = lab.build(_one(code, {"name": block["name"], "rows": broken}),
                          warmup=warmup)
        found = _pick(again, code, day)
        if found is None:
            continue
        _compare(row, found, code, day, "뒷날 값을 바꾼", skip=CROSS | FILED | CAPPED | TRADED)
        done += 1
    return done


def check_truncation(prices, rows, samples=40, seed=11, warmup=120):
    """그날까지만 남겨도 특징이 그대로인지 봅니다."""
    picker = random.Random(seed)
    usable = [r for r in rows if r["i"] > warmup + 5]
    if not usable:
        return 0
    done = 0
    for row in picker.sample(usable, min(samples, len(usable))):
        code, day, spot = row["code"], row["date"], row["i"]
        block = prices[code]
        # 앞날 수익률을 낼 수 있을 만큼만 남기고, 그 뒤는 잘라 냅니다.
        cut = block["rows"][:spot + 1 + max(lab.HORIZON, 5)]
        again = lab.build(_one(code, {"name": block["name"], "rows": cut}),
                          warmup=warmup, horizons=(5,))
        found = _pick(again, code, day)
        if found is None:
            continue
        _compare(row, found, code, day, "뒷날을 잘라 낸", skip=CROSS | FILED | CAPPED | TRADED)
        done += 1
    return done


def check_dates(rows, samples=400, seed=13):
    """실적과 목표가가 그날보다 뒤에 나온 것은 아닌지 하나씩 짚습니다."""
    picker = random.Random(seed)
    picked = picker.sample(rows, min(samples, len(rows)))
    looked = 0
    for row in picked:
        day = row["date"]
        if "매출성장" in row or "영업이익률" in row:
            stamps = [d for d, _ in study.money_timeline(row["code"]) if d <= day]
            if not stamps:
                raise LookaheadError(
                    f"{row['code']} {day} · 그날까지 나온 결산이 없는데 실적이 붙어 "
                    "있습니다.")
            looked += 1
        if "목표가괴리" in row:
            stamps = [d for d, _ in study.target_timeline(row["code"]) if d <= day]
            if not stamps:
                raise LookaheadError(
                    f"{row['code']} {day} · 그날까지 나온 목표가가 없는데 괴리가 "
                    "붙어 있습니다.")
            looked += 1
    return looked


def check_cross_section(rows, samples=3, seed=17):
    """가로로 견주어 만든 값이 뒷날 줄에 기대고 있지 않은지 봅니다.

    한 종목만 떼어 낼 수 없는 값이므로, 이번에는 줄이 아니라 날을 자릅니다.
    고른 날 뒤의 줄을 통째로 엉뚱하게 바꾸고, 또 통째로 잘라 낸 뒤 다시
    만들어, 그날 값이 꿈쩍도 하지 않는지 봅니다. 어느 이름을 몇 번 짚었는지
    세어 돌려주어, verify가 빠진 이름이 없는지 되짚을 수 있게 합니다.
    """
    seen = {name: 0 for name in CROSS}
    present = {name for row in rows for name in CROSS if name in row}
    if not present:
        return seen
    picker = random.Random(seed)
    days = sorted({row["date"] for row in rows})
    for day in picker.sample(days[len(days) // 4:], min(samples, len(days))):
        here = [row for row in rows if row["date"] == day]
        if not here:
            continue
        # 뒷날 줄을 통째로 더럽힙니다. 가로 중앙값이 뒷날을 보고 있다면 움직입니다.
        dirty = []
        for row in rows:
            if row["date"] <= day:
                dirty.append(dict(row))
                continue
            copy = dict(row)
            gap = copy.get("중기 이격")
            if gap is not None:
                copy["중기 이격"] = gap * -13.0 - 500.0
            dirty.append(copy)
        # 뒷날 줄을 통째로 바꾼 것입니다. 그날 값이 꿈쩍하면 뒷날을 본 것입니다.
        lab.market_relative(dirty)
        # 뒷날 줄을 아예 없앱니다. 없어도 같은 값이 나와야 합니다.
        cut = [dict(row) for row in rows if row["date"] <= day]
        lab.market_relative(cut)
        for tag, again in (("뒷날 줄을 더럽힌", dirty), ("뒷날 줄을 잘라 낸", cut)):
            found = {(row["code"], row["date"]): row for row in again
                     if row["date"] == day}
            for row in here:
                other = found.get((row["code"], row["date"]))
                if other is None:
                    raise LookaheadError(
                        f"{row['code']} {day} · {tag} 뒤에 그 줄이 사라졌습니다.")
                for name in present:
                    if row.get(name) != other.get(name):
                        raise LookaheadError(
                            f"{row['code']} {day} · {tag} 뒤에 값이 달라졌습니다 → "
                            f"{name}: {row.get(name)!r} → {other.get(name)!r}")
                    seen[name] += 1
    return seen


def check_filings(rows, samples=600, seed=19):
    """붙인 공시가 그날 이전에 접수된 것인지 하나씩 짚습니다.

    갈래만 보고 넘어가면 안 됩니다. 그 갈래의 공시가 그날 이전 window일
    안에 **실제로** 있었는지를 원장(timeline)에서 다시 찾습니다. 없으면
    어디선가 뒷날 것이 흘러든 것입니다.
    """
    picker = random.Random(seed)
    have = [row for row in rows if events.MARK in row]
    if not have:
        return 0
    looked = 0
    for row in picker.sample(have, min(samples, len(have))):
        day, code = row["date"], row["code"]
        stamps = [when for when, _ in events.timeline(code) if when <= day]
        for kind in row[events.MARK]:
            found = [when for when, name in events.timeline(code)
                     if name == kind and when <= day
                     and when >= events._back(day, events.WINDOW)]
            if not found:
                raise LookaheadError(
                    f"{code} {day} · '{kind}' 공시를 붙여 놓았는데 그날까지 "
                    "접수된 그 갈래의 공시가 없습니다. 뒷날 것을 본 것입니다.")
            looked += 1
        age = row.get(events.AGE)
        if age is not None:
            if age < 0:
                raise LookaheadError(
                    f"{code} {day} · 공시 나이가 {age}일입니다. 아직 나지 않은 "
                    "공시를 보고 있습니다.")
            if not stamps:
                raise LookaheadError(
                    f"{code} {day} · 그날까지 접수된 공시가 없는데 나이가 "
                    f"{age}일로 붙어 있습니다.")
            looked += 1
    return looked


def check_caps(rows, samples=500, seed=23, days=12):
    """시가총액과 그날 순위를 짚습니다.

    주식수는 보고서 접수일에 공개됩니다. 그 뒤에 나온 수로 그날의 시가총액을
    만들면 미래참조입니다. 액면분할·유상증자 자리에서 특히 위험합니다.
    순위는 그날 줄들끼리 세운 것이므로, 그날 줄만 다시 세워 같은지 봅니다.
    이름마다 몇 번 짚었는지 세어 돌려주어, verify가 빠진 이름을 되짚습니다.
    """
    seen = {name: 0 for name in CAPPED}
    have = [row for row in rows if caps.SIZE in row]
    if not have:
        return seen
    picker = random.Random(seed)
    for row in picker.sample(have, min(samples, len(have))):
        day, code = row["date"], row["code"]
        count = caps.known_by(code, day)
        if count is None:
            raise LookaheadError(
                f"{code} {day} · 그날까지 접수된 주식수가 없는데 시가총액이 "
                "붙어 있습니다.")
        want = count * row["price"]
        if abs(want - row[caps.SIZE]) > 1:
            later = [n for when, n in caps.timeline(code) if when > day]
            hint = (" (뒷날 주식수를 쓴 것으로 보입니다)"
                    if any(abs(n * row["price"] - row[caps.SIZE]) <= 1 for n in later)
                    else "")
            raise LookaheadError(
                f"{code} {day} · 시가총액이 그날 주식수로 만든 값과 다릅니다"
                f"{hint}.")
        seen[caps.SIZE] += 1
    # 순위는 그날 줄들끼리 다시 세워 봅니다. 그날 자료만 쓰는지 보는 것입니다.
    ranked = {}
    for row in rows:
        if caps.RANK in row and caps.SIZE in row:
            ranked.setdefault(row["date"], []).append(row)
    if ranked:
        for day in picker.sample(sorted(ranked), min(days, len(ranked))):
            here = sorted(ranked[day], key=lambda one: -one[caps.SIZE])
            for place, one in enumerate(here, 1):
                if one[caps.RANK] != place:
                    raise LookaheadError(
                        f"{one['code']} {day} · 그날 줄만으로 다시 세운 순위는 "
                        f"{place}등인데 {one[caps.RANK]}등이 붙어 있습니다.")
                seen[caps.RANK] += 1
    return seen


def check_money(rows, samples=400, seed=29):
    """붙인 거래대금이 그날까지의 것으로 만든 값인지 짚습니다.

    그날을 포함해 지난 스무 날의 중앙값이어야 합니다. 뒷날 거래대금이 한 날만
    섞여도 값이 달라지므로, 다시 만들어 견주면 바로 드러납니다.
    """
    seen = {name: 0 for name in TRADED}
    have = [row for row in rows if money.MONEY in row]
    if not have:
        return seen
    picker = random.Random(seed)
    for row in picker.sample(have, min(samples, len(have))):
        day, code = row["date"], row["code"]
        want = money.known_by(code, day)
        if want is None:
            raise LookaheadError(
                f"{code} {day} · 그날까지의 거래대금이 없는데 값이 붙어 "
                "있습니다.")
        if abs(want - row[money.MONEY]) > 1:
            raise LookaheadError(
                f"{code} {day} · 거래대금이 그날까지로 만든 값과 다릅니다.")
        # 그날 뒤의 거래대금을 엉뚱하게 바꿔도 값이 같아야 합니다.
        after = [value for when, value in money.timeline(code) if when > day]
        if after and want != money.known_by(code, day):
            raise LookaheadError(f"{code} {day} · 거래대금이 흔들립니다.")
        seen[money.MONEY] += 1
        if money.SHARE in row:
            seen[money.SHARE] += 1
    return seen


def check_anchor(prices, rows):
    """줄마다 적힌 자리(i)가 지금 일봉에서 정말 그날인지 봅니다.

    표를 한 번 구워 두고 일봉을 다시 받으면, 종목에 따라 앞쪽 날이 하나씩
    떨어져 나갑니다 — 수집기가 '오늘부터 서른 해 전'을 기준으로 잡기 때문에
    하루가 지나면 가장 오래된 날이 창 밖으로 밀립니다. 그러면 자리가 하나씩
    밀리는데, 매매 시뮬은 그 자리로 종가를 찾습니다. **하루 어긋난 값으로
    사고판 셈**이 됩니다.

    값이 1e-8쯤만 달라지므로 눈으로는 안 보이고, 더럽히기 검사에 우연히
    걸려야 드러납니다(47회차에 500종목 중 68종목이 그랬습니다). 그래서 자리와
    날짜가 맞는지 직접 봅니다. 종목마다 첫 줄과 끝 줄을 봅니다.
    """
    first, last = {}, {}
    for row in rows:
        code = row["code"]
        first.setdefault(code, row)
        last[code] = row
    off = []
    for code in first:
        block = prices.get(code)
        if not block:
            continue
        days = [d for d, _ in block["rows"]]
        for row in (first[code], last[code]):
            spot = row["i"]
            if not (0 <= spot < len(days)) or days[spot] != row["date"]:
                off.append(f'{code} {row["date"]}(자리 {spot})')
                break
    if off:
        raise LookaheadError(
            f"줄에 적힌 자리가 지금 일봉과 어긋납니다 — {len(off)}종목. "
            "표를 다시 구워야 합니다 → " + " / ".join(sorted(off)[:5])
            + (" …" if len(off) > 5 else ""))
    return len(first)


def check_gate(rows, top=100, slack=0.1, samples=40, seed=7, since=None):
    """문턱 안에 들었을 종목이 순위를 못 받고 있는지 봅니다.

    `check_pool`(55회차)은 "값이 있는 종목 중 몇 %가 순위를 받았나"를
    물었습니다. 그것은 아래쪽이 잘려도 울립니다. 물어야 할 것은 **위쪽**
    입니다 — 순위를 못 받은 종목 가운데 문턱 안에 들었을 것이 있나.

    그날의 크기를 모르는 종목의 크기를 어떻게 어림하나: **바로 다음에 그
    종목이 순위를 받은 날의 등수**를 씁니다. 같은 종목의 순위는 하루아침에
    수백 등씩 움직이지 않으므로, 그 등수가 문턱 안이면 그날도 안이었을
    공산이 큽니다. 뒷날 값을 쓰지만 **매매 판단이 아니라 자료가 찼는지를
    보는 데만** 씁니다 — 표에 넣지 않고, 여기서 세고 버립니다.

    문턱 자리 가운데 이렇게 비어 있는 몫이 slack을 넘으면 멈춥니다.

    since를 주면 그날부터만 봅니다. 조사에 안 쓰는 구간이 비어 있는 것은
    흠이 아닙니다 — 60회차에 2015·2016년을 조사에서 뺀 것이 그 까닭이고,
    그 두 해가 비어 있다고 멈추면 쓰지도 않는 자료 때문에 일을 못 합니다.
    """
    seen = {}
    for row in rows:
        place = row.get(caps.RANK)
        if place is not None:
            seen.setdefault(row["code"], []).append((row["date"], place))
    for code in seen:
        seen[code].sort()
    by_day = {}
    for row in rows:
        if since is not None and row["date"] < since:
            continue
        by_day.setdefault(row["date"], []).append(row)
    live = sorted(day for day, here in by_day.items()
                  if any(r.get(caps.RANK) is not None for r in here))
    if not live:
        return 0, 0.0
    picker = random.Random(seed)
    missing = ranked = 0
    for day in picker.sample(live, min(samples, len(live))):
        for row in by_day[day]:
            if row.get(caps.RANK) is not None:
                ranked += 1 if row[caps.RANK] <= top else 0
                continue
            later = seen.get(row["code"])
            if not later:
                continue
            place = next((p for when, p in later if when > day), None)
            if place is not None and place <= top:
                missing += 1
    share = missing / max(ranked + missing, 1)
    if share > slack:
        raise ShallowPoolError(
            f"문턱({top}등) 안에 들었을 종목의 {share * 100:.0f}%가 그날 "
            f"순위를 못 받고 있습니다(견딜 몫 {slack * 100:.0f}%). "
            "share-data를 마저 모으십시오.")
    return missing, round(share, 3)


def check_pool(rows, floor=POOL_FLOOR, samples=40, seed=7):
    """줄을 몇 종목으로 세웠는지 셉니다. 견주어 볼 값으로만 남깁니다.

    56·57회차에 이 수치 하나로 두 번 잘못 읽었습니다. 몫이 낮다고 문턱이
    느슨한 것도 아니고(아래쪽이 잘린 것일 수 있음), 높다고 맞는 것도
    아닙니다. 판단은 `check_gate`가 합니다.

    `caps.tag`는 그날 주식수가 접수된 종목끼리만 줄을 세웁니다. 주식수 자료가
    일부 종목에만 있으면 '코스피 100등 안'은 조용히 **'자료가 있는 N종목 중
    100등 안'**이 됩니다. 문턱이 느슨해진 만큼 성적이 좋게 나오는데, 어디에도
    그렇다고 적히지 않습니다 — 54회차에 507종목을 모아 두고 199종목으로 줄을
    세우고 있었던 것을 쉰 회차 만에 알았습니다.

    그날 값이 있는 종목 가운데 순위를 받은 몫이 floor 아래이면 멈춥니다.
    (종목, 몫)을 돌려줍니다.

    **한 줄도 순위가 없는 날은 빼고 셉니다.** 주식수 자료는 2015년부터라
    그 앞의 날은 아무도 순위를 못 받습니다. 그런 날까지 넣으면 몫이 자료의
    시작 시점을 재는 값이 되어 버립니다. 규칙이 실제로 고르는 날, 곧 순위가
    있는 날만 봐야 '문턱이 느슨한가'를 재는 것이 됩니다.
    """
    by_day = {}
    for row in rows:
        seen = by_day.setdefault(row["date"], [0, 0])
        seen[0] += 1
        if row.get(caps.RANK) is not None:
            seen[1] += 1
    live = sorted(day for day, seen in by_day.items() if seen[1])
    if not live:
        return 0, 0.0 if by_day else 1.0
    picker = random.Random(seed)
    days = picker.sample(live, min(samples, len(live)))
    here = sum(by_day[day][0] for day in days)
    ranked = sum(by_day[day][1] for day in days)
    share = ranked / here if here else 1.0
    # 순위가 한 줄도 없으면 그 문턱을 안 쓰고 있는 것입니다. 느슨한 것이
    # 아니라 없는 것이라, 아무것도 사지지 않으므로 그냥 둡니다.
    if ranked and share < floor:
        raise ShallowPoolError(
            f"순위를 매긴 종목이 그날 종목의 {share * 100:.0f}%뿐입니다"
            f"(있어야 할 몫 {floor * 100:.0f}%). '100등 안'이 실제로는 "
            f"'자료가 있는 것 중 100등 안'입니다. share-data를 마저 모으십시오.")
    return round(ranked / len(days)), round(share, 3)


def verify(prices, rows, samples=40, loud=True, pool=True, since=None):
    """아홉 겹을 모두 지나야 참입니다. 하나라도 어긋나면 멈춥니다.

    아홉째(줄 세운 종목)만 성격이 다릅니다 — 미래를 본 것이 아니라 문턱이
    자료 탓에 느슨해진 것을 봅니다. 자료를 아직 다 못 모은 동안에는
    pool=False로 끌 수 있지만, 그때 낸 수치는 실제보다 좋습니다.
    """
    zero = check_anchor(prices, rows)
    one = check_corruption(prices, rows, samples=samples)
    two = check_truncation(prices, rows, samples=samples)
    three = check_dates(rows)
    four = check_filings(rows)
    five = check_cross_section(rows)
    six = check_caps(rows)
    seven = check_money(rows)
    # 순위를 매긴 종목이 줄어 있으면 문턱이 느슨해진 것입니다. 표를 아직 다
    # 못 모은 동안에는 pool=False로 끌 수 있게 두되, 기본은 멈춥니다.
    eight = check_gate(rows, since=since) if pool else (0, None)
    # 1·2번을 면제받은 이름이 제 검사도 지나지 않았다면 아무도 보지 않은 것입니다.
    present = {name for row in rows for name in CROSS if name in row}
    missed = sorted(name for name in present if not five.get(name))
    if {name for row in rows for name in FILED if name in row} and not four:
        missed.append("공시")
    for name in sorted(CAPPED):
        if any(name in row for row in rows) and not six.get(name):
            missed.append(name)
    for name in sorted(TRADED):
        if any(name in row for row in rows) and not seven.get(name):
            missed.append(name)
    if missed:
        raise LookaheadError(
            "면제받은 값이 어느 검사도 지나지 않았습니다 → " + " / ".join(missed))
    if loud:
        print(f"미래참조 검사 통과 · 자리 확인 {zero}종목 · 더럽히기 {one}건 · 잘라내기 {two}건 · "
              f"날짜 확인 {three}건 · 공시 {four}건 · 가로줄 {sum(five.values())}건 "
              f"· 시가총액 {sum(six.values())}건 · 거래대금 {sum(seven.values())}건"
              + (f" · 문턱 밖 새는 자리 {eight[0]}({eight[1] * 100:.1f}%)"
                 if eight[1] is not None else " · 문턱 안 봄"))
    return {"anchor": zero, "corruption": one, "truncation": two, "dates": three,
            "filings": four, "cross": sum(five.values()),
            "caps": sum(six.values()), "money": sum(seven.values()),
            "gate": eight[0], "gate_share": eight[1]}


def build_verified(prices=None, samples=25, since=None, **kwargs):
    """특징을 만들고, 검사를 지난 것만 돌려줍니다.

    만들기와 검사를 따로 부르게 두면 언젠가 검사를 빼먹습니다. 한 문으로
    묶어 두면 빼먹을 수가 없습니다.
    """
    prices = prices if prices is not None else study.load_prices()
    rows = lab.build(prices, **kwargs)
    verify(prices, rows, samples=samples, since=since)
    return prices, rows
