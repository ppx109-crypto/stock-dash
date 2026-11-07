"""공시 manifest(BOOST-0001-D 사전등록 판 3 §1.2 · D3 · 2b단계) — 공시 수집기(collect_events.py)와 바구니 문(gates.py)이 같은 셈을 씀.

- 자리: event-manifest/<t0>-<작업 번호>-<시도>.json(자료 폴더 event-data/ 밖 · 로컬 실행은 <t0>-local-0.json).
- 갈래(mode): final = D 아침 최종 확인(평일 08:20 · 10:20 · 12:20 예약 · 첫 성공만) — **바구니 문을 여는 것은 이것뿐** ·
  regular = 19:20 정기 수집이 남기는 그날 t0 기록(문을 열지 않음 · 감사용).
- 칸: query_begin · query_end(= t0 · 판 고정 달력) · request_started_at_utc · response_received_at_utc(쪽마다) · status · total_count ·
  total_page · pages_received · retry_count · normalized_query_digest · normalized_event_digest(응답의 t0 사건 목록) ·
  event_data_tree_digest(저장 뒤 event-data 트리) · GITHUB_RUN_ID · GITHUB_RUN_ATTEMPT · GITHUB_WORKFLOW_SHA · persisted · ok
  (+ 곁 칸: mode · t0 · D · pages · rows_received · t0_events(정규화 t0 사건 목록 · H-D3 대조용) · stored_event_digest · completed_at_utc · why).
- ok(수집기가 정함) = 모든 쪽 status 정상(OpenDART '000' · 첫 쪽 '013' 정상 0건은 예외) · pages_received == total_page ·
  (사전등록보다 엄격히) 받은 줄 수 = total_count · 접수번호 겹침 없음 · 저장된 event-data의 t0 사건 목록 지문 = normalized_event_digest ·
  저장 성공(persisted).
- event_data_tree_digest = event-data/*.json을 이름 차례로 [경로, 파일 sha256] 목록 → 빈칸 없는 JSON → sha256
  (경로는 언제나 'event-data/<이름>' — 폴더가 어디 있든 같은 값 · 수집기와 바구니가 이 함수 하나를 씀).
- 바구니 문(morning_check): 판단 때 HEAD에 그날 t0의 final manifest(query_begin = query_end = t0 · D = 오늘 · ok · 저장됨 ·
  완료 시각 < 판단 시각)가 있고 그 트리 지문이 지금 event-data 트리 지문과 같을 때만 열림. 여럿이면 먼저 끝난 **첫 성공만** 씀.
  HEAD 확인: git으로 event-data/와 그 manifest 파일이 추적되고 고친 · 새 파일이 없는지(git이 없거나 저장소가 아니면 닫힘).
- 증권사 · DART를 부르지 않음(파일과 git만 읽음).
"""
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DATA = Path("event-data")
FOLDER = Path("event-manifest")
KIND = "event-manifest"
VERSION = 1
MODES = ("final", "regular")
FIELDS = ("query_begin", "query_end", "request_started_at_utc", "response_received_at_utc", "status", "total_count", "total_page",
          "pages_received", "retry_count", "normalized_query_digest", "normalized_event_digest", "event_data_tree_digest",
          "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW_SHA", "persisted", "ok")
UTC_FORM = "%Y-%m-%dT%H:%M:%SZ"
_SHA = re.compile(r"[0-9a-f]{64}")
_DAY = re.compile(r"\d{8}")
_PART = re.compile(r"[A-Za-z0-9]+")


def canon(x):
    """지문용 글(열쇠 차례 · 빈칸 없는 JSON · UTF-8)."""
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(x):
    return hashlib.sha256(canon(x).encode("utf-8")).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).strftime(UTC_FORM)


def parse_utc(text):
    """'YYYY-MM-DDTHH:MM:SSZ' → 시각(UTC) · 꼴이 다르면 None."""
    try:
        return datetime.strptime(str(text), UTC_FORM).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def tree_digest(folder=None):
    """event-data/*.json을 이름 차례로 [경로, 파일 sha256] 목록 → sha256. 폴더가 없으면 빈 목록의 지문."""
    folder = Path(folder) if folder is not None else DATA
    items = [[f"event-data/{p.name}", hashlib.sha256(p.read_bytes()).hexdigest()]
             for p in sorted(folder.glob("*.json"), key=lambda q: q.name)]
    return digest(items)


def normalize(events):
    """t0 사건 목록 → [코드, 날, 갈래, 제목] 정렬 · 겹침 없음(제목은 저장 꼴과 같게 60자까지)."""
    return [list(x) for x in sorted({(str(c), str(d), str(k), str(t)[:60]) for c, d, k, t in events})]


def stored_events(t0, folder=None):
    """저장된 event-data(모든 파일 · 바구니가 읽는 그대로)의 t0 사건 → 정규화 목록. 파일이 깨졌으면 예외(부르는 쪽이 실패로 셈)."""
    folder = Path(folder) if folder is not None else DATA
    out = []
    for p in sorted(folder.glob("*.json"), key=lambda q: q.name):
        body = json.loads(p.read_text(encoding="utf-8"))
        for r in body.get("rows") or []:
            if str(r.get("date")) == str(t0):
                out.append((p.stem, str(t0), r.get("kind"), r.get("title")))
    return normalize(out)


def query_digest(begin, end, page_count, sort, sort_mth):
    """정규화 질의 지문(키 · 쪽 번호는 뺌)."""
    return digest({"endpoint": "list.json", "bgn_de": str(begin), "end_de": str(end), "page_count": int(page_count),
                   "sort": str(sort), "sort_mth": str(sort_mth), "corp_code": None})


# ───────────────────────── 파일 ─────────────────────────

def run_tag():
    """(작업 번호, 시도) — GitHub 작업이면 GITHUB_RUN_ID · GITHUB_RUN_ATTEMPT, 로컬이면 ('local', '0')."""
    rid = (os.getenv("GITHUB_RUN_ID") or "").strip()
    att = (os.getenv("GITHUB_RUN_ATTEMPT") or "").strip()
    return (rid if _PART.fullmatch(rid) else "local"), (att if _PART.fullmatch(att) else "0")


def name_for(t0, run_id, attempt):
    return f"{t0}-{run_id}-{attempt}.json"


def write(body, folder=None):
    """manifest를 원자적으로 씀(같은 이름은 같은 작업 · 시도만) → 경로 또는 None(예외 없음)."""
    folder = Path(folder) if folder is not None else FOLDER
    p = folder / name_for(body["t0"], body["GITHUB_RUN_ID"] or "local", body["GITHUB_RUN_ATTEMPT"] or "0")
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    try:
        folder.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, p)
        return p
    except Exception as e:
        print("공시 manifest를 쓰지 못함 ·", type(e).__name__)
        try:
            tmp.unlink()
        except Exception:
            pass
        return None


def load_all(t0, folder=None):
    """그 t0의 manifest 파일들 → [(이름, 본문 또는 None)] 이름 차례."""
    folder = Path(folder) if folder is not None else FOLDER
    out = []
    for p in sorted(folder.glob(f"{t0}-*.json"), key=lambda q: q.name):
        try:
            body = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            body = None
        out.append((p.name, body if isinstance(body, dict) else None))
    return out


def shape_problems(body, name):
    """manifest 꼴 검사 → 까닭 목록(비면 꼴 맞음)."""
    if not isinstance(body, dict):
        return ["읽을 수 없는 manifest"]
    bad = [f"칸 빠짐 {k}" for k in FIELDS if k not in body]
    if body.get("kind") != KIND or body.get("mode") not in MODES:
        bad.append("갈래(kind · mode)가 이상함")
    t0 = str(body.get("t0") or "")
    if not _DAY.fullmatch(t0):
        bad.append("t0 꼴이 이상함")
    elif name != name_for(t0, body.get("GITHUB_RUN_ID") or "local", body.get("GITHUB_RUN_ATTEMPT") or "0"):
        bad.append("파일 이름이 t0 · 작업 번호 · 시도와 다름")
    if not _SHA.fullmatch(str(body.get("event_data_tree_digest") or "")):
        bad.append("트리 지문 꼴이 이상함")
    if not isinstance(body.get("ok"), bool) or not isinstance(body.get("persisted"), bool):
        bad.append("ok · persisted가 참/거짓이 아님")
    return bad


def first_ok(t0, day, folder=None):
    """수집기: 이미 그날(D) t0 아침 최종 확인이 성공했으면 그 이름(첫 성공만 · 다시 묻지 않음) · 없으면 None."""
    good = []
    for name, body in load_all(t0, folder):
        if not shape_problems(body, name) and body.get("mode") == "final" and body.get("ok") is True \
                and body.get("persisted") is True and str(body.get("D")) == str(day) and parse_utc(body.get("completed_at_utc")):
            good.append((body["completed_at_utc"], name))
    return min(good)[1] if good else None


# ───────────────────────── HEAD 확인 ─────────────────────────

def _git(args, cwd=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}       # 바깥 GIT_DIR 등에 끌려가지 않게
    return subprocess.run(["git", *args], capture_output=True, text=True, timeout=30, cwd=cwd, env=env)


def head_clean(data, manifest, cwd=None):
    """event-data/ 폴더와 manifest 파일이 HEAD 그대로인가(추적됨 · 고친 · 새 · 지운 파일 없음) → (참/거짓, 까닭).
    git이 없거나 · 저장소가 아니거나 · 확인 중 오류면 거짓(fail-closed)."""
    try:
        top = _git(["rev-parse", "--is-inside-work-tree"], cwd)
        if top.returncode != 0 or top.stdout.strip() != "true":
            return False, "git 저장소가 아니라 HEAD를 확인하지 못함"
        st = _git(["--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", str(data), str(manifest)], cwd)
        if st.returncode != 0:
            return False, "git status 실패"
        dirty = [x for x in st.stdout.splitlines() if x.strip()]
        if dirty:
            return False, f"HEAD와 다른 파일 {len(dirty)}개(" + " · ".join(x.strip() for x in dirty[:3]) + ")"
        ls = _git(["ls-files", "--error-unmatch", "--", str(manifest)], cwd)
        if ls.returncode != 0:
            return False, "manifest가 HEAD에 없음"
        return True, ""
    except Exception as e:
        return False, f"HEAD 확인 오류 · {type(e).__name__}"


# ───────────────────────── 바구니 문 ─────────────────────────

def _why_not(body, name, t0, day, decided):
    """final manifest 하나가 문을 열 수 없는 까닭(없으면 '')."""
    bad = shape_problems(body, name)
    if bad:
        return "꼴 이상 · " + " · ".join(bad[:3])
    if str(body.get("query_begin")) != str(t0) or str(body.get("query_end")) != str(t0) or str(body.get("t0")) != str(t0):
        return f"질의 날(query_begin {body.get('query_begin')} · query_end {body.get('query_end')})이 t0 {t0}와 다름"
    if str(body.get("D")) != str(day):
        return f"다른 날({body.get('D')})의 확인"
    if body.get("ok") is not True:
        return "아침 확인이 성공하지 못함(ok 거짓 · " + str(body.get("why") or "까닭 없음") + ")"
    if body.get("persisted") is not True:
        return "저장되지 않음(persisted 거짓)"
    done = parse_utc(body.get("completed_at_utc"))
    if done is None:
        return "완료 시각이 없음"
    if not done < decided:
        return f"완료 시각 {body.get('completed_at_utc')}이 판단 시각보다 늦음"
    return ""


def morning_check(t0, day, decided_at, folder=None, data=None, git=True):
    """바구니 문(§1.2) → (열림, 까닭, 기록 칸). decided_at = 판단 시각(시간대 있는 datetime). 예외 없음(셈이 말썽이면 닫힘)."""
    folder = Path(folder) if folder is not None else FOLDER
    data = Path(data) if data is not None else DATA
    info = {"t0": t0, "D": day, "decided_at_utc": None, "id": None, "completed_at_utc": None, "manifest_tree": None,
            "tree": None, "head": None, "candidates": []}
    try:
        decided = decided_at.astimezone(timezone.utc)
        info["decided_at_utc"] = decided.strftime(UTC_FORM)
        if not t0:
            return False, "앞 거래일(t0)을 몰라 공시 확인을 못 함", info
        found = load_all(t0, folder)
        good = []
        for name, body in found:
            mode = body.get("mode") if isinstance(body, dict) else None
            if mode == "final":
                why = _why_not(body, name, t0, day, decided)
            elif mode == "regular":
                why = "19:20 정기 기록(문을 열지 않음)"
            else:
                why = "읽을 수 없는 manifest"
            info["candidates"].append({"id": name, "mode": mode, "ok": body.get("ok") if isinstance(body, dict) else None,
                                       "why": why})
            if mode == "final" and not why:
                good.append((body["completed_at_utc"], name, body))
        if not good:
            if not found:
                return False, f"그날 공시 확인 기록(manifest · t0 {t0})이 없음", info
            finals = [c for c in info["candidates"] if c["mode"] == "final"]
            if not finals:
                if any(c["mode"] == "regular" for c in info["candidates"]):
                    return False, "아침 최종 확인 manifest가 없음(19:20 정기 기록만 있음)", info
                return False, "읽을 수 있는 아침 최종 확인 manifest가 없음", info
            return False, "아침 최종 확인을 쓸 수 없음 · " + " / ".join(f"{c['id']} {c['why']}" for c in finals[:3]), info
        done, name, body = min(good, key=lambda x: (x[0], x[1]))           # 첫 성공만
        info.update(id=name, completed_at_utc=done, manifest_tree=body["event_data_tree_digest"])
        info["tree"] = tree_digest(data)
        if info["tree"] != body["event_data_tree_digest"]:
            return False, f"지금 공시 자료 트리 지문이 아침 확인 manifest({name})와 다름(확인 뒤 event-data가 바뀜)", info
        if git:
            ok, why = head_clean(data, folder / name)
            info["head"] = {"ok": ok, "why": why}
            if not ok:
                return False, f"HEAD에 커밋된 그대로가 아님 · {why}", info
        return True, "", info
    except Exception as e:
        return False, f"공시 확인 셈 오류 · {type(e).__name__}", info
