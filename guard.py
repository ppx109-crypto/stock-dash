"""미래를 본 값이 하나라도 있으면 멈춥니다.

과거 자료로 규칙을 시험할 때 가장 크고 가장 흔한 잘못은, 그날 알 수 없던
것을 그날의 판단에 쓰는 일입니다. 한 번 섞이면 어떤 규칙이든 좋아 보이고,
숫자만 봐서는 알아챌 수 없습니다. 실제로 이 저장소에서도 한 번 있었습니다.
오늘의 실적으로 몇 해 전의 날을 판정하고 있었습니다.

그래서 세 겹으로 막습니다.

1. **더럽히기** — 그날 뒤의 값을 엉뚱한 수로 바꿔 다시 계산합니다. 특징이
   조금이라도 달라지면 그 값은 뒷날을 본 것입니다. '안 쓴 척'이 아니라
   '조금 쓴 것'까지 잡힙니다.
2. **잘라내기** — 그날까지만 남기고 다시 계산합니다. 뒷날 자료가 아예 없어도
   같은 값이 나와야 합니다.
3. **날짜 확인** — 실적과 목표가는 발표일이 그날보다 뒤면 쓰지 않았는지
   하나씩 짚습니다.

세 겹 모두 통과해야 조사를 돌립니다. 하나라도 어긋나면 멈추고 어느 값이
어긋났는지 말합니다.
"""
from __future__ import annotations

import random

import lab
import study

# 앞날 수익률은 뒷날을 보라고 만든 값입니다. 검사에서 뺍니다.
LABELS = {"ahead"}
# 종목·날짜·자리는 값이 아니라 이름표입니다.
KEYS = {"code", "date", "i"}


class LookaheadError(AssertionError):
    """미래를 본 값이 있습니다. 결과를 믿을 수 없으니 멈춥니다."""


def _one(code, block):
    return {code: block}


def _pick(rows, code, day):
    return next((r for r in rows if r["code"] == code and r["date"] == day), None)


def _compare(clean, dirty, code, day, how):
    gaps = []
    for key, value in clean.items():
        if key in LABELS or key in KEYS:
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
        _compare(row, found, code, day, "뒷날 값을 바꾼")
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
        _compare(row, found, code, day, "뒷날을 잘라 낸")
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


def verify(prices, rows, samples=40, loud=True):
    """세 겹을 모두 지나야 참입니다. 하나라도 어긋나면 멈춥니다."""
    one = check_corruption(prices, rows, samples=samples)
    two = check_truncation(prices, rows, samples=samples)
    three = check_dates(rows)
    if loud:
        print(f"미래참조 검사 통과 · 더럽히기 {one}건 · 잘라내기 {two}건 · "
              f"날짜 확인 {three}건")
    return {"corruption": one, "truncation": two, "dates": three}


def build_verified(prices=None, samples=25, **kwargs):
    """특징을 만들고, 검사를 지난 것만 돌려줍니다.

    만들기와 검사를 따로 부르게 두면 언젠가 검사를 빼먹습니다. 한 문으로
    묶어 두면 빼먹을 수가 없습니다.
    """
    prices = prices if prices is not None else study.load_prices()
    rows = lab.build(prices, **kwargs)
    verify(prices, rows, samples=samples)
    return prices, rows
