"""시작 전 점검(BOOST-0001-D 사전등록 판 3 §5 · 1단계는 코드만 · 작업 흐름에 넣는 것은 다음 단계).

주문 작업의 첫 15:10 주문 단계(python idle_live.py) 앞에서 돌릴 빠르고 결정적인 점검입니다. 증권사 · DART를 부르지 않습니다.
  ① 판 고정 달력: 그 해의 가장 큰 번호 판을 읽고 정규화 지문을 다시 셈(trade_calendar.load_year)
  ② 오늘 day_info: 오늘 · 앞 거래일(P) · 개장 · 마감을 정할 수 있는지
  ③ 문 출력 꼴: 문을 닫고 · 기록(snapshot) · 저장 · 다시 읽기가 정해진 꼴인지(임시 폴더에서)
  ④ 옛 출력 거부: D1 검증(paper_trade.d1_check)이 어제 날짜 · 14:30 전 · 시세 빠짐 · P 다름 본문을 거부하고 맞는 본문만 통과시키는지
  ⑤ 공시 manifest 결속(2b단계 · D3): 바구니 문 검사(event_manifest.morning_check)가 맞는 아침 최종 확인만 통과시키고 19:20 정기만 ·
     ok 거짓 · 판단 뒤 완료 · 질의 날 다름 · 트리 지문 다름을 거부하는지(합성 · 임시 폴더 · 실제 manifest가 있는지는 보지 않음)
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
SNAP_KEYS = ("decision", "open", "reasons", "run", "D", "P", "session", "calendar_sha256", "calendar_version",
             "p_calendar_sha256", "live_p", "cross_ok", "sync_ok", "head", "smoke", "d1", "checks")


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
    """⑤ 공시 manifest 결속(합성 · 임시 폴더 · git 확인은 빼고 칸 · 지문만) → 까닭 목록."""
    from datetime import timedelta, timezone
    import event_manifest as M
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        data, folder = Path(tmp) / "event-data", Path(tmp) / "event-manifest"
        data.mkdir()
        (data / "000001.json").write_text(json.dumps({"code": "000001", "rows": [{"date": p, "kind": "무상증자", "title": "점검"}]},
                                                     ensure_ascii=False), encoding="utf-8")
        decided = datetime(int(day[:4]), int(day[4:6]), int(day[6:]), 15, 10, tzinfo=KST)
        good = {k: None for k in M.FIELDS}
        good.update(kind=M.KIND, version=M.VERSION, mode="final", t0=p, D=day, query_begin=p, query_end=p, ok=True, persisted=True,
                    event_data_tree_digest=M.tree_digest(data), GITHUB_RUN_ID="1", GITHUB_RUN_ATTEMPT="1",
                    completed_at_utc=(decided - timedelta(hours=6)).astimezone(timezone.utc).strftime(M.UTC_FORM))

        def opens(body):
            for f in folder.glob("*.json"):
                f.unlink()
            M.write(body, folder)
            return M.morning_check(p, day, decided, folder=folder, data=data, git=False)[0]
        if not opens(good):
            bad.append("맞는 아침 확인 manifest를 거부함")
        late = (decided + timedelta(minutes=1)).astimezone(timezone.utc).strftime(M.UTC_FORM)
        for name, change in (("19:20 정기만", {"mode": "regular"}), ("ok 거짓", {"ok": False}), ("판단 뒤 완료", {"completed_at_utc": late}),
                             ("질의 날 다름", {"query_end": day}), ("트리 지문 다름", {"event_data_tree_digest": "0" * 64})):
            body = dict(good)
            body.update(change)
            if opens(body):
                bad.append(f"{name} manifest를 통과시킴")
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
            if not info["trading"]:
                reasons.append("달력에서 오늘은 휴장")
        reasons += _gate_shape(day)
        reasons += _old_output_rejected(day, (info or {}).get("P") or "20000101")
        reasons += _manifest_binding(day, (info or {}).get("P") or "20000101")
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
