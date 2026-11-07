"""공통 문(BOOST-0001-D 사전등록 판 3 §0 · §1 · §6 · 1단계) — 판단마다 '새 위험 증가'를 열고 닫음.

- 판단 id 4개: engine(빈칸 엔진 · 15:10) · basket(사건 바구니 · 엔진 실행 안) · overlay(덧붙임 · 엔진 뒤) · daily(1일봉 · 15:20).
- 닫힘이면 그 판단은 새 종목 매수 · 수량 늘리기 · 현금 → 위험자산만 막고, 매도 · 줄이기 · 손절 · 기간 청산 · 흔들림 상한 덜어내기 ·
  15:10 예방 자리 내주기는 그대로(§0.1). 어떻게 막는지는 봇마다(엔진 drop_buys · 바구니 돈 0 · 덧붙임 buy_ok · 1일봉 cands = []).
- 같은 날 엔진 실행(15:10)과 1일봉 실행(15:20)은 다른 프로세스라 그날 상태를 gates/<날>.json에 저장하고 이어 읽음.
  실행마다 자기 판단은 새로 열고(다시 돌면 새로 셈) 다른 실행이 적은 판단은 그대로 둠(1일봉 실행은 자기 daily 문 · sync_ok를 더함).
- 파일 읽기 · 쓰기가 실패해도 매매는 멈추지 않음(문 상태는 메모리에 그대로 · 한 줄만 찍음). 모르는 판단은 닫힘으로 봄(fail-closed).
- 판단 기록(audit_log 곁 칸 gates)에는 snapshot(판단 id): 판단 id · 열림 · 까닭 · 달력 sha256 · D · P · 세션 · sync_ok · D1 검증 칸.
- 저장소 맞추기(git pull)를 막지 않게 엔진 실행은 저장소 맞추기 뒤에만 파일을 씀(부르는 쪽 차례).
"""
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
        self.body = {"day": self.day,
                     "decisions": {d: self._clean(dec.get(d)) for d in DECISIONS},
                     "runs": {r: v for r, v in runs.items() if r in RUN_DECISIONS and isinstance(v, dict)},
                     "d1": old.get("d1") if isinstance(old.get("d1"), dict) else None}
        for d in self.active:                              # 이 실행의 판단은 새로 엶(까닭은 이 실행이 다시 셈)
            self.body["decisions"][d] = {"open": True, "reasons": []}
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

    # ───── 기록 · 알림 ─────
    def snapshot(self, decision_id):
        """판단 기록용(예외 없음): 판단 id · 열림 · 까닭 · 달력 sha256 · D · P · 세션 · sync_ok · D1 검증 칸."""
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
                    "d1": _copy(self.body.get("d1"))}
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
