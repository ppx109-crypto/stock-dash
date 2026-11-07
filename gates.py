"""공통 문(BOOST-0001-D 사전등록 판 3 §0 · §1 · §6 · 1단계) — 판단마다 '새 위험 증가'를 열고 닫음.

- 판단 id 4개: engine(빈칸 엔진 · 15:10) · basket(사건 바구니 · 엔진 실행 안) · overlay(덧붙임 · 엔진 뒤) · daily(1일봉 · 15:20).
- 닫힘이면 그 판단은 새 종목 매수 · 수량 늘리기 · 현금 → 위험자산만 막고, 매도 · 줄이기 · 손절 · 기간 청산 · 흔들림 상한 덜어내기 ·
  15:10 예방 자리 내주기는 그대로(§0.1). 어떻게 막는지는 봇마다(엔진 drop_buys · 바구니 돈 0 · 덧붙임 buy_ok · 1일봉 cands = []).
- 같은 날 엔진 실행(15:10)과 1일봉 실행(15:20)은 다른 프로세스라 그날 상태를 gates/<날>.json에 저장하고 이어 읽음.
  실행마다 자기 판단은 새로 열고(다시 돌면 새로 셈) 다른 실행이 적은 판단은 그대로 둠(1일봉 실행은 자기 daily 문 · sync_ok를 더함).
- 파일 읽기 · 쓰기가 실패해도 매매는 멈추지 않음(문 상태는 메모리에 그대로 · 한 줄만 찍음). 모르는 판단은 닫힘으로 봄(fail-closed).
- 판단 기록(audit_log 곁 칸 gates)에는 snapshot(판단 id): 판단 id · 열림 · 까닭 · 달력 sha256 · D · P · 세션 · sync_ok · D1 검증 칸.
- 저장소 맞추기(git pull)를 막지 않게 엔진 실행은 저장소 맞추기 뒤에만 파일을 씀(부르는 쪽 차례).
- 2a단계(원천별 신선도 · 그 판단만 닫음): D2 엔진 ETF 종가 마지막 날 = 달력 P(check_etf · engine) ·
  D4 (가) 수급 풀 건강도 90%(check_flow_pool · daily) · (나) 주문 안전 거르기(keep_flow_exact · 1일봉 후보 단계 · 빠진 기회 기록).
  점검 칸은 판단별 checks(snapshot · gates/<날>.json)에 남김.
"""
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
FOLDER = Path("gates")
DECISIONS = ("engine", "basket", "overlay", "daily")
RUN_DECISIONS = {"engine": ("engine", "basket", "overlay"), "daily": ("daily",)}     # 실행(프로세스)마다 그 실행의 활성 판단
RUN_OF = {d: run for run, ds in RUN_DECISIONS.items() for d in ds}
D1_DECISIONS = ("engine", "basket", "overlay")          # D1(15:05 다시 셈) 실패 때 막는 판단(셋 다 같은 비켜 두기 값을 씀 · §1.1)
LABEL = {"engine": "빈칸 엔진", "basket": "사건 바구니", "overlay": "덧붙임", "daily": "1일봉"}
D1_KEYS = ("ok", "why", "rc", "id", "at", "expected_p", "source_p", "pool_digest", "quotes_expected", "quotes_got",
           "started", "ended", "deadline", "reserve", "basis")
FLOW_KEYS = ("외국인", "투신", "개인")    # D4: final_group.flow_before가 더하는 칸(외국인 · 기관(투신) · 개인)
FLOW_DAYS = 5                            # D4: 수급 거래일 수(final_group.FLOW_DAYS와 같음)
FLOW_POOL_MIN = (9, 10)                  # D4 (가) 문턱 90% — 정수 비로 견줌(맞는 수 × 10 ≥ 풀 수 × 9 · 소수 반올림 없음)


def _now():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


def _head():
    """그때 저장소 HEAD(못 읽으면 None · 매매와 무관)."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        head = out.stdout.strip()
        return head if out.returncode == 0 and head else None
    except Exception:
        return None


def _copy(x):
    try:
        return json.loads(json.dumps(x, ensure_ascii=False, default=str))
    except Exception:
        return None


class Gates:
    """그날 문 상태. 판단 id마다 {"open": 참/거짓, "reasons": [까닭]}."""

    def __init__(self, day, run, folder=None):
        if run not in RUN_DECISIONS:
            raise ValueError(f"모르는 실행: {run}")
        self.day, self.run = str(day), run
        self.folder = Path(folder) if folder is not None else FOLDER
        self.active = RUN_DECISIONS[run]
        old = self._load()
        dec = old.get("decisions") if isinstance(old.get("decisions"), dict) else {}
        runs = old.get("runs") if isinstance(old.get("runs"), dict) else {}
        chk = old.get("checks") if isinstance(old.get("checks"), dict) else {}
        self.body = {"day": self.day,
                     "decisions": {d: self._clean(dec.get(d)) for d in DECISIONS},
                     "runs": {r: v for r, v in runs.items() if r in RUN_DECISIONS and isinstance(v, dict)},
                     "d1": old.get("d1") if isinstance(old.get("d1"), dict) else None,
                     "checks": {d: chk[d] for d in DECISIONS if isinstance(chk.get(d), dict)}}
        for d in self.active:                              # 이 실행의 판단은 새로 엶(까닭 · 점검 칸은 이 실행이 다시 셈)
            self.body["decisions"][d] = {"open": True, "reasons": []}
            self.body["checks"][d] = {}
        self.calendar_folder = None                        # 판 고정 달력 폴더(begin이 넣음 · D4 최근 5거래일)
        self._flow_days = None                             # D4: 달력 최근 5거래일(P로 끝남 · check_flow_pool이 정함)
        self.body["runs"][run] = {"started": _now(), "sync_ok": None, "head": None, "calendar": None, "live_p": None,
                                  "cross_ok": None, "smoke": None}
        if run == "engine":
            self.body["d1"] = None

    # ───── 파일 ─────
    def path(self):
        return self.folder / f"{self.day}.json"

    def _load(self):
        try:
            body = json.loads(self.path().read_text(encoding="utf-8"))
            return body if isinstance(body, dict) and str(body.get("day")) == self.day else {}
        except Exception:
            return {}

    @staticmethod
    def _clean(x):
        """파일에서 읽은 판단 칸 → 꼴이 이상하면 닫힘(모르면 막음)."""
        if isinstance(x, dict) and isinstance(x.get("open"), bool) and isinstance(x.get("reasons"), list):
            return {"open": x["open"], "reasons": [str(r) for r in x["reasons"]]}
        return {"open": False, "reasons": ["문 기록이 없음"]}

    def save(self):
        """gates/<날>.json에 원자적으로 씀. 실패해도 예외 없음(매매는 그대로) → 쓴 경로 또는 None."""
        p = self.path()
        tmp = p.with_name(f"{p.name}.{os.getpid()}.tmp")
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            self.body["saved"] = _now()
            tmp.write_text(json.dumps(self.body, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
            os.replace(tmp, p)
            return p
        except Exception as e:
            print("문 기록 저장 실패(매매는 그대로) ·", type(e).__name__)
            try:
                tmp.unlink()
            except Exception:
                pass
            return None

    # ───── 열고 닫기 ─────
    def close(self, decision_ids, reason):
        """판단들(id 하나 또는 여럿)을 닫고 까닭을 남김(같은 까닭은 한 번만)."""
        ids = (decision_ids,) if isinstance(decision_ids, str) else tuple(decision_ids)
        bad = [d for d in ids if d not in DECISIONS]
        if bad:
            raise ValueError(f"모르는 판단 id: {bad}")
        for d in ids:
            cur = self.body["decisions"].setdefault(d, {"open": True, "reasons": []})
            cur["open"] = False
            if str(reason) not in cur["reasons"]:
                cur["reasons"].append(str(reason))

    def allows_new_risk(self, decision_id):
        """그 판단이 새 위험을 늘려도 되는가(모르는 id · 꼴이 이상하면 거짓)."""
        cur = self.body["decisions"].get(decision_id)
        return isinstance(cur, dict) and cur.get("open") is True

    def reasons(self, decision_ids=None):
        out = []
        for d in decision_ids or self.active:
            for r in (self.body["decisions"].get(d) or {}).get("reasons") or []:
                if r not in out:
                    out.append(r)
        return out

    # ───── 까닭 재료 ─────
    def _run(self):
        return self.body["runs"][self.run]

    def set_sync(self, ok):
        """D6: 저장소 맞추기 결과 · 그때 HEAD. 실패면 이 실행의 활성 판단 모두 닫음."""
        self._run()["sync_ok"] = bool(ok)
        self._run()["head"] = _head()
        if not ok:
            self.close(self.active, "저장소를 최신으로 맞추지 못함(sync_repo 실패 · 낡은 장부로 판단할 수 있음)")

    def set_calendar(self, info, live_p=None):
        """D5: 판 고정 달력 정보와 2차 대조(실시간 앞 거래일). 못 정함 · 휴장 · 불일치면 이 실행의 활성 판단 모두 닫음."""
        import trade_calendar
        r = self._run()
        r["calendar"] = {k: info.get(k) for k in ("D", "trading", "open", "close", "P", "sha256", "version",
                                                    "p_sha256", "p_version")} if info else None
        r["live_p"] = live_p
        if not info:
            self.close(self.active, "판 고정 달력으로 오늘 · 앞 거래일을 못 정함(판 없음 · 지문 불일치 · 판에 없는 날)")
            r["cross_ok"] = False
            return
        if not info.get("trading"):
            self.close(self.active, "판 고정 달력에서 오늘은 휴장")
        ok, why = trade_calendar.cross_check(info, live_p)
        r["cross_ok"] = ok
        if not ok:
            self.close(self.active, why)

    def set_smoke(self, ok, why, body=None):
        """§5: 시작 전 점검 파일(gate-smoke/<날>.json). 없거나 ok가 아니면 이 실행의 활성 판단 모두 닫음."""
        b = body if isinstance(body, dict) else {}
        self._run()["smoke"] = {"ok": bool(ok), "why": why, "version": b.get("version"), "sha256": b.get("sha256"),
                                "run_id": b.get("run_id")}
        if not ok:
            self.close(self.active, why or "시작 전 점검 실패")

    def bind_d1(self, d1):
        """D1(15:05 다시 셈) 검증 칸을 엔진 · 바구니 · 덧붙임이 함께 씀(예외 없음). 실패면 셋을 닫음 ·
        달력 P(이 실행의 판)가 다시 셈의 expected_p와 다르면 그것도 실패로 봄."""
        try:
            d1 = d1 if isinstance(d1, dict) else {"ok": False, "why": "다시 셈 결과 없음"}
            self.body["d1"] = {k: _copy(d1.get(k)) for k in D1_KEYS}
            self.body["d1"]["ok"] = bool(d1.get("ok"))
            if not d1.get("ok"):
                self.close(D1_DECISIONS, "15:05 1일봉 몫 다시 셈 실패 · " + str(d1.get("why") or "까닭 모름"))
                return
            p = self.calendar_p()
            if not p or p != d1.get("expected_p"):
                self.fail_d1(f"달력 앞 거래일 {p}이 다시 셈의 앞 거래일 {d1.get('expected_p')}과 다름")
        except Exception as e:
            self.fail_d1(f"결속 오류 · {type(e).__name__}")

    def fail_d1(self, why):
        """D1을 실패로 고쳐 적고 엔진 · 바구니 · 덧붙임을 닫음."""
        if not isinstance(self.body.get("d1"), dict):
            self.body["d1"] = {k: None for k in D1_KEYS}
        self.body["d1"]["ok"] = False
        self.body["d1"]["why"] = str(why)
        self.close(D1_DECISIONS, "15:05 1일봉 몫 다시 셈 실패 · " + str(why))

    def d1_ok(self):
        return isinstance(self.body.get("d1"), dict) and self.body["d1"].get("ok") is True

    def calendar_p(self):
        """이 실행이 읽은 판 고정 달력의 앞 거래일(P) · 못 정했으면 None."""
        return ((self.body["runs"].get(self.run) or {}).get("calendar") or {}).get("P")

    def set_reserve(self, reserve, basis=None):
        """비켜 두기 금액(원)과 그 근거(검증 통과 판정 가운데 가장 늦은 것)를 D1 칸에 하나로 결속(세 판단이 같은 값을 봄)."""
        if not isinstance(self.body.get("d1"), dict):
            self.body["d1"] = {k: None for k in D1_KEYS}
        try:
            self.body["d1"]["reserve"] = 0.0 if reserve is None else float(reserve)
        except (TypeError, ValueError):
            self.body["d1"]["reserve"] = None
        self.body["d1"]["basis"] = _copy(basis)

    # ───── D2 · D4: 원천별 신선도(그 판단만 닫음 · 2a단계) ─────
    def _check(self, decision_id):
        return self.body.setdefault("checks", {}).setdefault(decision_id, {})

    def check_etf(self, last_by_code):
        """D2: 엔진 ETF가 판단에 쓴 종가의 마지막 날(D 앞)이 달력 P와 같은지 → 하나라도 아니면 **engine만** 닫음(까닭에 코드 · 마지막 날).
        달력 P를 못 정했으면 이미 D5 길로 닫혀 있음(그래도 엔진이 열려 있으면 닫음 · fail-closed). 예외 없음."""
        try:
            p = self.calendar_p()
            last = {str(c): (str(d) if d else None) for c, d in sorted(dict(last_by_code).items())}
            self._check("engine")["etf_last"] = {"P": p, "last": last}
            if not p:
                if self.allows_new_risk("engine"):
                    self.close("engine", "달력 앞 거래일을 몰라 엔진 ETF 종가 마지막 날을 못 견줌")
                return
            bad = [f"{c} {d if d else '없음'}" for c, d in last.items() if d != p]
            if bad or not last:
                self.close("engine", f"엔진 ETF 종가 마지막 날이 달력 앞 거래일 {p}과 다름 · " + (" · ".join(bad) if bad else "ETF 목록 없음"))
        except Exception as e:
            self.close("engine", f"엔진 ETF 종가 날짜 셈 오류 · {type(e).__name__}")

    def check_flow_pool(self, pool, day, rows_of):
        """D4 (가) 수급 풀 건강도: 결정과 무관한 고정 풀(전날 시총 150위 + 1일봉 보유 종목)의 investor-data에서 판단 날 앞 마지막 날 =
        달력 P인 비율이 90% 이상이 아니면 daily 닫음. 풀 목록 · sha256 · 비율 · 낡은 종목은 점검 칸(판단 기록 곁 칸)에.
        90% 통과는 '자료 완전'이 아님 — 매수 후보는 keep_flow_exact가 종목마다 다시 봄. 그 거르기에 쓸 달력 최근 5거래일(P로 끝남)을
        못 정해도 daily 닫음. rows_of(code) = 그 종목 수급 줄(final_group.flow_rows 꼴 · 오래된 날 먼저). 예외 없음(셈이 말썽이면 닫음)."""
        self._flow_days = None
        try:
            codes = sorted({str(c) for c in pool})
            p = self.calendar_p()
            days = None
            if p:
                import trade_calendar
                days = trade_calendar.last_days(day, FLOW_DAYS, folder=self.calendar_folder)
                if not days or days[-1] != p:
                    days = None
            stale = []
            for c in codes:
                last = flow_last(rows_of(c), day)
                if not p or last != p:                     # P를 모르면 맞는 종목 0으로 셈
                    stale.append([c, last])
            n, exact = len(codes), len(codes) - len(stale)
            self._check("daily")["flow_pool"] = {"P": p, "days": days, "n": n, "exact": exact,
                                                 "ratio": round(exact / n, 4) if n else None, "min": 0.9,
                                                 "sha256": pool_digest(codes), "pool": codes, "stale": stale}
            if not p:
                if self.allows_new_risk("daily"):
                    self.close("daily", "달력 앞 거래일을 몰라 수급 신선도를 못 셈")
                return
            if not (n > 0 and exact * FLOW_POOL_MIN[1] >= n * FLOW_POOL_MIN[0]):
                self.close("daily", f"수급 풀 건강도 미달 · investor-data 마지막 날이 앞 거래일 {p}인 종목 {exact}/{n}"
                                    f"({exact / n * 100 if n else 0:.1f}%) < 90%")
            if days is None:
                self.close("daily", "판 고정 달력으로 최근 5거래일을 못 정함(수급 주문 안전 거르기를 못 함)")
            self._flow_days = days
        except Exception as e:
            self._flow_days = None
            self.close("daily", f"수급 풀 건강도 셈 오류 · {type(e).__name__}")

    def keep_flow_exact(self, cands, day, rows_of):
        """D4 (나) 주문 안전: 1일봉 decide에 넘길 후보(기울기 정렬 · [:free] 자르기 **앞**)에서 수급 줄이 정확히 '달력 최근 5거래일
        (P로 끝남)'이고 외국인 · 투신 · 개인 칸이 모두 있는 종목만 남김(차례 · 후보 dict 그대로 → 모두 맞으면 지금과 같은 후보).
        10일 낡음 허용 길(final_group.flow_before)로만 통과한 후보는 여기서 빠지고 '빠진 기회'로 점검 칸에 남음.
        check_flow_pool이 먼저 돌아야 함(최근 5거래일을 못 정했으면 모두 뺌). → (남은 후보, 빠진 목록). 예외 없음."""
        days = self._flow_days
        keep, missed = [], []
        try:
            for c in cands:
                ok, why = flow_exact(rows_of(c["code"]), day, days) if days else (False, "달력으로 최근 5거래일을 못 정함")
                if ok:
                    keep.append(c)
                else:
                    missed.append({"code": c.get("code"), "name": c.get("name"), "why": why})
        except Exception as e:
            self.close("daily", f"수급 주문 안전 거르기 오류 · {type(e).__name__}")
            keep, missed = [], [{"code": None, "name": None, "why": f"거르기 오류 · {type(e).__name__}"}]
        self._check("daily")["flow_missed"] = _copy(missed)
        return keep, missed

    # ───── 기록 · 알림 ─────
    def snapshot(self, decision_id):
        """판단 기록용(예외 없음): 판단 id · 열림 · 까닭 · 달력 sha256 · D · P · 세션 · sync_ok · D1 검증 칸 · 점검 칸(D2 · D4)."""
        try:
            r = self.body["runs"].get(RUN_OF.get(decision_id, "")) or {}
            cal = r.get("calendar") or {}
            cur = self.body["decisions"].get(decision_id) or {}
            return {"decision": decision_id, "open": self.allows_new_risk(decision_id), "reasons": list(cur.get("reasons") or []),
                    "run": RUN_OF.get(decision_id), "D": cal.get("D") or self.day, "P": cal.get("P"),
                    "session": {"open": cal.get("open"), "close": cal.get("close")} if cal else None,
                    "calendar_sha256": cal.get("sha256"), "calendar_version": cal.get("version"),
                    "p_calendar_sha256": cal.get("p_sha256"), "live_p": r.get("live_p"), "cross_ok": r.get("cross_ok"),
                    "sync_ok": r.get("sync_ok"), "head": r.get("head"), "smoke": _copy(r.get("smoke")),
                    "d1": _copy(self.body.get("d1")), "checks": _copy((self.body.get("checks") or {}).get(decision_id) or {})}
        except Exception as e:
            return {"decision": decision_id, "open": False, "reasons": [f"문 기록 만들기 실패 · {type(e).__name__}"]}

    def warn_line(self):
        """이 실행에서 닫힌 판단이 있으면 디스코드 ⚠️ 한 줄(없으면 None)."""
        shut = [d for d in self.active if not self.allows_new_risk(d)]
        if not shut:
            return None
        return (f"⚠️ 새 매수 막음({' · '.join(LABEL[d] for d in shut)}) · 까닭: {' / '.join(self.reasons(shut))}"
                " · 팔기 · 줄이기는 그대로")


def begin(day, run, sync_ok, live_p=None, folder=None, calendar_folder=None, smoke_folder=None):
    """그 실행의 문을 새로 열고 공통 까닭을 셈: 저장소 맞추기(D6) · 판 고정 달력과 2차 대조(D5) · 시작 전 점검(§5).
    예외 없음 — 셈 자체가 말썽이면 이 실행의 활성 판단을 닫음(fail-closed)."""
    g = Gates(day, run, folder)
    g.calendar_folder = calendar_folder
    steps = (("저장소 맞추기", lambda: g.set_sync(sync_ok)),
             ("달력", lambda: _calendar(g, day, live_p, calendar_folder)),
             ("시작 전 점검", lambda: _smoke(g, day, smoke_folder)))
    for name, fn in steps:
        try:
            fn()
        except Exception as e:
            g.close(g.active, f"문 셈 오류({name} · {type(e).__name__})")
    return g


def _calendar(g, day, live_p, folder):
    import trade_calendar
    g.set_calendar(trade_calendar.day_info(day, folder=folder), live_p)


def _smoke(g, day, folder):
    import gate_smoke
    ok, why, body = gate_smoke.status(day, folder=folder)
    g.set_smoke(ok, why, body)


# ───────────────────────── D4 셈(증권사 없이 · 시험할 수 있게) ─────────────────────────

def pool_digest(codes):
    """풀 목록 지문(코드 목록을 빈칸 없는 JSON으로 → sha256 · hourly_a.pool_digest와 같은 꼴)."""
    return hashlib.sha256(json.dumps(list(codes), separators=(",", ":")).encode("utf-8")).hexdigest()


def _before(rows, day):
    """판단 날(day) 앞 줄만(final_group.flow_before와 같은 거르기 · 오래된 날 먼저)."""
    return [r for r in rows or [] if isinstance(r, dict) and str(r.get("date", "")) < str(day)]


def flow_last(rows, day):
    """수급 줄에서 판단 날 앞 마지막 날(없으면 None)."""
    got = _before(rows, day)
    return str(got[-1].get("date")) if got else None


def flow_exact(rows, day, want):
    """D4 (나): 판단 날 앞 마지막 len(want)줄의 날짜가 정확히 want(달력 최근 거래일 · P로 끝남)이고 외국인 · 투신 · 개인 칸이 모두 있으면
    (참, "") · 아니면 (거짓, 까닭). final_group.flow_before가 실제로 더하는 줄(날짜 < day의 끝 5줄)과 같은 줄을 보므로, 통과한 종목의
    수급 합은 10일 낡음 허용 없이 센 값과 같음."""
    want = [str(d) for d in want]
    got = _before(rows, day)[-len(want):]
    dates = [str(r.get("date")) for r in got]
    if not dates or dates[-1] != want[-1]:
        return False, f"수급 마지막 날 {dates[-1] if dates else '없음'} ≠ 앞 거래일 {want[-1]}"
    if dates != want:
        miss = [d for d in want if d not in dates]
        return False, f"최근 {len(want)}거래일 수급 줄 빠짐 · " + (" · ".join(miss) if miss else "날짜가 달력과 어긋남")
    empty = [f"{r.get('date')} {k}" for r in got for k in FLOW_KEYS if r.get(k) is None]
    if empty:
        return False, f"최근 {len(want)}거래일 수급 칸 빔 · " + " · ".join(empty[:5])
    return True, ""
