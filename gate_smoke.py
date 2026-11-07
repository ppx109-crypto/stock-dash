"""시작 전 점검(BOOST-0001-D 사전등록 판 3 §5 · 1단계는 코드만 · 작업 흐름에 넣는 것은 다음 단계).

주문 작업의 첫 15:10 주문 단계(python idle_live.py) 앞에서 돌릴 빠르고 결정적인 점검입니다. 증권사 · DART를 부르지 않습니다.
  ① 판 고정 달력: 그 해의 가장 큰 번호 판을 읽고 정규화 지문을 다시 셈(trade_calendar.load_year)
  ② 오늘 day_info: 오늘 · 앞 거래일(P) · 개장 · 마감을 정할 수 있는지
  ③ 문 출력 꼴: 문을 닫고 · 기록(snapshot) · 저장 · 다시 읽기가 정해진 꼴인지(임시 폴더에서)
  ④ 옛 출력 거부: D1 검증(paper_trade.d1_check)이 어제 날짜 · 14:30 전 · 시세 빠짐 · P 다름 본문을 거부하고 맞는 본문만 통과시키는지
  ⑤ 공시 manifest 결속(2b단계 · D3 · 2c단계 범위): 바구니 문 검사(event_manifest.morning_check)가 맞는 아침 최종 확인(주말 낀 범위 ·
     범위 안 주말 접수 사건 포함)만 통과시키고 19:20 정기만 · ok 거짓 · 판단 뒤 완료 · 질의 날 다름 · 질의 시작이 t0 하루 · 질의 지문 다름 ·
     트리 지문 다름 · 범위 안 사건이 manifest에서 빠짐을 거부하는지(합성 · 임시 폴더 · 실제 manifest가 있는지는 보지 않음)
  ⑥ 첫 실행 확인 문(2c단계 · GPT §4-4 · 판 2 §2-A): gates.armed_status가 ARMED.json 없음 · 달력 sha256 다름 · 확인 날이 뒤 ·
     세션 검토 영수증 없음 · 검토 시각이 판과 다름을 거부하고 맞는 것만 통과시키는지
     (합성 · 임시 폴더) · 오늘 판의 세션이 unknown이면 그것도 까닭으로 적음
결과: gate-smoke/<날>-<작업 번호>-<시도>.json(ok · 판 · 까닭 · 로컬은 <날>-local-0.json) — 2b단계부터 작업마다 다른 이름이라 같은 날
뒤 작업이 앞 작업 파일을 덮지 않고, 새 파일은 추적 밖이라 15:10 저장소 맞추기(git pull --rebase)를 막지 않음(로컬 커밋 필요 없음).
봇은 **자기 작업 · 시도의 파일만** 읽고, 없거나 · 오늘 것이 아니거나 · 본문의 작업 번호 · 시도가 다르거나 · ok가 아니면 그 실행의
활성 판단 모두 새 위험 증가를 막습니다(매매 전체를 멈추지는 않음 · 팔기 · 줄이기는 그대로).
끝 값은 언제나 0(점검이 실패해도 작업을 멈추지 않음 · 막기는 봇이 이 파일을 보고 함).
"""
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
FOLDER = Path("gate-smoke")
SNAP_KEYS = ("decision", "open", "reasons", "run", "D", "P", "session", "session_kind", "session_sha256", "calendar_sha256",
             "calendar_version", "p_calendar_sha256", "live_p", "cross_ok", "sync_ok", "head", "smoke", "armed", "d1", "checks")


def _gate_shape(day):
    """③ 문 출력 꼴(임시 폴더에서 · 실제 gates/는 건드리지 않음) → 까닭 목록(비면 통과)."""
    import gates
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        g = gates.Gates(day, "engine", folder=tmp)
        if not all(g.allows_new_risk(d) for d in gates.RUN_DECISIONS["engine"]):
            bad.append("새로 연 문이 열림이 아님")
        g.close(("basket",), "점검")
        if g.allows_new_risk("basket") or not g.allows_new_risk("engine") or g.allows_new_risk("없는 판단"):
            bad.append("닫기 · 열림 판정이 이상함")
        for d in gates.DECISIONS:
            snap = g.snapshot(d)
            if tuple(snap) != SNAP_KEYS or not isinstance(snap["open"], bool) or not isinstance(snap["reasons"], list) \
                    or not isinstance(snap["checks"], dict):
                bad.append(f"{d} 기록 꼴이 다름")
        if g.save() is None:
            bad.append("문 파일을 쓰지 못함")
        again = gates.Gates(day, "daily", folder=tmp)
        if again.allows_new_risk("basket") or "점검" not in again.reasons(("basket",)) or not again.allows_new_risk("daily"):
            bad.append("문 파일을 이어 읽지 못함")
    return bad


def _old_output_rejected(day, p):
    """④ D1 검증이 옛 출력 · 빠진 출력을 거부하는지(합성 본문) → 까닭 목록."""
    import hashlib
    import paper_trade
    pool = ["000001", "000002"]
    good = {"date": day, "at": f"{day[:4]}-{day[4:6]}-{day[6:]} 15:05", "picks_daily": [], "expected_p": p, "source_p": p,
            "pool": pool, "pool_digest": hashlib.sha256(json.dumps(pool, separators=(",", ":")).encode()).hexdigest(),
            "quotes_expected": 2, "quotes_got": 2}
    bad = []
    if not paper_trade.d1_check(good, day, p)[0]:
        bad.append("맞는 본문을 거부함")
    for name, body in (("어제 날짜", dict(good, date=p)), ("14:30 전", dict(good, at=good["at"][:11] + "14:29")),
                       ("시세 빠짐", dict(good, quotes_got=1)), ("P 다름", dict(good, source_p="19990101"))):
        if paper_trade.d1_check(body, day, p)[0]:
            bad.append(f"{name} 본문을 통과시킴")
    return bad


def _manifest_binding(day, p):
    """⑤ 공시 manifest 결속(합성 · 임시 폴더 · git 확인은 빼고 칸 · 지문 · 범위만) → 까닭 목록.
    합성 범위 = 'p 이틀 앞 ~ p'(주말을 낀 월요일 t0처럼) · 범위 첫날(주말) 접수 사건 1건 + t0 사건 1건."""
    from datetime import timedelta, timezone
    import event_manifest as M
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        data, folder = Path(tmp) / "event-data", Path(tmp) / "event-manifest"
        data.mkdir()
        t0 = datetime.strptime(p, "%Y%m%d")
        begin = (t0 - timedelta(days=2)).strftime("%Y%m%d")
        win = {"begin": begin, "end": p, "before": (t0 - timedelta(days=3)).strftime("%Y%m%d")}
        rows = [{"date": begin, "kind": "무상증자", "title": "점검(주말 접수)"}, {"date": p, "kind": "무상증자", "title": "점검"}]
        (data / "000001.json").write_text(json.dumps({"code": "000001", "rows": rows}, ensure_ascii=False), encoding="utf-8")
        events = M.normalize([("000001", r["date"], r["kind"], r["title"]) for r in rows])
        decided = datetime(int(day[:4]), int(day[4:6]), int(day[6:]), 15, 10, tzinfo=KST)
        good = {k: None for k in M.FIELDS}
        good.update(kind=M.KIND, version=M.VERSION, mode="final", t0=p, D=day, query_begin=begin, query_end=p, ok=True, persisted=True,
                    normalized_query_digest=M.query_digest(begin, p), normalized_event_digest=M.digest(events),
                    stored_event_digest=M.digest(events), event_data_tree_digest=M.tree_digest(data), GITHUB_RUN_ID="1",
                    GITHUB_RUN_ATTEMPT="1", completed_at_utc=(decided - timedelta(hours=6)).astimezone(timezone.utc).strftime(M.UTC_FORM))

        def opens(body):
            for f in folder.glob("*.json"):
                f.unlink()
            M.write(body, folder)
            return M.morning_check(p, day, decided, folder=folder, data=data, git=False, window=win)[0]
        if not opens(good):
            bad.append("맞는 아침 확인 manifest를 거부함")
        late = (decided + timedelta(minutes=1)).astimezone(timezone.utc).strftime(M.UTC_FORM)
        short = M.digest(events[1:])
        for name, change in (("19:20 정기만", {"mode": "regular"}), ("ok 거짓", {"ok": False}), ("판단 뒤 완료", {"completed_at_utc": late}),
                             ("질의 날 다름", {"query_end": day}), ("질의 시작이 t0 하루", {"query_begin": p}),
                             ("질의 지문 다름", {"normalized_query_digest": M.query_digest(p, p)}),
                             ("트리 지문 다름", {"event_data_tree_digest": "0" * 64}),
                             ("범위 안 사건 빠짐", {"normalized_event_digest": short, "stored_event_digest": short})):
            body = dict(good)
            body.update(change)
            if opens(body):
                bad.append(f"{name} manifest를 통과시킴")
    return bad


def _armed_check(day):
    """⑥ 첫 실행 확인 문(합성 · 임시 폴더) → 까닭 목록."""
    import gates
    bad = []
    sha = "a" * 64
    reg = {"source_url": "https://regulation.krx.co.kr/hours", "notice_no": None, "effective_from": day, "raw_sha256": "c" * 64,
           "open": "0900", "close": "1530"}
    sessions = {"regular": reg, "special": []}
    review = {"reviewer": "점검", "reviewed_on": day, "special": [],
              "regular": {"source_url": reg["source_url"], "raw_sha256": reg["raw_sha256"], "read_open": "0900", "read_close": "1530",
                          "read_effective_from": day}}
    good = {"calendar_sha256": sha, "confirmed_on": day, "run_id": "1", "session_review": review}
    with tempfile.TemporaryDirectory() as tmp:
        if gates.armed_status(sha, day, folder=tmp, sessions=sessions)[0]:
            bad.append("ARMED.json이 없는데 통과시킴")
        f = Path(tmp) / gates.ARMED
        for name, body, want in (("맞는 확인", good, True),
                                 ("달력 sha256 다름", dict(good, calendar_sha256="b" * 64), False),
                                 ("확인 날이 뒤", dict(good, confirmed_on="29991231"), False),
                                 ("작업 번호 없음", {k: v for k, v in good.items() if k != "run_id"}, False),
                                 ("세션 검토 영수증 없음", {k: v for k, v in good.items() if k != "session_review"}, False),
                                 ("세션 검토 시각 다름", dict(good, session_review=dict(review, regular=dict(review["regular"],
                                                                                               read_close="1600"))), False)):
            f.write_text(json.dumps(body), encoding="utf-8")
            ok, why, _ = gates.armed_status(sha, day, folder=tmp, sessions=sessions)
            if ok != want:
                bad.append(f"첫 실행 확인 문이 '{name}'을 {'거부함' if want else '통과시킴'}")
            elif not ok and not why.startswith(gates.ARMED_WHY):
                bad.append("첫 실행 확인 문의 까닭 꼴이 다름")
    return bad


def check(day, calendar_folder=None):
    """점검 본문(쓰지 않음). 셈 중 예외도 실패로 적음."""
    import trade_calendar
    reasons, body = [], {"date": day, "ok": False, "version": None, "sha256": None, "P": None,
                         "at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
                         "run_id": os.getenv("GITHUB_RUN_ID"), "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT")}
    try:
        cal = trade_calendar.load_year(day[:4], folder=calendar_folder)
        if cal is None:
            reasons.append("올해 판 고정 달력을 못 읽음(판 없음 · 칸 빠짐 · 지문 불일치)")
        else:
            body.update(version=cal["version"], sha256=cal["sha256"])
        info = trade_calendar.day_info(day, folder=calendar_folder)
        if info is None:
            reasons.append("오늘 · 앞 거래일을 달력으로 못 정함")
        else:
            body["P"] = info["P"]
            body["trading"] = info["trading"]
            body["session"] = info.get("session")
            if not info["trading"]:
                reasons.append("달력에서 오늘은 휴장")
            elif info.get("session") == "unknown":
                reasons.append("달력에 오늘 세션 원천이 없음(session unknown)")
        reasons += _gate_shape(day)
        reasons += _old_output_rejected(day, (info or {}).get("P") or "20000101")
        reasons += _manifest_binding(day, (info or {}).get("P") or "20000110")
        reasons += _armed_check(day)
    except Exception as e:
        reasons.append(f"점검 중 오류 · {type(e).__name__}")
    body["reasons"] = reasons
    body["ok"] = not reasons
    return body


def path_for(day, folder=None):
    """이 작업 · 시도의 점검 파일 자리: gate-smoke/<날>-<작업 번호>-<시도>.json(로컬은 <날>-local-0.json)."""
    import event_manifest
    rid, att = event_manifest.run_tag()
    return (Path(folder) if folder is not None else FOLDER) / f"{day}-{rid}-{att}.json"


def write(body, folder=None):
    """gate-smoke/<날>-<작업 번호>-<시도>.json에 원자적으로 씀 → 경로 또는 None."""
    folder = Path(folder) if folder is not None else FOLDER
    p = path_for(body["date"], folder)
    tmp = p.with_name(f"{p.name}.{os.getpid()}.tmp")
    try:
        folder.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, p)
        return p
    except Exception as e:
        print("시작 전 점검 파일을 쓰지 못함 ·", type(e).__name__)
        try:
            tmp.unlink()
        except Exception:
            pass
        return None


def status(day, folder=None):
    """봇이 읽음(자기 작업 · 시도의 파일만) → (통과, 까닭, 본문). 없음 · 깨짐 · 다른 날 · ok 아님 ·
    (작업 번호 · 시도가 있으면) 본문의 작업 번호 · 시도가 다름 → 통과 아님."""
    try:
        body = json.loads(path_for(day, folder).read_text(encoding="utf-8"))
    except OSError:
        return False, "시작 전 점검 파일이 없음", None
    except ValueError:
        return False, "시작 전 점검 파일이 깨짐", None
    if not isinstance(body, dict) or str(body.get("date")) != str(day):
        return False, "시작 전 점검 파일이 오늘 것이 아님", body if isinstance(body, dict) else None
    run_id, attempt = os.getenv("GITHUB_RUN_ID"), os.getenv("GITHUB_RUN_ATTEMPT")
    if (run_id and str(body.get("run_id")) != run_id) or (attempt and str(body.get("run_attempt")) != attempt):
        return False, "시작 전 점검 파일이 이 작업의 것이 아님", body
    if body.get("ok") is not True:
        why = " · ".join(str(r) for r in body.get("reasons") or []) or "까닭 없음"
        return False, f"시작 전 점검 실패({why})", body
    return True, "", body


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    day = argv[0] if argv else datetime.now(KST).strftime("%Y%m%d")
    body = check(day)
    path = write(body)
    if body["ok"]:
        print(f"시작 전 점검 통과 · 달력 판 {body['version']} · 앞 거래일 {body['P']}")
    else:
        print("⚠️ 시작 전 점검 실패 → 오늘 봇의 새 매수는 막힘(팔기는 그대로) · " + " · ".join(body["reasons"]))
    if path is None:
        print("⚠️ 점검 파일이 없으니 봇은 새 매수를 막음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
