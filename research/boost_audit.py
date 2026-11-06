"""BOOST-0001-A 판단 기록 감사(사전등록 판 2의 셈 코드 · 읽기만 · 주문 없음 · 봇 규칙은 그대로).

기록(<봇 장부 폴더>/audit/<날>-<봇>.json · audit_log.py)은 **끝점 커밋에서** 읽고, 하루 · 봇마다 봄:
 ① 재현   기록한 입력을 **기록한 코드 판**(블롭 id)의 판단 함수에 다시 넣으면 같은 결과인지(canon 글 비교 · nan 포함)
 ② 입력   실제 자료 날짜(1일봉 일봉 · 엔진 ETF · 덧붙임 종가 줄)가 어제 거래일인지 · 판단 날 이상 줄 → 미래(즉시 실패) ·
          판단 때 저장소 판으로 입력을 다시 만들면 같은지(엔진 이력 · 덧붙임 종가 줄 · 국면 · 바구니 반응 · 200위 안 · t0 사건) ·
          바구니 거래일 목록 = 감사 달력 · t0 공시 수집이 t0 날 19:20 뒤 · 판단 뒤 들어온 사건이 결정을 바꿨을 수 있는지 ·
          결측(시장 폭 못 셈 · 지금 값 없음)
 ③ 때     주문 마감 뒤 · 봇의 늦음 → 부른 까닭과 상관없이 SCHEDULER(설명 필요) · 손으로 부른 것은 참고(MANUAL)
 ④ 장부   판단 뒤 기록을 처음 올린 커밋(같은 작업)에서 장부 지문이 같은지 · 앞 판단의 그 커밋이 이 판단 HEAD의 조상인지 ·
          판단 앞 장부 = 판단 때 HEAD 판(같은 작업 안 자리 내주기 · 흔들림 덜어내기는 그 줄로 설명)
 ⑤ 증권사 주문 상태가 '접수'가 아님 · 수량 줄임
 ⑥ 빠짐 · 겹침 · 주문 빠짐  기록 없음 · 같은 날 다른 작업(번호 · 시도)이 판단을 또 적음 · 판단한 주문이 장부에 없음
원인 꼬리표: LATE_INPUT · SCHEDULER · LEDGER · BROKER · MANUAL. 설명 파일(causes.json)의 근거는 작업 번호(8자리 이상) 또는 커밋.
쓰기: python research/boost_audit.py --from 20261109 --to 20261204 [--causes 파일] [--out 폴더] [--end-commit 커밋]
끝 상태: 0 = 진행 중 · 설명 필요 · 통과 / 1 = 실패 / 2 = 불완전(감사 쪽 읽기 실패 · 다시 셈)
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

KST = ZoneInfo("Asia/Seoul")
CODE_ROOT = Path(__file__).resolve().parents[1]     # 재현에 쓰는 코드(기록한 판과 블롭 id가 다르면 기록한 판을 꺼내 하위 작업으로)
ROOT = CODE_ROOT                                     # git 저장소(기록 · 자료 · 코드 판을 읽음)
for _p in (str(CODE_ROOT), str(CODE_ROOT / "research")):    # 뒤에 붙임(하위 작업이 기록한 코드 판을 앞에 둘 수 있게)
    if _p not in sys.path:
        sys.path.append(_p)

import audit_log as A          # noqa: E402

BOTS = {"engine": "idle-live", "basket": "basket-live", "overlay": "overlay-live", "daily": "daily-live"}
START = {"engine": "1510", "basket": "1510", "overlay": "1510", "daily": "1520"}      # 판단 시각(이 앞 기록 = 너무 이름)
DEADLINE = {"engine": "1518", "basket": "1518", "overlay": "1520", "daily": "1528"}   # 주문 마감(이 뒤 기록 = 주문 못 냄)
CODES = ("LATE_INPUT", "SCHEDULER", "LEDGER", "BROKER", "MANUAL")
HARD = ("미래", "재현", "기록 고장")          # 설명으로 못 덮음(즉시 실패)
MISSING = ("빠짐", "겹침", "주문 빠짐")       # 원인 꼬리표 + 근거로만 덮음(못 덮으면 즉시 실패)
EVIDENCE = re.compile(r"\d{8,}|\b[0-9a-f]{7,40}\b")
EVENTS_DUE = "1920"            # 바구니 t0 공시: t0 날 19:20(평일 공시 수집 예약) 뒤 수집분이 판단 앞에 있어야 '제때'
STRAIN = 0.10                  # 설명된 빠짐 + SCHEDULER가 봇 · 날의 10%를 넘으면 '실행 보강 필요'(판정과 함께 적음)
END = "HEAD"                   # 끝점 커밋(audit()가 정해 고정 · git은 이 커밋까지만 봄 · 점검표 31)
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


_FOLDERS = {}


def folder_at(commit, folder):
    """그 커밋의 작은 자료 폴더(etf-data)를 임시 폴더에 꺼냄. 못 꺼내면 None(읽기 실패로 셈 · 실패는 담아 두지 않음)."""
    key = (commit, folder)
    if key not in _FOLDERS:
        try:
            tmp = tempfile.mkdtemp(prefix="boostA-")
            extract(commit, folder, tmp)
            _FOLDERS[key] = Path(tmp) / folder
        except Exception as e:
            ERRS.append(f"{str(commit)[:12]}:{folder} 꺼내기 실패 · {type(e).__name__}")
            return None
    return _FOLDERS[key]


def extract(commit, folder, into):
    raw = git("archive", commit, folder, text=False)
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        tar.extractall(into, filter="data")


def calendar():
    """거래일 = 끝점 커밋의 KODEX 200 종가가 있는 날(감사 때 앎 · 판단에는 안 씀)."""
    txt = show(END, "etf-data/069500.json", required=True)
    try:
        body = json.loads(txt) if txt else {}
    except ValueError:
        ERRS.append("etf-data/069500.json JSON 읽기 실패")
        body = {}
    return sorted({str(d) for d, c in body.get("closes", []) if c})


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


# ───────────────────────── 하위 작업(기록한 코드 판 · 판단 때 자료 판) ─────────────────────────

DRIVER = """import json, os, sys
tmp, code, task = sys.argv[1:4]
sys.path[:0] = [tmp, os.path.join(tmp, "research")]
sys.path += [code, os.path.join(code, "research")]
import boost_audit as B
payload = json.load(open(os.path.join(tmp, "payload.json"), encoding="utf-8"))
print(json.dumps(B.task(task, payload), ensure_ascii=False))
"""


def run_at(task_name, payload, head=None, folders=(), blobs=None):
    """판단 때 HEAD의 자료 폴더 + 기록한 코드 판(블롭)으로 하위 작업을 돌림 → 결과 dict. 못 하면 None(읽기 실패로 셈)."""
    try:
        with tempfile.TemporaryDirectory(prefix="boostA-") as tmp:
            for f in folders:
                extract(head, f, tmp)
            for rel, blob in (blobs or {}).items():
                if rel.startswith(("/", "..")) or "/../" in rel or not re.fullmatch(r"[0-9a-f]{40}", str(blob)):
                    raise ValueError(f"이상한 코드 판 {rel}")
                q = Path(tmp) / rel
                q.parent.mkdir(parents=True, exist_ok=True)
                q.write_bytes(git("cat-file", "-p", blob, text=False))
            Path(tmp, "payload.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "CAPS_ADJ"}          # 작업 흐름과 같게(시총 고침 끔)
            out = subprocess.run([sys.executable, "-c", DRIVER, tmp, str(CODE_ROOT), task_name], cwd=tmp, env=env,
                                 capture_output=True, text=True, timeout=900)
            if out.returncode != 0:
                raise RuntimeError(out.stderr.strip().splitlines()[-1] if out.stderr.strip() else "끝 상태 ≠ 0")
            return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception as e:
        ERRS.append(f"하위 작업 {task_name} 실패 · {type(e).__name__} · {str(e)[:80]}")
        return None


def task(name, p):
    """하위 작업 안에서 도는 셈(cwd = 꺼낸 자료 폴더)."""
    if name == "replay":
        same, _, why = replay(p["bot"], p["body"])
        return {"same": same, "why": why}
    if name == "basket_inputs":
        import basket_live as BL
        import study
        react, inside = BL.reactions(study.load_prices(), p["t0"], p["before"])
        return {"react": A.plain(react), "inside": A.plain(inside),
                "events": A.plain(BL.todays_events(BL.load_events(), p["t0"], p["before"]))}
    raise ValueError(name)


# ───────────────────────── ① 재현 ─────────────────────────

def replay(bot, body):
    """(같음 여부, 다시 낸 결과, 까닭) — 지금 불러온 코드로. 물은 적 없는 질문 · 같은 질문에 다른 답이면 재현 실패."""
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
    except Exception as e:                          # 재현 중 오류도 재현 실패(감사가 멈추지 않게)
        return False, None, f"재현 중 오류 · {type(e).__name__}"
    same = A.canon(got) == A.canon(body.get("결과"))
    return same, A.plain(got), "같음" if same else "다름"


def replay_any(bot, body):
    """기록한 코드 판으로 재현. (같음 · 다름 · None = 코드 판을 못 꺼냄(불완전), 까닭)."""
    rec = body.get("코드")
    if not isinstance(rec, dict) or not rec or any(not v for v in rec.values()):
        return False, "기록 고장(코드 판 없음)"
    now = {p: A.safe(lambda p=p: A.blob_id(CODE_ROOT / p)) for p in rec}
    if now == rec:
        same, _, why = replay(bot, body)
        return same, why
    got = run_at("replay", {"bot": bot, "body": body}, blobs=rec)
    if got is None:
        return None, "기록한 코드 판으로 재현 못 함(불완전)"
    return got["same"], got["why"] + "(기록한 코드 판)"


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


# ───────────────────────── ② 입력 ─────────────────────────

def etf_rows(folder, code, sort=True):
    """etf-data 종가 줄. sort=True는 덧붙임 closes()와 같게(날짜 차례) · False는 엔진 history()와 같게(파일 차례 그대로)."""
    try:
        body = json.loads((folder / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ERRS.append(f"{folder}/{code}.json 읽기 실패")
        return []
    rows = [(str(d), float(c)) for d, c in body.get("closes", []) if c]
    return sorted(rows) if sort else rows


def inputs_check(bot, body, cal, ctx):
    """(문제 [(꼬리표, 글)], 참고 [글]). ctx: 감사 끝점의 공시 자료(main_events) · 바구니 하위 작업 함수(basket_inputs)."""
    day, i, x = body["날"], body.get("입력") or {}, body.get("곁") or {}
    pd = prev_day(cal, day)
    head = body.get("판단 때 저장소 HEAD")
    out, info = [], []
    if not head:
        out.append(("기록 고장", "판단 때 저장소 HEAD 기록 없음"))
    if bot == "daily":
        asof = x.get("data_asof")
        if not isinstance(asof, dict):
            out.append(("기록 고장", "일봉 자료 날짜 칸 없음"))
        elif asof.get("today_or_later") or (asof.get("max") and asof["max"] >= day):
            out.append(("미래", f"판단 날 이상 일봉 줄 {asof.get('today_or_later')}종목 · 마지막 {asof.get('max')}"))
        if x.get("expect") != pd:
            out.append(("LATE_INPUT", f"증권사 기대일 {x.get('expect')} · 감사 달력 어제 거래일 {pd}"))
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
        folder = folder_at(head, "etf-data") if head else None
        lens = (x.get("px_len") or {}) if folder is not None else {}
        for code, n in lens.items():
            rows = [(d, c) for d, c in etf_rows(folder, code, sort=False) if d < day]      # idle_live.history와 같은 길
            now = (i.get("now_price") or {}).get(code)
            full = [c for _, c in rows] + [now]
            tail = (i.get("px") or {}).get(code) or []
            same = now is not None and len(full) == n and A.digest(np.array(full, float)) == (x.get("px_digest") or {}).get(code) \
                and A.canon(full[-len(tail):] if tail else []) == A.canon(tail)
            if not same:
                out.append(("재현", f"{code} 가격 이력을 판단 때 판으로 다시 만들면 다름"))
    elif bot == "overlay":
        import overlay_live as O
        rows_last = i.get("rows_last") or []
        last = rows_last[-1][0] if rows_last else None
        if last and last >= day:
            out.append(("미래", f"KODEX 200 종가 줄 마지막 {last} ≥ 판단 날"))
        elif i.get("stale") or last != pd:
            out.append(("LATE_INPUT", f"KODEX 200 마지막 {last or '-'} · 어제 거래일 {pd}(맞추지 않음)"))
        folder = folder_at(head, "etf-data") if head else None
        if folder is not None:
            rows = [r for r in etf_rows(folder, O.SIGNAL) if r[0] < day]
            if A.digest(rows) != x.get("rows_digest"):
                out.append(("재현", "KODEX 200 종가 줄을 판단 때 판으로 다시 만들면 다름"))
            elif rows and not i.get("stale") and O.states(rows)[rows[-1][0]] != i.get("state"):
                out.append(("재현", "국면을 다시 셈하면 다름"))
    elif bot == "basket":
        import basket_live as BL
        tail = x.get("days_tail") or []
        if i.get("t0") != pd:
            out.append(("LATE_INPUT", f"t0 {i.get('t0')} · 어제 거래일 {pd}"))
        want = [d for d in cal if d < day][-(len(tail) - 1):] + [day] if len(tail) > 1 else [day]
        if tail != want:
            out.append(("LATE_INPUT", "거래일 목록이 감사 달력과 다름(날짜 셈이 어긋날 수 있음)"))
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
            got = ctx["basket_inputs"](head, i["t0"], x["before"])
            if got is not None:
                for k, rec in (("react", i.get("react")), ("inside", i.get("inside")), ("events", i.get("events_t0"))):
                    if A.canon(got[k]) != A.canon(rec):
                        out.append(("재현", f"바구니 {k}를 판단 때 판으로 다시 셈하면 다름"))
            try:
                ct = git("log", "-1", "--format=%ct", head, "--", "event-data").strip()
                at = datetime.fromtimestamp(int(ct), KST).strftime("%Y%m%d%H%M") if ct else None
            except (RuntimeError, ValueError):
                ERRS.append(f"{day}:basket 공시 수집 시각 읽기 실패")
                at = None
            if at is not None and at < i["t0"] + EVENTS_DUE:
                out.append(("LATE_INPUT", f"판단 앞 마지막 공시 수집 {at[:8]} {at[8:]} · t0 수집 예정 {i['t0']} {EVENTS_DUE} 전"))
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
            extract(commit, "event-data", tmp)
            return BL.load_events(folder=str(Path(tmp) / "event-data"))
    except Exception as e:
        ERRS.append(f"끝점 공시 자료 꺼내기 실패 · {type(e).__name__}")
        return {}


# ───────────────────────── ③ 때 · ⑤ 증권사 · 주문 대조 ─────────────────────────

def hhmm(body):
    return (body.get("기록 시각(한국)") or "")[11:16].replace(":", "")


def timing(bot, body):
    """(문제, 참고). 늦어 주문을 못 낸 것은 부른 까닭과 상관없이 SCHEDULER(설명 필요)."""
    out, info = [], []
    t, res, x = hhmm(body), body.get("주문 결과") or {}, body.get("곁") or {}
    late = res.get("late") if "late" in res else (x.get("late_at_decision") if bot == "engine" else x.get("late"))
    ev = body.get("부른 까닭")
    if late or not t or t > DEADLINE[bot]:
        out.append(("SCHEDULER", f"기록 {t or '-'} · 주문 마감 {DEADLINE[bot]} 넘음(주문 못 냄 · 부른 까닭 {ev or '작업 흐름 밖'})"))
    if t and t < START[bot]:
        out.append(("SCHEDULER", f"기록 {t} · 판단 시각 {START[bot]} 전"))
    if ev != "schedule":
        info.append(f"MANUAL · 부른 까닭 {ev or '작업 흐름 밖'}")
    return out, info


def book_rows(body):
    """오늘 장부 주문(봇 장부에 적힌 그날 주문 · 자리 내주기 · 비켜 두기 · 흔들림 덜어내기 포함) + 덧붙임 접수 결과."""
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


# ───────────────────────── ④ 장부 · ⑥ 겹침 ─────────────────────────

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


def new_buys(bot, body):
    """그 판단에 새로 사기가 있었는지(G1 '입력 시각 문' 그림자 셈용 · 보고만)."""
    out = body.get("결과") or {}
    if bot in ("engine", "basket"):
        return any(len(o) > 1 and o[1] == "buy" for o in out.get("orders", []))
    if bot == "overlay":
        return bool(out.get("rebalance")) and any(o[1] == "buy" for o in (body.get("주문 결과") or {}).get("orders") or [])
    return bool(out.get("buys"))


# ───────────────────────── 하루 · 기간 ─────────────────────────

def explained(causes, key, tag):
    e = (causes.get(key) or {}).get(tag)
    if tag in MISSING:
        return isinstance(e, dict) and e.get("원인") in CODES and bool(EVIDENCE.search(str(e.get("근거", ""))))
    if isinstance(e, dict):
        e = e.get("근거")
    return bool(e) and bool(EVIDENCE.search(str(e)))


def audit(start, end, causes=None, end_commit="HEAD"):
    try:
        return _audit(start, end, causes, end_commit)
    finally:                                          # 꺼낸 임시 폴더는 셈이 끝나면 지움(디스크)
        for p in _FOLDERS.values():
            shutil.rmtree(p.parent, ignore_errors=True)
        _FOLDERS.clear()


def _audit(start, end, causes, end_commit):
    global END
    ERRS.clear()
    _FOLDERS.clear()
    try:
        END = git("rev-parse", "--verify", f"{end_commit}^{{commit}}").strip()
    except RuntimeError:
        ERRS.append(f"끝점 커밋 {end_commit}을 못 읽음")
        return {"요약": {"기간": [start, end], "끝점 커밋": None, "불완전": list(ERRS), "판정": "불완전(다시 셈)"}, "줄들": []}
    cal = calendar()
    found = receipts(start, end)
    days = sorted({d for d in cal if start <= d <= end} | {d for d, _ in found})
    ctx = {"main_events": main_events_at(END),
           "basket_inputs": lambda head, t0, before: run_at("basket_inputs", {"t0": t0, "before": before}, head=head,
                                                             folders=("price-data", "share-data", "event-data"))}
    causes = causes or {}
    rows, fails, needs = [], [], []
    for bot in BOTS:
        prev_commit = None
        for d in days:
            key = f"{d}:{bot}"
            row = {"날": d, "봇": bot, "문제": [], "참고": []}
            got = found.get((d, bot))
            if got is None:
                eng = found.get((d, "engine"))
                if bot in ("basket", "overlay") and eng and hhmm(eng[1]) > DEADLINE["engine"]:
                    row["문제"].append(("SCHEDULER", f"엔진 기록 {hhmm(eng[1])} · 마감 뒤라 {bot}는 돌지 않음(설계대로)"))
                else:
                    row["문제"].append(("빠짐", "기록 없음"))
            else:
                rel, body = got
                same, why = replay_any(bot, body)
                row["재현"] = why
                if same is False:
                    row["문제"].append(("기록 고장" if why.startswith("기록 고장") else "재현", why))
                if bot == "overlay":
                    ok, why_t = replay_overlay_target(body)
                    row["맞춤 재현"] = why_t
                    if ok is False:
                        row["문제"].append(("재현", "맞춤 " + why_t))
                if "주문 결과" not in body:
                    row["문제"].append(("빠짐", "판단 뒤 기록(주문 결과) 없음"))
                p1, i1 = inputs_check(bot, body, cal, ctx)
                p2, i2 = timing(bot, body)
                vers = versions_of(rel)
                p3, i3, commit = ledger_check(bot, rel, body, prev_commit, vers)
                prev_commit = commit or prev_commit
                row["문제"] += p1 + p2 + broker_check(bot, body) + orders_check(bot, body) + p3 + duplicates(vers)
                row["참고"] += i1 + i2 + i3
                row["기록 시각"], row["부른 까닭"] = body.get("기록 시각(한국)"), body.get("부른 까닭")
                row["G1 문이면 달라짐"] = any(t == "LATE_INPUT" for t, _ in row["문제"]) and new_buys(bot, body)
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
    n_cells = len(days) * len(BOTS)
    strain = sum(1 for r in rows for t, _ in r["문제"] if t == "SCHEDULER" or t in MISSING)
    orders = [o for r in rows for o in r.get("주문", [])]
    summary = {
        "기간": [start, end], "끝점 커밋": END, "거래일": len(days), "기록 수": f"{len(found)}/{n_cells}",
        "꼬리표 수": {c: sum(1 for r in rows for t, _ in r["문제"] if t == c) for c in CODES + MISSING + HARD},
        "즉시 실패": fails, "설명 안 된 꼬리표": needs, "불완전": list(ERRS),
        "손으로 부른 기록": sum(1 for r in rows if r.get("부른 까닭") not in (None, "schedule") and "기록 시각" in r),
        "주문 접수율": f"{sum(1 for o in orders if o[2].startswith('접수'))}/{len(orders)}",
        "실행 보강 필요": bool(n_cells) and strain / n_cells > STRAIN,
        "G1 그림자(보고만)": {"늦은 입력 판단": sum(1 for r in rows if any(t == "LATE_INPUT" for t, _ in r["문제"])),
                           "그중 새로 산 판단(문이면 안 샀을 것)": sum(1 for r in rows if r.get("G1 문이면 달라짐"))},
        "기준 ① · ②": "월 점검 셈(tools/bt_mix54.py · reconcile)으로 따로 보고(이 셈 밖)",
        "판정": ("실패" if fails else "불완전(다시 셈)" if ERRS else "진행 중" if len(days) < 20
                 else "통과" if not needs else "설명 필요")}
    return {"요약": summary, "줄들": rows}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", required=True)
    ap.add_argument("--to", dest="end", required=True)
    ap.add_argument("--causes", default=str(CODE_ROOT / "research" / "boost_a" / "causes.json"))
    ap.add_argument("--out", default=str(CODE_ROOT / "research" / "boost_a"))
    ap.add_argument("--end-commit", default="HEAD")
    a = ap.parse_args(argv)
    cpath = Path(a.causes)
    causes = json.loads(cpath.read_text(encoding="utf-8")) if cpath.is_file() else {}
    res = audit(a.start, a.end, causes, end_commit=a.end_commit)
    res["요약"]["설명 파일 지문"] = A.file_digest(cpath) if cpath.is_file() else None
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"audit-{a.end}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    s = res["요약"]
    print(f"BOOST-0001-A 감사 {a.start} ~ {a.end} · 끝점 {str(s.get('끝점 커밋'))[:12]} · 거래일 {s.get('거래일')} · "
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
