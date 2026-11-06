"""판단 기록장(관측 전용 · BOOST-0001-A · 사용자 2026-11-06 "네, 기록 추가").

봇이 판단 함수에 넣은 입력과 나온 결과를 그대로 적어 둡니다. 나중에 같은 입력으로 다시 돌려
같은 결정이 나오는지(재현) · 입력이 제때 들어왔는지 · 장부가 이어지는지를 감사할 수 있게 합니다.
- 사고파는 규칙 · 금액 · 주문은 바꾸지 않습니다. 봇은 기록 식을 모두 `safe(lambda: ...)` 안에서만 평가하고
  `_audit`가 없으면(불러오기 실패) 기록을 건너뜁니다 → 기록이 실패해도 매매는 멈추지 않습니다(tests/test_audit_log.py 구조 검사).
- 키 · 계좌번호 · 증권사 응답 본문은 적지 않습니다. 적는 것은 봇이 이미 계산한 숫자 · 목록 · 작업 정보뿐입니다.
- 파일: <봇 장부 폴더>/audit/<날>-<봇>.json (장부 폴더를 따라가므로 시험 때는 시험의 임시 폴더에 생김).
"""
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
PX_TAIL = 130        # 엔진 가격 이력은 끝 130개만 적음(판단이 읽는 것은 끝 62개까지 · 전체 길이 · 지문은 따로 적음)
DAYS_TAIL = 250      # 바구니 거래일 목록도 끝 250개만(날짜 셈 답은 따로 다 적음)
_HEAD = {}


def plain(x):
    """JSON으로 바꿀 수 있는 꼴로(숫자는 반올림하지 않음 · nan은 실수 그대로 · 모음은 정렬 · 넘파이 값은 파이썬 값)."""
    try:
        import numpy as np
        if isinstance(x, np.ndarray):
            return [plain(v) for v in x.tolist()]
        if isinstance(x, np.generic):
            return plain(x.item())
    except ImportError:
        pass
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, (set, frozenset)):
        return sorted((plain(v) for v in x), key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
    if isinstance(x, Path):
        return str(x)
    if x is None or isinstance(x, (bool, int, float, str)):
        return x
    return repr(x)


def canon(obj):
    """비교 · 지문용 한 줄 글(nan은 NaN 글자로 같게 · 열쇠 차례 무관)."""
    return json.dumps(plain(obj), sort_keys=True, ensure_ascii=False)


def digest(obj):
    try:
        return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()
    except Exception:                           # 지문을 못 떠도 매매는 그대로
        return None


def file_digest(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def blob_id(path):
    """git 블롭 id(그 파일 내용 그대로) — 감사가 git에서 같은 판의 코드를 꺼내 재현."""
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def file_ids(*paths):
    """불러온 모듈 파일들의 블롭 id {저장소 기준 경로: id}. 봇은 모듈을 불러올 때 한 번 부름(그때 판 = 실제로 도는 코드)."""
    out, top = {}, Path(__file__).resolve().parent          # audit_log.py는 저장소 맨 위에 있음 → 지금 폴더와 상관없이 같은 경로
    for p in paths:
        try:
            rel = os.path.relpath(os.path.abspath(p), top).replace(os.sep, "/")
        except Exception:
            rel = str(p)
        try:
            out[rel] = blob_id(p)
        except Exception:
            out[rel] = None
    return out


def safe(fn, default=None):
    """기록 식을 여기서만 평가(인자 만들기에서 난 예외까지 삼킴 · 한 줄만 찍음)."""
    try:
        return fn()
    except Exception as e:
        print("판단 기록 실패(매매는 그대로) ·", type(e).__name__)
        return default


def capture(inputs):
    """판단 함수를 부르기 **앞에** 입력을 떠 둠(함수가 입력을 바꿔도 기록은 그대로)."""
    return plain(inputs)


def _head():
    """판단 때 저장소 HEAD(작업마다 한 번 · 판단 직전 저장소 맞추기 뒤에 처음 부름)."""
    cwd = os.getcwd()
    if cwd not in _HEAD:
        try:
            out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=3)
            _HEAD[cwd] = out.stdout.strip() or None
        except Exception:
            _HEAD[cwd] = None
    return _HEAD[cwd]


def meta():
    return {"기록 시각(한국)": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
            "작업 번호": os.getenv("GITHUB_RUN_ID"), "작업 시도": os.getenv("GITHUB_RUN_ATTEMPT"),
            "부른 까닭": os.getenv("GITHUB_EVENT_NAME"), "작업 코드 커밋": os.getenv("GITHUB_SHA"),
            "판단 때 저장소 HEAD": _head()}


def path_for(state_path, day, bot):
    return Path(state_path).parent / "audit" / f"{day}-{bot}.json"


def _write(p, body):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


def record(state_path, day, bot, inputs, outputs, ledgers=(), extra=None, code=None):
    """판단 하나를 적음. inputs = capture()로 판단 앞에 떠 둔 것 · ledgers = 판단 앞 장부 파일들(지문만) · code = 불러온 코드 판."""
    try:
        body = {"날": day, "봇": bot, **meta(), "코드": code, "입력": inputs, "결과": plain(outputs),
                "입력 지문": digest(inputs), "결과 지문": digest(outputs),
                "장부 지문(판단 앞)": {str(p): file_digest(p) for p in ledgers}}
        if extra is not None:
            body["곁"] = plain(extra)
        p = path_for(state_path, day, bot)
        _write(p, body)
        return p
    except Exception as e:
        print("판단 기록 실패(매매는 그대로) ·", type(e).__name__)
        return None


def today_orders(book_path, day):
    """주문 장부에서 열쇠가 그날로 시작하는 줄(자리 내주기 · 비켜 두기 · 흔들림 덜어내기 포함)."""
    b = json.loads(Path(book_path).read_text(encoding="utf-8")) if Path(book_path).exists() else {}
    return [o for o in (b.get("orders") or []) if isinstance(o, dict) and str(o.get("key", "")).startswith(day)]


def after(state_path, day, bot, outcome, ledgers=(), books=()):
    """주문 결과 · 판단 뒤 장부 지문 · 오늘 장부 주문(books)을 같은 기록에 덧붙임."""
    try:
        p = path_for(state_path, day, bot)
        body = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"날": day, "봇": bot, **meta()}
        body["주문 결과"] = plain(outcome)
        body["장부 지문(판단 뒤)"] = {str(q): file_digest(q) for q in ledgers}
        got = {}
        for b in books:                         # 장부 하나를 못 읽어도 나머지 기록은 그대로 남김
            try:
                got[str(b)] = plain(today_orders(b, day))
            except Exception as e:
                got[str(b)] = f"읽기 실패 · {type(e).__name__}"
        if books:
            body["오늘 장부 주문"] = got
        body["덧붙인 시각(한국)"] = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        _write(p, body)
        return p
    except Exception as e:
        print("판단 기록 덧붙이기 실패(매매는 그대로) ·", type(e).__name__)
        return None


def recorder(fn, calls):
    """함수 인자(예: 1일봉 kin_ok)를 감싸 물어본 질문과 답을 calls에 적음 · 답 · 예외는 원래 함수 그대로."""
    def wrapped(*args):
        r = fn(*args)
        try:
            calls.append([plain(a) for a in args] + [plain(r)])
        except Exception:
            pass
        return r
    return wrapped


def price_asof(prices, day):
    """1일봉 일봉 자료의 실제 날짜(증권사 기대일이 아니라 자료 자체): 종목별 마지막 날의 최댓값 · 판단 날 이상인 종목 수."""
    lasts = [str(v["rows"][-1][0]) for v in prices.values() if v.get("rows")]
    return {"max": max(lasts) if lasts else None, "today_or_later": sum(d >= day for d in lasts), "codes": len(lasts)}


def etf_asof(codes, day, folder="etf-data"):
    """엔진 ETF 종가 자료의 실제 날짜: 판단에 쓴(판단 날 앞) 마지막 날 · 파일에 있는 판단 날 이상 줄 수(엔진은 거름)."""
    out = {}
    for c in codes:
        rows = json.loads((Path(folder) / f"{c}.json").read_text(encoding="utf-8")).get("closes", [])
        used = [str(d) for d, v in rows if v and str(d) < day]
        out[c] = {"last": max(used) if used else None, "today_or_later": sum(1 for d, v in rows if v and str(d) >= day)}
    return out
