"""미래를 본 값이 하나라도 있으면 멈춥니다.

과거 자료로 규칙을 시험할 때 가장 크고 가장 흔한 잘못은, 그날 알 수 없던
것을 그날의 판단에 쓰는 일입니다. 한 번 섞이면 어떤 규칙이든 좋아 보이고,
숫자만 봐서는 알아챌 수 없습니다. 실제로 이 저장소에서도 한 번 있었습니다.
오늘의 실적으로 몇 해 전의 날을 판정하고 있었습니다.

그래서 다섯 겹으로 막습니다.

1. **더럽히기** — 그날 뒤의 값을 엉뚱한 수로 바꿔 다시 계산합니다. 특징이
   조금이라도 달라지면 그 값은 뒷날을 본 것입니다. '안 쓴 척'이 아니라
   '조금 쓴 것'까지 잡힙니다.
2. **잘라내기** — 그날까지만 남기고 다시 계산합니다. 뒷날 자료가 아예 없어도
   같은 값이 나와야 합니다.
3. **날짜 확인** — 실적과 목표가는 발표일이 그날보다 뒤면 쓰지 않았는지
   하나씩 짚습니다.
4. **공시 검사** — 신호에 붙인 공시가 하나라도 그날보다 뒤에 접수된 것이면
   멈춥니다. 공시는 접수일에 공개되므로, 그 뒤의 것을 쓰면 그대로
   미래참조입니다. 붙이는 쪽(events.py)에서 한 번 거르고 여기서 다시
   짚습니다.
5. **가로줄 검사** — 그날 온 종목을 가로로 견주어 만든 값(시장 이격 같은
   것)은 한 종목만 떼어 다시 만들 수가 없어 1·2번이 닿지 않습니다. 대신
   그날 뒤의 줄을 통째로 더럽히거나 잘라 낸 뒤 다시 만들어, 그날 값이
   그대로인지 봅니다. 이 검사가 닿지 않은 가로줄 값이 하나라도 있으면
   그대로 멈춥니다. 빼먹어도 지나가는 일이 없도록 열어 두지 않습니다.

다섯 겹 모두 통과해야 조사를 돌립니다. 하나라도 어긋나면 멈추고 어느 값이
어긋났는지 말합니다.
"""
from __future__ import annotations

import random

import events
import lab
import study

# 앞날 수익률은 뒷날을 보라고 만든 값입니다. 검사에서 뺍니다.
LABELS = {"ahead"}
# 종목·날짜·자리는 값이 아니라 이름표입니다.
KEYS = {"code", "date", "i"}
# 그날 온 종목을 가로로 견주어 만든 값입니다. 한 종목만 떼어 내면 만들 수가
# 없으므로 1·2번 검사에서 빼고, 대신 check_cross_section이 따로 맡습니다.
# 여기에 이름을 올리면 1·2번을 면제받는 것이므로, verify가 이 이름들이
# 정말 4번 검사를 지났는지 되짚습니다.
CROSS = {"시장 이격", "상대 이격"}
# 공시에서 온 값입니다. 가로줄과 같은 까닭으로 1·2번이 닿지 않습니다(한 종목의
# 일봉만으로는 다시 만들 수 없습니다). check_filings가 따로 맡고, verify가
# 정말 그 검사를 지났는지 되짚습니다.
FILED = {events.MARK, events.AGE}


class LookaheadError(AssertionError):
    """미래를 본 값이 있습니다. 결과를 믿을 수 없으니 멈춥니다."""


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
        _compare(row, found, code, day, "뒷날 값을 바꾼", skip=CROSS | FILED)
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
        _compare(row, found, code, day, "뒷날을 잘라 낸", skip=CROSS | FILED)
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


def verify(prices, rows, samples=40, loud=True):
    """네 겹을 모두 지나야 참입니다. 하나라도 어긋나면 멈춥니다."""
    one = check_corruption(prices, rows, samples=samples)
    two = check_truncation(prices, rows, samples=samples)
    three = check_dates(rows)
    four = check_filings(rows)
    five = check_cross_section(rows)
    # 1·2번을 면제받은 이름이 제 검사도 지나지 않았다면 아무도 보지 않은 것입니다.
    present = {name for row in rows for name in CROSS if name in row}
    missed = sorted(name for name in present if not five.get(name))
    if {name for row in rows for name in FILED if name in row} and not four:
        missed.append("공시")
    if missed:
        raise LookaheadError(
            "면제받은 값이 어느 검사도 지나지 않았습니다 → " + " / ".join(missed))
    if loud:
        print(f"미래참조 검사 통과 · 더럽히기 {one}건 · 잘라내기 {two}건 · "
              f"날짜 확인 {three}건 · 공시 {four}건 · 가로줄 {sum(five.values())}건")
    return {"corruption": one, "truncation": two, "dates": three,
            "filings": four, "cross": sum(five.values())}


def build_verified(prices=None, samples=25, **kwargs):
    """특징을 만들고, 검사를 지난 것만 돌려줍니다.

    만들기와 검사를 따로 부르게 두면 언젠가 검사를 빼먹습니다. 한 문으로
    묶어 두면 빼먹을 수가 없습니다.
    """
    prices = prices if prices is not None else study.load_prices()
    rows = lab.build(prices, **kwargs)
    verify(prices, rows, samples=samples)
    return prices, rows
