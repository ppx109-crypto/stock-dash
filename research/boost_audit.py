"""BOOST-0001-A 판단 기록 감사(사전등록 판 3의 셈 코드 · 읽기만 · 주문 없음 · 봇 규칙은 그대로).

범위(판 3 · GPT #488 검토 뒤): **G2 — 결정 · 장부 · 주문 일치**. 후보 생성 앞 원천 자료(공시 · 수급 · 목표가 등)의 수집 시각 · 완전성은
증명하지 않음(G1 원천 영수증 사슬은 따로 사전등록). 기록에 적힌 자료 날짜 점검은 '찾아내기'일 뿐 증명이 아님.

기록(<봇 장부 폴더>/audit/<날>-<봇>.json · audit_log.py)은 **끝점 커밋에서** 읽고, 분모는 **고정 목록**(run_days.json · 지문 고정)만 씀:
 ① 재현   판단 때 HEAD의 코드 트리(+ 기록한 블롭)를 격리한 하위 작업에서 판단 · 덧붙임 목표 · 입력 다시 만들기(엔진 이력 ·
          덧붙임 종가 줄 · 국면 · 바구니 반응 · 200위 안 · t0 사건)를 하고 기록과 canon 글로 비교
 ② 자료 날짜  1일봉 일봉 · 엔진 ETF · 덧붙임 종가 줄의 날짜(판단 날 이상 → 미래 · 어제 거래일 아님 → LATE_INPUT) · 결측
 ③ 때     주문 마감 뒤 · 봇의 늦음 → 부른 까닭과 상관없이 SCHEDULER · 예약 아닌 실행은 참고(MANUAL)
 ④ 장부   같은 작업 커밋의 장부 = 판단 뒤 지문 · 앞 판단 커밋이 이번 HEAD의 조상 · 판단 앞 장부 = HEAD 판(같은 작업 안 앞 단계는 그 줄로)
 ⑤ 증권사 · ⑥ 주문 대조 · ⑦ 빠짐 · 겹침 · 예정 무실행 날 실행 · 분모 밖 기록(OFF_CALENDAR)
쓰기: python research/boost_audit.py --from 20261109 --to 20261207 [--causes 파일] [--out 폴더] [--end-commit 커밋] [--days 분모 파일]
끝 상태: 0 = 진행 중 · 설명 필요 · 통과 / 1 = 실패 / 2 = 불완전(감사 쪽 읽기 실패 · 분모 지문 다름 · 다시 셈)
"""
import argparse
import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

KST = ZoneInfo("Asia/Seoul")
CODE_ROOT = Path(__file__).resolve().parents[1]     # 감사 코드가 있는 작업 나무(재현에는 쓰지 않음 · 하위 작업은 판단 때 HEAD 트리만)
ROOT = CODE_ROOT                                     # git 저장소(기록 · 자료 · 코드 판을 읽음)
if os.environ.get("BOOSTA_SUB") != "1":              # 하위 작업 안에서는 작업 나무를 경로에 넣지 않음(판단 때 코드와 섞이지 않게)
    for _p in (str(CODE_ROOT), str(CODE_ROOT / "research")):
        if _p not in sys.path:
            sys.path.append(_p)

import audit_log as A          # noqa: E402

BOTS = {"engine": "idle-live", "basket": "basket-live", "overlay": "overlay-live", "daily": "daily-live"}
DECISION_MODULES = {"engine": ("idle_live", "idle_signal"), "basket": ("basket_live",), "overlay": ("overlay_live",), "daily": ("daily_live",)}
CODES = ("LATE_INPUT", "SCHEDULER", "LEDGER", "BROKER", "MANUAL", "OFF_CALENDAR")
HARD = ("미래", "재현", "기록 고장")                       # 설명으로 못 덮음(즉시 실패)
MISSING = ("빠짐", "겹침", "주문 빠짐", "예정 무실행 날 실행")  # 원인 꼬리표 + 근거로만 덮음(못 덮으면 즉시 실패)
STRAIN_TAGS = ("SCHEDULER",) + MISSING
EVIDENCE = re.compile(r"\d{8,}|\b[0-9a-f]{7,40}\b")
STRAIN = 0.10                  # 위 꼬리표가 하나라도 붙은 봇 × 날 칸이 10%를 넘으면 '실행 보강 필요'(판정과 함께 적음)
RUN_DAYS_PATH = CODE_ROOT / "research-exchange" / "claude-to-gpt" / "BOOST-0001-A" / "run_days.json"
RUN_DAYS_SHA = "a19eb525eedfdc9874f0c0af44039ae05db1aa4a17caef554b4eec44decdb811"    # 사전등록 판 3에 고정한 분모 파일
EVENTS_DUE = "1920"            # (참고만) 바구니 t0 공시 수집 예정 시각 — 커밋 시각은 수집 시각 인증이 아님
END = "HEAD"                   # 끝점 커밋(audit()가 정해 고정 · git은 이 커밋까지만 봄)
ERRS = []                      # 감사 쪽 읽기 실패(하나라도 있으면 '불완전' · 봇 탓으로 세지 않음)


# ───────────────────────── 저장소 읽기 ─────────────────────────

def git(*args, text=True):
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=text)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(str(a) for a in args[:2])} 실패")
    return out.stdout


def show(commit, path, raw=False, required=False):
    """그 커밋의 파일 내용(없으면 None). required면 못 읽은 것을 읽기 실패로 셈."""
    try:
        return git("show", f"{commit}:{path}", text=not raw)
    except RuntimeError:
        if required:
            ERRS.append(f"{str(commit)[:12]}:{path} 읽기 실패")
        return None


def sha(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def is_ancestor(a, b):
    out = subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=ROOT, capture_output=True)
    if out.returncode in (0, 1):
        return out.returncode == 0
    ERRS.append(f"조상 확인 실패 {a[:12]} → {b[:12]}")
    return None


def extract(commit, paths, into):
    raw = git("archive", commit, "--", *paths, text=False)
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        tar.extractall(into, filter="data")


def load_run_days(path=RUN_DAYS_PATH, want=RUN_DAYS_SHA):
    """고정 분모 파일. 지문이 사전등록과 다르면 읽기 실패(불완전)로 셈."""
    try:
        raw = Path(path).read_bytes()
    except OSError:
        ERRS.append(f"분모 파일 {path} 없음")
        return None
    if want and sha(raw) != want:
        ERRS.append(f"분모 파일 지문 {sha(raw)[:12]} ≠ 사전등록 {want[:12]}")
    return json.loads(raw.decode("utf-8"))


def special_hours():
    """봇이 쉬도록 정한 장 시간이 다른 날(collect_kis_intraday.SPECIAL_HOURS · 끝점 커밋 판) — 분모 파일의 예정 무실행과 대조용."""
    txt = show(END, "collect_kis_intraday.py", required=True)
    try:
        for node in ast.parse(txt or "").body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "SPECIAL_HOURS" for t in node.targets):
                return {str(k): str(v) for k, v in ast.literal_eval(node.value).items()}
    except (SyntaxError, ValueError):
        pass
    ERRS.append("장 시간이 다른 날 목록(SPECIAL_HOURS)을 못 읽음")
    return {}


def prev_day(cal, day):
    xs = [d for d in cal if d < day]
    return xs[-1] if xs else None


def receipts(start, end):
    """끝점 커밋의 기록 {(날, 봇): (경로, 내용)}."""
    out = {}
    for bot, folder in BOTS.items():
        try:
            names = git("ls-tree", "-r", "--name-only", END, "--", f"{folder}/audit").split()
        except RuntimeError:
            ERRS.append(f"{folder}/audit 목록 읽기 실패")
            continue
        for rel in names:
            name = rel.rsplit("/", 1)[-1]
            if not name.endswith(f"-{bot}.json"):
                continue
            d = name.split("-")[0]
            if not start <= d <= end:
                continue
            txt = show(END, rel, required=True)
            if txt is None:
                continue
            try:
                out[(d, bot)] = (rel, json.loads(txt))
            except ValueError:
                ERRS.append(f"{rel} JSON 읽기 실패")
    return out


# ───────────────────────── 하위 작업(판단 때 HEAD 코드 트리 + 기록 블롭 · 판단 때 자료) ─────────────────────────

DRIVER = """import importlib.util, json, os, sys
tmp, me, task = sys.argv[1:4]
os.environ["BOOSTA_SUB"] = "1"
sys.path[:0] = [tmp, os.path.join(tmp, "research")]
spec = importlib.util.spec_from_file_location("boost_audit", me)
B = importlib.util.module_from_spec(spec)
sys.modules["boost_audit"] = B
spec.loader.exec_module(B)
payload = json.load(open(os.path.join(tmp, "payload.json"), encoding="utf-8"))
print(json.dumps(B.task(task, payload, tmp), ensure_ascii=False))
"""


def run_at(task_name, payload, head, folders=(), blobs=None):
    """판단 때 HEAD의 코드 트리(루트 · research의 .py) + 자료 폴더 + 기록한 블롭으로 하위 작업 → 결과. 못 하면 None(읽기 실패로 셈)."""
    try:
        with tempfile.TemporaryDirectory(prefix="boostA-") as tmp:
            extract(head, [":(glob)*.py", ":(glob)research/*.py"], tmp)
            for f in folders:
                extract(head, [f], tmp)
            for rel, blob in (blobs or {}).items():
                if rel.startswith(("/", "..")) or "/../" in rel or not re.fullmatch(r"[0-9a-f]{40}", str(blob)):
                    raise ValueError(f"이상한 코드 판 {rel}")
                q = Path(tmp) / rel
                q.parent.mkdir(parents=True, exist_ok=True)
                q.write_bytes(git("cat-file", "-p", blob, text=False))
            Path(tmp, "payload.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k not in ("CAPS_ADJ", "PYTHONPATH")}   # 작업 흐름과 같게 · 바깥 경로 안 섞임
            out = subprocess.run([sys.executable, "-c", DRIVER, tmp, str(Path(__file__).resolve()), task_name], cwd=tmp, env=env,
                                 capture_output=True, text=True, timeout=1800)
            if out.returncode != 0:
                raise RuntimeError(out.stderr.strip().splitlines()[-1] if out.stderr.strip() else "끝 상태 ≠ 0")
            return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception as e:
        ERRS.append(f"하위 작업 {task_name} 실패 · {type(e).__name__} · {str(e)[:80]}")
        return None


def tree_digest(tmp):
    """격리 재현 트리 지문 = 꺼낸 루트 · research `.py` 파일들의 (경로, sha256) 목록의 sha256."""
    rows = []
    for p in sorted(list(Path(tmp).glob("*.py")) + list((Path(tmp) / "research").glob("*.py"))):
        rows.append(f"{p.relative_to(tmp).as_posix()}\t{sha(p.read_bytes())}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def task(name, p, tmp):
    """하위 작업 안에서 도는 셈(cwd = 꺼낸 트리 · 코드는 그 트리에서만)."""
    if name != "check_group":
        raise ValueError(name)
    tree = tree_digest(tmp)
    out = []
    for item in p["items"]:
        bot, body = item["bot"], item["body"]
        r = {"key": item["key"]}
        same, _, why = replay(bot, body)
        r["same"], r["why"] = same, why
        if bot == "overlay":
            r["target_ok"], r["target_why"] = replay_overlay_target(body)
        r.update(rebuild(bot, body))
        mods = {m: getattr(sys.modules.get(m), "__file__", None) for m in DECISION_MODULES[bot] + ("audit_log",)}
        r["isolated"] = all(f and os.path.realpath(f).startswith(os.path.realpath(tmp)) for f in mods.values())
        r["tree"] = tree
        out.append(r)
    return {"items": out, "tree": tree}


def rebuild(bot, body):
    """판단 때 HEAD의 코드 · 자료로 입력을 다시 만들어 기록과 비교 → {"rebuild": [다른 것 목록]}."""
    day, i, x = body["날"], body.get("입력") or {}, body.get("곁") or {}
    bad = []
    try:
        if bot == "engine":
            import idle_live as I
            for code, n in (x.get("px_len") or {}).items():
                now = (i.get("now_price") or {}).get(code)
                full = np.array(I.history(code, day) + [now], float) if now is not None else None
                tail = (i.get("px") or {}).get(code) or []
                if full is None or len(full) != n or A.digest(full) != (x.get("px_digest") or {}).get(code) \
                        or A.canon(full[-len(tail):].tolist() if tail else []) != A.canon(tail):
                    bad.append(f"{code} 가격 이력")
        elif bot == "overlay":
            import overlay_live as O
            rows = O.closes(before=day)
            if A.digest(rows) != x.get("rows_digest"):
                bad.append("KODEX 200 종가 줄")
            elif rows and not i.get("stale") and O.states(rows)[rows[-1][0]] != i.get("state"):
                bad.append("국면")
        elif bot == "basket" and i.get("t0") and x.get("before"):
            import basket_live as BL
            import study
            react, inside = BL.reactions(study.load_prices(), i["t0"], x["before"])
            got = {"react": react, "inside": inside, "events": BL.todays_events(BL.load_events(), i["t0"], x["before"])}
            for k, rec in (("react", i.get("react")), ("inside", i.get("inside")), ("events", i.get("events_t0"))):
                if A.canon(got[k]) != A.canon(rec):
                    bad.append(f"바구니 {k}")
    except Exception as e:
        bad.append(f"다시 만들기 오류 {type(e).__name__}")
    return {"rebuild": bad}


# ───────────────────────── ① 재현 ─────────────────────────

def replay(bot, body):
    """(같음 여부, 다시 낸 결과, 까닭) — 불러온 코드로(하위 작업 안에서는 판단 때 HEAD 트리). 물은 적 없는 질문 · 답이 둘이면 실패."""
    import basket_live as BL
    import daily_live as D
    import idle_live as I
    import overlay_live as O
    i, x = body.get("입력"), body.get("곁") or {}
    if i is None:
        return False, None, "기록 고장(입력 없음)"
    try:
        if bot == "engine":
            px = {c: np.array(v, float) for c, v in i["px"].items()}
            o, st, why = I.step(i["state"], i["day"], px, i["breadth"], i["used"], i["total"], i["cash"], i["held"],
                                i["now_price"], i["is_week_end"], reserve=i["reserve"])
            got = {"orders": o, "new_state": st, "why": why}
        elif bot == "basket":
            asked = {}
            for d, n in x.get("days_since_calls", []):
                if asked.setdefault(str(d), n) != n:
                    return False, None, f"날짜 셈 {d}에 답이 둘"
            o, st, why = BL.step(i["state"], i["day"], i["t0"], lambda d: asked[str(d)], [tuple(e) for e in i["events_t0"]],
                                 i["react"], set(i["inside"]), i["held"], i["now_price"], capital=i["capital"], avail=i["avail"],
                                 names=i["names"], others=set(i["others"]))
            got = {"orders": o, "new_state": st, "why": why}
        elif bot == "overlay":
            got = {"rebalance": (not i["stale"]) and O.needs_rebalance(i["st"], i["state"], i["day"])}
        elif bot == "daily":
            asked = {}
            for code, holding, ans in x.get("kin_calls", []):
                if asked.setdefault((code, tuple(holding)), ans) != ans:
                    return False, None, f"닮음 질문 {code}에 답이 둘"
            s, b = D.decide(i["state"], i["cands"], i["now_price"], i["aligned"], i["rate"], lambda c, h: asked[(c, tuple(h))])
            got = {"sells": s, "buys": b}
        else:
            return False, None, "모르는 봇"
    except KeyError as e:
        return False, None, f"기록에 없는 값을 물음 · {e}"
    except Exception as e:
        return False, None, f"재현 중 오류 · {type(e).__name__}"
    same = A.canon(got) == A.canon(body.get("결과"))
    return same, A.plain(got), "같음" if same else "다름"


def replay_overlay_target(body):
    """덧붙임 맞춤 수량 · 주문 목록 다시 셈(맞춘 날만). (같음 여부 또는 None, 까닭)."""
    import overlay_live as O
    t = (body.get("주문 결과") or {}).get("target")
    if not t:
        return None, "맞춘 날 아님"
    try:
        code, want, f = O.target_qty(t["state"], t["nav_total"], t["cash_b"], t["nav_b"], t["reserve"], t["price"])
    except Exception as e:
        return False, f"재현 중 오류 · {type(e).__name__}"
    orders = [[c, "sell", q] for c, q in t["cur"].items() if c != code]
    if code:
        diff = want - t["cur"].get(code, 0)
        if diff:
            orders.append([code, "sell" if diff < 0 else "buy", abs(diff)])
    same = A.canon([want, f, orders]) == A.canon([t.get("want"), t.get("f"), body["주문 결과"].get("orders")])
    return same, "같음" if same else f"다름(수량 {want} · 몫 {f} · 주문 {orders})"


def code_problems(body):
    """기록한 코드 판 · HEAD가 재현에 쓸 수 있는 꼴인지(아니면 기록 고장)."""
    rec, head = body.get("코드"), body.get("판단 때 저장소 HEAD")
    if not head:
        return "기록 고장(판단 때 HEAD 없음)"
    if not isinstance(rec, dict) or not rec or any(not re.fullmatch(r"[0-9a-f]{40}", str(v or "")) for v in rec.values()):
        return "기록 고장(코드 판 없음)"
    if body.get("입력") is None:
        return "기록 고장(입력 없음)"
    return None


def check_groups(found):
    """기록을 (판단 때 HEAD · 기록 블롭)으로 묶어 하위 작업 한 번씩 → {(날, 봇): 결과}. 실패한 묶음은 결과 없음(불완전)."""
    groups = {}
    for (d, bot), (rel, body) in found.items():
        if code_problems(body):
            continue
        k = (body["판단 때 저장소 HEAD"], json.dumps(body["코드"], sort_keys=True))
        groups.setdefault(k, []).append({"key": f"{d}:{bot}", "bot": bot, "body": body})
    out = {}
    for (head, blobs), items in groups.items():
        folders = ["etf-data"] + (["price-data", "share-data", "event-data"] if any(it["bot"] == "basket" for it in items) else [])
        got = run_at("check_group", {"items": items}, head, folders=folders, blobs=json.loads(blobs))
        for r in (got or {}).get("items", []):
            d, bot = r["key"].split(":")
            out[(d, bot)] = r
    return out


# ───────────────────────── ② 자료 날짜 · 결측 ─────────────────────────

def inputs_check(bot, body, cal, ctx):
    """(문제, 참고). 기록에 적힌 자료 날짜 · 결측만 봄(원천 수집 시각 증명 아님). 코드에 기대는 다시 만들기는 하위 작업(rebuild)에서."""
    day, i, x = body["날"], body.get("입력") or {}, body.get("곁") or {}
    pd = prev_day(cal, day)
    head = body.get("판단 때 저장소 HEAD")
    out, info = [], []
    if bot == "daily":
        asof = x.get("data_asof")
        if not isinstance(asof, dict):
            out.append(("기록 고장", "일봉 자료 날짜 칸 없음"))
        elif asof.get("today_or_later") or (asof.get("max") and asof["max"] >= day):
            out.append(("미래", f"판단 날 이상 일봉 줄 {asof.get('today_or_later')}종목 · 마지막 {asof.get('max')}"))
        if x.get("expect") != pd:
            out.append(("LATE_INPUT", f"증권사 기대일 {x.get('expect')} · 분모 파일 어제 거래일 {pd}"))
        if not x.get("ready"):
            out.append(("LATE_INPUT", f"일봉 자료 준비 안 됨 → 새로 사기 멈춤 · {str(x.get('data_why'))[:60]}"))
        if x.get("quotes") is not None and x.get("pool") and x["quotes"] < x["pool"]:
            out.append(("BROKER", f"지금 값 받은 수 {x['quotes']}/{x['pool']}"))
        miss = sorted(c for c in (i.get("state") or {}).get("positions", {}) if c not in (i.get("now_price") or {}))
        if miss:
            out.append(("BROKER", f"든 종목 지금 값 없음 {miss} → 팔기 판단 안 함"))
    elif bot == "engine":
        asof = x.get("etf_asof")
        if not isinstance(asof, dict):
            out.append(("기록 고장", "ETF 자료 날짜 칸 없음"))
            asof = {}
        for code, a in asof.items():
            if a.get("last") and a["last"] >= day:
                out.append(("미래", f"{code} 판단에 쓴 이력 마지막 {a['last']} ≥ 판단 날"))
            elif code in (i.get("px") or {}) and a.get("last") != pd:
                out.append(("LATE_INPUT", f"{code} 이력 마지막 {a.get('last')} · 어제 거래일 {pd}"))
        if x.get("breadth_raw") is None:
            out.append(("LATE_INPUT", "시장 폭 못 셈 → 100으로 봄(엔진 끔)"))
        if x.get("px_missing"):
            out.append(("BROKER", f"지금 값 · 이력 없는 ETF {x['px_missing']} → 판단에서 빠짐"))
    elif bot == "overlay":
        rows_last = i.get("rows_last") or []
        last = rows_last[-1][0] if rows_last else None
        if last and last >= day:
            out.append(("미래", f"KODEX 200 종가 줄 마지막 {last} ≥ 판단 날"))
        elif i.get("stale") or last != pd:
            out.append(("LATE_INPUT", f"KODEX 200 마지막 {last or '-'} · 어제 거래일 {pd}(맞추지 않음)"))
    elif bot == "basket":
        import basket_live as BL
        tail = x.get("days_tail") or []
        if i.get("t0") != pd:
            out.append(("LATE_INPUT", f"t0 {i.get('t0')} · 어제 거래일 {pd}"))
        lo = cal[0] if cal else day
        if not tail or tail[-1] != day or [d for d in tail[:-1] if d >= lo] != [d for d in cal if lo <= d < day]:
            out.append(("LATE_INPUT", "거래일 목록이 분모 파일의 거래일과 다름(날짜 셈이 어긋날 수 있음)"))
        for d, n in x.get("days_since_calls", []):          # 날짜 셈 답을 거래일 목록으로 다시 확인
            if d in tail:
                ok = n == len(tail) - 1 - tail.index(d)
            elif tail and d >= tail[0]:
                ok = n == sum(1 for t in tail if t > d)
            else:
                continue
            if not ok:
                out.append(("재현", f"날짜 셈 {d} → {n}이 거래일 목록과 다름"))
        if head and i.get("t0") and x.get("before"):
            try:
                ct = git("log", "-1", "--format=%ct", head, "--", "event-data").strip()
                at = datetime.fromtimestamp(int(ct), KST).strftime("%Y%m%d %H%M") if ct else None
                info.append(f"참고 · 판단 앞 마지막 공시 커밋 {at}(커밋 시각 · 수집 시각 인증 아님 · t0 수집 예정 {i['t0']} {EVENTS_DUE})")
            except (RuntimeError, ValueError):
                ERRS.append(f"{day}:basket 공시 커밋 시각 읽기 실패")
            now = set(BL.todays_events(ctx["main_events"], i["t0"], x["before"]))
            extra = sorted(now - {tuple(e) for e in i.get("events_t0", [])})
            inside, react = set(i.get("inside", [])), i.get("react", {})
            big = [c for c, k in extra if c in inside and react.get(c) is not None and (k == "무상증자" or react[c] < BL.TH)]
            if big:
                out.append(("LATE_INPUT", f"판단 뒤 들어온 t0 사건이 결정을 바꿨을 수 있음 {big}"))
            elif extra:
                info.append(f"판단 뒤 들어온 t0 사건 {len(extra)}건(결정과 무관)")
        why = (body.get("결과") or {}).get("why") or []
        for c in sorted({c for c, _ in i.get("events_t0", []) if c in set(i.get("inside", [])) and c not in (i.get("now_price") or {})}):
            nm = (i.get("names") or {}).get(c, c)
            if any(str(w).startswith(f"{nm} ") and "살 돈이 모자람" in str(w) for w in why):    # 값이 없어 수량 0 → 안 삼
                out.append(("BROKER", f"사건 종목 {c} 지금 값 없음 → 안 삼"))
            else:
                info.append(f"사건 종목 {c} 지금 값 없음(결정과 무관)")
    return out, info


def main_events_at(commit):
    import basket_live as BL
    try:
        with tempfile.TemporaryDirectory(prefix="boostA-") as tmp:
            extract(commit, ["event-data"], tmp)
            return BL.load_events(folder=str(Path(tmp) / "event-data"))
    except Exception as e:
        ERRS.append(f"끝점 공시 자료 꺼내기 실패 · {type(e).__name__}")
        return {}


# ───────────────────────── ③ 때 · ⑤ 증권사 · ⑥ 주문 대조 ─────────────────────────

def hhmm(body):
    return (body.get("기록 시각(한국)") or "")[11:16].replace(":", "")


def timing(bot, body, sess):
    """(문제, 참고). 늦어 주문을 못 낸 것은 부른 까닭과 상관없이 SCHEDULER(설명 필요)."""
    out, info = [], []
    start, deadline = sess["판단"][bot], sess["마감"][bot]
    t, res, x = hhmm(body), body.get("주문 결과") or {}, body.get("곁") or {}
    late = res.get("late") if "late" in res else (x.get("late_at_decision") if bot == "engine" else x.get("late"))
    ev = body.get("부른 까닭")
    if late or not t or t > deadline:
        out.append(("SCHEDULER", f"기록 {t or '-'} · 주문 마감 {deadline} 넘음(주문 못 냄 · 부른 까닭 {ev or '작업 흐름 밖'})"))
    if t and t < start:
        out.append(("SCHEDULER", f"기록 {t} · 판단 시각 {start} 전"))
    if ev != "schedule":
        info.append(f"MANUAL · 부른 까닭 {ev or '작업 흐름 밖'}")
    return out, info


def book_rows(body):
    """오늘 장부 주문(봇 장부에 적힌 그날 주문 · 자리 내주기 · 비켜 두기 · 흔들림 덜어내기 포함)."""
    rows, bad = [], []
    for path, got in (body.get("오늘 장부 주문") or {}).items():
        if isinstance(got, list):
            rows += got
        else:
            bad.append(path)
    return rows, bad


def broker_check(bot, body):
    rows, bad = book_rows(body)
    if bot == "overlay":
        seen = {(o.get("code"), o.get("side"), o.get("status")) for o in rows}
        rows += [o for o in (body.get("주문 결과") or {}).get("sent") or [] if (o.get("code"), o.get("side"), o.get("status")) not in seen]
    out = [("LEDGER", f"{p} 오늘 주문 줄을 못 읽음") for p in bad]
    for o in rows:
        st = str(o.get("status", ""))
        if not st.startswith("접수"):
            out.append(("BROKER", f"{o.get('code')} {o.get('side')} · {st[:40]}"))
        elif "줄임" in st:
            out.append(("BROKER", f"{o.get('code')} {o.get('side')} · 수량 줄임(살 수 있는 만큼)"))
    return out


def orders_check(bot, body):
    """판단한 주문이 장부에 있는지(늦은 날은 SCHEDULER가 덮음). 없으면 '주문 빠짐'."""
    res, out = body.get("주문 결과"), []
    if res is None or res.get("late") or (body.get("곁") or {}).get("late"):
        return out
    day, rows = body["날"], book_rows(body)[0]
    keys = {str(o.get("key", "")) for o in rows}
    if bot in ("engine", "basket"):
        for o in (body.get("결과") or {}).get("orders", []):
            if f"{day}:{o[1]}:{o[0]}" not in keys:
                out.append(("주문 빠짐", f"{o[0]} {o[1]} 판단했으나 장부에 없음"))
    elif bot == "overlay":
        sent = {(o.get("code"), o.get("side")) for o in res.get("sent") or []}
        for o in res.get("orders") or []:
            if (o[0], o[1]) not in sent and f"{day}:{o[1]}:{o[0]}" not in keys:
                out.append(("주문 빠짐", f"{o[0]} {o[1]} 판단했으나 주문 줄 없음"))
    elif bot == "daily":
        lines = [str(s) for s in res.get("paper") or []]
        for x in (body.get("결과") or {}).get("sells", []) + (body.get("결과") or {}).get("buys", []):
            code, kind = x.get("code"), x.get("type")
            placed = any(k.startswith(f"{day}1520:{kind}:{code}:") for k in keys)
            skipped = any("건너뜀" in s and f"({code})" in s for s in lines)        # paper_trade가 까닭과 함께 건너뛴 주문
            if not placed and not skipped:
                out.append(("주문 빠짐", f"{code} {kind} 판단했으나 장부 · 건너뜀 줄에 없음"))
    return out


# ───────────────────────── ④ 장부 · ⑦ 겹침 ─────────────────────────

def versions_of(rel):
    """기록 파일의 판들 [(커밋, 내용)] (오래된 → 새 · 끝점까지)."""
    try:
        hs = git("log", END, "--reverse", "--format=%H", "--", rel).split()
    except RuntimeError:
        ERRS.append(f"{rel} 기록 읽기 실패")
        return None
    out = []
    for h in hs:
        txt = show(h, rel)
        try:
            out.append((h, json.loads(txt) if txt else None))
        except ValueError:
            out.append((h, None))
    return out


def job_commit(vers, body):
    """이 기록(주문 결과 포함)을 처음 올린 커밋 = 판단한 작업이 장부와 함께 올린 커밋. 없으면 ''."""
    for h, b in vers:
        if b and "주문 결과" in b and b.get("작업 번호") == body.get("작업 번호") \
                and b.get("덧붙인 시각(한국)") == body.get("덧붙인 시각(한국)"):
            return h
    return ""


def in_job_change(bot, path, body, commit):
    """판단 앞 장부가 HEAD 판과 다른 까닭이 같은 작업 안의 앞 단계인지(엔진 자리 내주기 · 1일봉 흔들림 덜어내기)."""
    day, x = body["날"], body.get("곁") or {}
    if bot == "engine" and x.get("room_note"):
        return "같은 작업 안 자리 내주기(판단 앞)"
    if bot == "daily" and path.endswith("paper-orders.json") and commit:
        txt = show(commit, path)
        try:
            orders = (json.loads(txt) or {}).get("orders", []) if txt else []
        except ValueError:
            orders = []
        if any(str(o.get("key", "")).startswith(f"{day}:acccap:1d:") for o in orders if isinstance(o, dict)):
            return "같은 작업 안 흔들림 상한 덜어내기(15:20 · 판단 앞)"
    return None


def ledger_check(bot, rel, body, prev_commit, vers):
    """(문제, 참고, 이 기록을 올린 커밋)."""
    out, info = [], []
    commit = job_commit(vers, body) if vers is not None else None
    if commit == "":
        out.append(("LEDGER", "판단 뒤 기록이 저장소에 안 올라감"))
    elif commit:
        first = next((b for h, b in vers if h == commit), None)
        if A.canon(first) != A.canon(body):
            out.append(("기록 고장", "판단한 작업이 올린 기록과 끝점 기록이 다름(나중에 고쳐짐)"))
        for path, dg in (body.get("장부 지문(판단 뒤)") or {}).items():
            if sha(show(commit, path, raw=True)) != dg:
                out.append(("LEDGER", f"{path} 올린 장부가 판단 뒤 장부와 다름"))
    head = body.get("판단 때 저장소 HEAD")
    if head and prev_commit and is_ancestor(prev_commit, head) is False:
        out.append(("LEDGER", "앞 판단 뒤 저장소를 못 받고 판단함(옛 장부)"))
    if head:
        for path, dg in (body.get("장부 지문(판단 앞)") or {}).items():
            if sha(show(head, path, raw=True)) != dg:
                why = in_job_change(bot, path, body, commit)
                if why:
                    info.append(f"{path} 판단 앞 장부 ≠ HEAD 판 · {why}")
                else:
                    out.append(("LEDGER", f"{path} 판단 앞 장부가 판단 때 저장소 판과 다름(까닭 모름)"))
    return out, info, commit


def duplicates(vers):
    runs = {(b.get("작업 번호"), b.get("작업 시도")) for _, b in vers or [] if b and "결과" in b}
    return [("겹침", f"판단을 적은 작업(번호 · 시도) {len(runs)}개")] if len(runs) > 1 else []


# ───────────────────────── 하루 · 기간 ─────────────────────────

def explained(causes, key, tag):
    e = (causes.get(key) or {}).get(tag)
    if tag in MISSING:
        return isinstance(e, dict) and e.get("원인") in CODES and bool(EVIDENCE.search(str(e.get("근거", ""))))
    if isinstance(e, dict):
        e = e.get("근거")
    return bool(e) and bool(EVIDENCE.search(str(e)))


def incomplete(start, end):
    return {"요약": {"기간": [start, end], "끝점 커밋": None, "불완전": list(ERRS), "판정": "불완전(다시 셈)"}, "줄들": []}


def audit(start, end, causes=None, end_commit="HEAD", run_days=None):
    """run_days = 고정 분모(없으면 사전등록 지문을 확인하며 읽음)."""
    global END
    ERRS.clear()
    if run_days is None:
        run_days = load_run_days()
    try:
        END = git("rev-parse", "--verify", f"{end_commit}^{{commit}}").strip()
    except RuntimeError:
        ERRS.append(f"끝점 커밋 {end_commit}을 못 읽음")
        return incomplete(start, end)
    if run_days is None:
        return incomplete(start, end)
    cal = list(run_days["거래일"])
    sess = run_days["세션"]["보통"]
    planned_off = dict(run_days.get("예정 무실행") or {})
    days = [d for d in run_days["기대 실행일"] if start <= d <= end]
    bots_off = {d for d in special_hours() if start <= d <= end}
    if bots_off != {d for d in planned_off if start <= d <= end}:
        ERRS.append(f"봇이 쉬는 날 {sorted(bots_off)} ≠ 분모 파일 예정 무실행 {sorted(d for d in planned_off if start <= d <= end)}")
    found = receipts(start, end)
    ctx = {"main_events": main_events_at(END)}
    checked = check_groups(found)
    causes = causes or {}
    rows, fails, needs = [], [], []
    for bot in BOTS:
        prev_commit = None
        for d in sorted(set(days) | {d for d, b in found if b == bot}):
            key = f"{d}:{bot}"
            row = {"날": d, "봇": bot, "문제": [], "참고": [], "분모": d in days}
            got = found.get((d, bot))
            if d not in days:
                if d in planned_off:
                    row["문제"].append(("예정 무실행 날 실행", f"{str(planned_off[d].get('까닭', ''))[:40]} 날인데 기록이 있음"))
                else:
                    row["문제"].append(("OFF_CALENDAR", "분모 파일의 기대 실행일이 아닌 날의 기록"))
            if got is None:
                eng = found.get((d, "engine"))
                if bot in ("basket", "overlay") and eng and hhmm(eng[1]) > sess["마감"]["engine"]:
                    row["문제"].append(("SCHEDULER", f"엔진 기록 {hhmm(eng[1])} · 마감 뒤라 {bot}는 돌지 않음(설계대로)"))
                else:
                    row["문제"].append(("빠짐", "기록 없음"))
            else:
                rel, body = got
                bad = code_problems(body)
                r = checked.get((d, bot))
                if bad:
                    row["문제"].append(("기록 고장", bad))
                elif r is None:
                    row["재현"] = "판단 때 코드 판으로 재현 못 함(불완전)"
                else:
                    row["재현"] = r["why"]
                    row["재현 트리"] = {"판단 때 HEAD": body.get("판단 때 저장소 HEAD"), "기록 블롭": body.get("코드"), "트리 지문": r.get("tree")}
                    if r["same"] is False:
                        row["문제"].append(("기록 고장" if r["why"].startswith("기록 고장") else "재현", r["why"]))
                    if not r.get("isolated"):
                        row["문제"].append(("재현", "하위 작업이 판단 때 코드 트리 밖 모듈을 불러옴"))
                    if bot == "overlay":
                        row["맞춤 재현"] = r.get("target_why")
                        if r.get("target_ok") is False:
                            row["문제"].append(("재현", "맞춤 " + str(r.get("target_why"))))
                    for what in r.get("rebuild", []):
                        row["문제"].append(("재현", f"{what}을(를) 판단 때 판으로 다시 만들면 다름"))
                if "주문 결과" not in body:
                    row["문제"].append(("빠짐", "판단 뒤 기록(주문 결과) 없음"))
                p1, i1 = inputs_check(bot, body, cal, ctx)
                p2, i2 = timing(bot, body, sess)
                vers = versions_of(rel)
                p3, i3, commit = ledger_check(bot, rel, body, prev_commit, vers)
                prev_commit = commit or prev_commit
                row["문제"] += p1 + p2 + broker_check(bot, body) + orders_check(bot, body) + p3 + duplicates(vers)
                row["참고"] += i1 + i2 + i3
                row["기록 시각"], row["부른 까닭"] = body.get("기록 시각(한국)"), body.get("부른 까닭")
                row["주문"] = [[o.get("code"), o.get("side"), str(o.get("status", ""))[:20]] for o in book_rows(body)[0]]
            for tag, text in row["문제"]:
                if tag in HARD:
                    fails.append((key, tag, text))
                elif tag in MISSING:
                    if not explained(causes, key, tag):
                        fails.append((key, tag, text))
                elif tag in CODES and not explained(causes, key, tag):
                    needs.append((key, tag, text))
            row["설명"] = causes.get(key, {})
            rows.append(row)
    in_rows = [r for r in rows if r["분모"]]
    n_cells = len(days) * len(BOTS)
    strain = sum(1 for r in in_rows if any(t in STRAIN_TAGS for t, _ in r["문제"]))     # 고유 봇 × 날 칸 수
    orders = [o for r in in_rows for o in r.get("주문", [])]
    try:
        me = {"boost_audit.py 블롭": A.blob_id(Path(__file__).resolve()),
              "감사 작업 나무 HEAD": subprocess.run(["git", "rev-parse", "HEAD"], cwd=CODE_ROOT, capture_output=True, text=True).stdout.strip()}
    except Exception:
        me = None
    all_days = run_days["기대 실행일"]
    summary = {
        "기간": [start, end], "끝점 커밋": END, "감사 코드": me, "범위": "G2(결정 · 장부 · 주문 일치) · 원천 수집 시각 증명 아님",
        "재현 트리 지문": sorted({r["재현 트리"]["트리 지문"] for r in rows if r.get("재현 트리")} - {None}),
        "기대 실행일": len(days), "기록 수": f"{sum(1 for k in found if k[0] in days)}/{n_cells}",
        "예정 무실행": {d: v.get("까닭") for d, v in planned_off.items() if start <= d <= end},
        "분모 밖 기록 날": sorted({d for d, _ in found} - set(days)),
        "꼬리표 수": {c: sum(1 for r in rows for t, _ in r["문제"] if t == c) for c in CODES + MISSING + HARD},
        "즉시 실패": fails, "설명 안 된 꼬리표": needs, "불완전": list(ERRS),
        "손으로 부른 기록": sum(1 for r in in_rows if r.get("부른 까닭") not in (None, "schedule") and "기록 시각" in r),
        "주문 접수율": f"{sum(1 for o in orders if o[2].startswith('접수'))}/{len(orders)}",
        "보강 칸": f"{strain}/{n_cells}", "실행 보강 필요": bool(n_cells) and strain / n_cells > STRAIN,
        "기준 ① · ②": "월 점검 셈(tools/bt_mix54.py · reconcile)으로 따로 보고(이 셈 밖)",
        "판정": ("실패" if fails else "불완전(다시 셈)" if ERRS else
                 "진행 중" if start > all_days[0] or end < all_days[-1] else "통과" if not needs else "설명 필요")}
    return {"요약": summary, "줄들": rows}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", required=True)
    ap.add_argument("--to", dest="end", required=True)
    ap.add_argument("--causes", default=str(CODE_ROOT / "research" / "boost_a" / "causes.json"))
    ap.add_argument("--out", default=str(CODE_ROOT / "research" / "boost_a"))
    ap.add_argument("--end-commit", default="HEAD")
    ap.add_argument("--days", default=str(RUN_DAYS_PATH))
    a = ap.parse_args(argv)
    cpath = Path(a.causes)
    causes = json.loads(cpath.read_text(encoding="utf-8")) if cpath.is_file() else {}
    ERRS.clear()
    rd = load_run_days(a.days)
    errs0 = list(ERRS)
    res = audit(a.start, a.end, causes, end_commit=a.end_commit, run_days=rd) if rd else incomplete(a.start, a.end)
    if errs0:                                     # 분모 파일 지문이 다르면 불완전
        res["요약"]["불완전"] = errs0 + res["요약"].get("불완전", [])
        if res["요약"]["판정"] != "실패":
            res["요약"]["판정"] = "불완전(다시 셈)"
    res["요약"]["설명 파일 지문"] = A.file_digest(cpath) if cpath.is_file() else None
    res["요약"]["분모 파일 지문"] = A.file_digest(a.days)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"audit-{a.end}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    s = res["요약"]
    print(f"BOOST-0001-A 감사 {a.start} ~ {a.end} · 끝점 {str(s.get('끝점 커밋'))[:12]} · 기대 실행일 {s.get('기대 실행일')} · "
          f"기록 {s.get('기록 수')} · 판정 {s['판정']}" + (" · 실행 보강 필요" if s.get("실행 보강 필요") else ""))
    print("꼬리표:", " · ".join(f"{k} {v}" for k, v in (s.get("꼬리표 수") or {}).items() if v) or "없음")
    for e in s.get("불완전", []):
        print("읽기 실패:", e)
    for f in s.get("즉시 실패", []):
        print("즉시 실패:", *f)
    for u in s.get("설명 안 된 꼬리표", []):
        print("설명 필요:", *u)
    return 1 if s["판정"] == "실패" else 2 if s["판정"].startswith("불완전") else 0


if __name__ == "__main__":
    sys.exit(main())
