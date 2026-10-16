"""MPOS-0021 부품(MPOS-0020 parts20.py + 진입 기록 Entries · 보유 칸 관찰 HeldAudit · Audit의 프레임 거리 depth):
MPOS-0020 부품: 정배열 갈래에 더하는 청산 조건(extra) · 날짜 접근 감사(Audit · GPT #446 §2).

Audit: 엔진(lab.run)이 청산 판단(exit_at)을 부를 때마다
- 판단 날 = 엔진 루프의 지역 변수 day(부른 쪽 프레임에서 읽기만 함 · 엔진 코드 안 고침)
- 오늘 칸 = start + step, 그 칸의 날 = lane["날"][start + step]
- 판단이 실제로 읽은 가장 먼 칸 = 종목 길의 줄(closes · 날 · 중기선 · 변동성)을 읽기 기록 덮개(Rec)로 감싸 잼
을 견줘 셈. '미래 바' = 오늘 칸의 날 > 판단 날(정지 · 결측 날에 다음 바 종가를 앞당겨 읽음 · GPT 재현 경로).
'미래 칸' = 읽은 가장 먼 칸 > 오늘 칸(LEAK처럼 다음 칸을 읽음).
'줄 끝 사라짐'(보고만) = 마지막 판단이 그 종목 줄의 마지막 칸에서 '안 팜'이었고 그 종목 줄이 전체 자료 끝보다 일찍 끝남
→ 엔진(settle_end=False)이 다음 날 그 매매를 기록 없이 지움(상속 한계 · 폐지 · 긴 정지).
감사 범위: 종목 길 줄의 읽기만. nrl.broken이 읽는 nrl.shape(정배열 모양 · 고정 캐시 · 오늘 칸만 읽음)와 후보 줄(row)은 덮지 못함."""
import sys


def extra(mode, n, lane, start, price, step, peak):
    spot = start + step
    c = lane["closes"]
    if mode == "NP":       # 무익 N일: 산 뒤 N번째 종목 바 이상 · 그때까지 최고 종가 ≤ 산 값
        return step >= n and peak <= price
    if mode == "CH":       # N일 채널 저점: 오늘 종가 < 오늘 앞 N개 종목 바 종가의 최저(오늘 제외 · 같으면 안 팜)
        return spot - n >= 0 and step >= 1 and c[spot] < min(c[spot - n:spot])
    if mode == "LEAK":     # 검사 도구 시험: 내일 종가 < 오늘 종가
        return spot + 1 < len(c) and c[spot + 1] < c[spot]
    if mode == "LEAK2":    # 검사 도구 시험: 모레 / 내일 비율 < 1(미래 두 값의 비율만 봄 · GPT #446 §2 지적 경로)
        return spot + 2 < len(c) and c[spot + 2] < c[spot + 1]
    return False


class Rec:
    """줄 읽기 기록 덮개: 읽은 가장 큰 칸 번호를 적음(값은 그대로 돌려줌)."""
    __slots__ = ("s", "hi")

    def __init__(self, s):
        self.s, self.hi = s, -1

    def __len__(self):
        return len(self.s)

    def _see(self, top):
        if top > self.hi:
            self.hi = top

    def __getitem__(self, k):
        if isinstance(k, slice):
            a, b, _ = k.indices(len(self.s))
            if b > a:
                self._see(b - 1)
        else:
            self._see(k if k >= 0 else len(self.s) + k)
        return self.s[k]

    def __iter__(self):
        self._see(len(self.s) - 1)
        return iter(self.s)


LISTS = ("closes", "날", "중기선", "변동성")


class Audit:
    def __init__(self, fn, data_end=None):
        self.fn, self.data_end = fn, data_end
        self.calls = self.ahead = self.far = self.no_day = 0
        self.examples = []
        self.last = {}
        self.depth = 1          # 엔진 프레임까지 거리(덮개를 한 겹 더 씌우면 2)

    def __call__(self, lane, start, price, step, peak, row=None):
        day = sys._getframe(self.depth).f_locals.get("day")
        spot = start + step
        recs = {k: Rec(lane[k]) for k in LISTS if k in lane}
        one = dict(lane)
        one.update(recs)
        got = self.fn(one, start, price, step, peak, row)
        self.calls += 1
        hi = max([r.hi for r in recs.values()] + [spot])
        if day is None:
            self.no_day += 1
        else:
            bar = lane["날"][spot]
            if bar > day:
                self.ahead += 1
                if len(self.examples) < 5:
                    self.examples.append({"종목": lane.get("code"), "판단 날": day, "읽은 오늘 바 날": bar})
        if hi > spot:
            self.far += 1
        self.last[(lane.get("code"), start)] = (spot, len(lane["closes"]), lane["날"][-1], got is True)
        return got

    def receipt(self):
        end = self.data_end
        gone = sum(1 for spot, ln, last_day, sold in self.last.values() if not sold and spot == ln - 1 and end and last_day < end)
        return {"판단 수": self.calls, "미래 바(오늘 바 날 > 판단 날)": self.ahead, "미래 칸(읽은 칸 > 오늘 칸)": self.far,
                "판단 날 못 읽음": self.no_day, "미래 바 예": self.examples, "줄 끝 사라짐(보고 · 상속 한계)": gone}


class Entries:
    """크기 함수 덮개(MPOS-0021 · GPT #450 2): 엔진(lab.py:1031)은 실제로 살 때만 크기를 물음.
    그때 (종목 · 산 날 · 요청 칸 · 배정 칸)을 기록. 배정 칸 = 엔진 지역 변수(top · used · freed · beyond)를 부른 쪽 프레임에서 읽어
    lab.py:1031과 같은 식 min(max(요청, 1), top − used, freed if beyond else top)으로 셈(stop_run을 안 쓸 때만 · 쓰면 멈춤).
    결정은 바꾸지 않음. 배정 칸은 다음 날 청산 판단에서 본 실제 보유 칸(Audit.held)과 대조함."""
    def __init__(self, fn):
        self.fn, self.rows = fn, []

    def __call__(self, r):
        k = self.fn(r)
        loc = sys._getframe(1).f_locals
        assert not loc.get("stop_run"), "stop_run을 쓰면 배정 식이 다름"
        top, used, freed, beyond = loc["top"], loc["used"], loc.get("freed", 0), loc.get("beyond", False)
        self.rows.append([r["code"], r["date"], k, min(max(int(k), 1), top - used, freed if beyond else top)])
        return k


class HeldAudit(Audit):
    """Audit + 청산 판단 때 부른 쪽 프레임의 spot['자리']를 (종목, 산 칸)마다 첫 판단에서 기록(실제 보유 칸 관찰)."""
    def __init__(self, fn, data_end=None):
        super().__init__(fn, data_end)
        self.held = {}
        self.depth = 2

    def __call__(self, lane, start, price, step, peak, row=None):
        spot = sys._getframe(1).f_locals.get("spot")
        key = (lane.get("code"), start)
        if spot is not None and key not in self.held:
            self.held[key] = spot.get("자리")
        return super().__call__(lane, start, price, step, peak, row)
