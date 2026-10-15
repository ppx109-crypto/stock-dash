"""오늘의 A그룹(study/a_group.json)을 디스코드로 보냅니다.

웹훅 주소는 환경변수 DISCORD_WEBHOOK_URL(GitHub Secrets)로만 받고, 어디에도 찍지 않습니다.
주소가 없으면 아무것도 보내지 않고 조용히 끝납니다. A그룹이 없는 날에도 'A그룹 없음'을 보냅니다(B그룹은 싣지 않음 — 사용자 요청).
"""
import json
import os
import re
import sys
from pathlib import Path

import requests

LIMIT = 1900          # 디스코드 한 메시지 2000자 제한 아래로


def _won(v):
    try:
        return f"{float(v):,.0f}원"
    except (TypeError, ValueError):
        return "-"


def lines(found):
    """A그룹 알림 — 짧게(사용자 2026-10-06 "거두절미하고 요약버전으로 전부"). 자세한 건 대시보드."""
    day = str(found.get("date") or "")
    day = f"{day[4:6]}-{day[6:8]}" if len(day) == 8 else day or "날짜 모름"
    picks = found.get("picks") or []
    out = [f"A그룹 {day}, {len(picks)}종목, 시장 폭 {found.get('breadth', '-')}%"]
    for one in picks:
        out.append(f"{one.get('name')}, {' '.join(one.get('갈래') or [])}, {_won(one.get('종가'))}")
    return out


# ───────── 봇 알림을 짧게(사용자 2026-10-06 "각 시간마다 발송되는 디스코드 내용이 너무 길어 · 거두절미하고 요약버전으로 전부") ─────────
# 디스코드에는 종목 이름 · 칸(주) · 손익만. 종목코드 · 까닭 설명 · 안내문(※)은 뺌(대시보드 · 기록 파일에는 그대로 남음).
_CODE = re.compile(r"\(([0-9A-Z]{6})\)")
_SLOT = re.compile(r"(\d+)칸")
_GAIN = re.compile(r"([+−-]\d+(?:\.\d+)?%)")
_QTY = re.compile(r"([\d,]+)주")


def _name(text):
    """'이름(코드) · …' → 이름."""
    head = text.split(" · ")[0].strip()
    return _CODE.sub("", head).strip()


def short_item(icon, kind, text):
    """1시간봉 · 15분봉 판단 한 줄: '🟢 매수 삼성전자 4칸' · '🔴 손절 X 2칸 −3.1%' · '🔄 자리 바꾸기 A → B'."""
    if kind == "자리 바꾸기":
        to = re.search(r"자리를 ([^(·]+)", text)
        gain = _GAIN.search(text)
        return f"{icon} 자리 바꾸기: {_name(text)} 팔고 {to.group(1).strip() if to else '?'} 사기" + (f" ({gain.group(1)})" if gain else "")
    slot, gain = _SLOT.search(text), _GAIN.search(text)
    return f"{icon} {kind} {_name(text)}" + (f" {slot.group(1)}칸" if slot else "") + (f" {gain.group(1)}" if gain and kind != "매수" else "")


def short_line(line):
    """체결 · 모의 주문 · 그 밖의 줄을 짧게. 모르는 모양이면 종목코드 · 세 번째 마디부터만 뺌."""
    line = line.strip()
    if not line or line.startswith("※"):
        return ""
    m = re.match(r"✅ (매수|매도) 체결 · (.+)$", line)
    if m:
        body = m.group(2)
        slot, gain = _SLOT.search(body), _GAIN.search(body)
        price = re.search(r"([\d,]+원)", body)
        return (f"{m.group(1)} 체결: {_name(body)}" + (f" {slot.group(1)}칸" if slot else "")
                + (f" {gain.group(1)}" if gain and m.group(1) == "매도" else f" {price.group(1)}" if price else ""))
    m = re.match(r"🧪 모의투자\(([^)]*)\) (매수|매도) · (.+)$", line)
    if m:
        seg = m.group(3).split(" · ")
        qty = _QTY.search(seg[0])
        name = re.sub(r"\s*[\d,]+주$", "", _CODE.sub("", seg[0])).strip()
        status = " · ".join(x for x in seg[1:] if x != "시장가")
        ok = "접수" in status and "실패" not in status
        if "자리 내줌" in status:
            name += " (규칙에 자리 내줌)"
        tail = (" 주문 들어감" + (" (살 수 있는 만큼으로 줄임)" if "줄임" in status else "")) if ok else " 주문 거절됨"
        return f"모의 {m.group(2)}: {name}" + (f" {qty.group(1)}주" if qty else "") + tail
    m = re.match(r"🧪 모의투자\(([^)]*)\) (매수|매도) 건너뜀 · (.+)$", line)
    if m:
        return f"모의 {m.group(2)} 건너뜀: {_name(m.group(3))} ({m.group(3).split(' · ')[-1]})"
    parts = [_CODE.sub("", x).strip() for x in line.split(" · ")]
    return " · ".join(parts[:3])


def brief(rows):
    """알림 줄 목록 → 짧은 줄 목록(빈 줄 · 안내문 뺌)."""
    out = []
    for r in rows:
        s = short_line(r) if r else ""
        if s:
            out.append(s)
    return out


def chunks(rows):
    """디스코드 한 메시지 글자 수 안으로 나눔. '※'로 시작하는 안내 줄은 늘 뺌(사용자 2026-10-06 "이런거 다 빼")."""
    msg, found = "", []
    for row in rows:
        if str(row).lstrip().startswith("※"):
            continue
        if len(msg) + len(row) + 1 > LIMIT:
            found.append(msg)
            msg = ""
        msg += row + "\n"
    if msg:
        found.append(msg)
    return found


# ───────── 디스코드 글 다듬기(사용자 2026-10-12 "☆한투 · 모의투자 메시지 앞에 붙여줘 · 영어 다 빼고 · 알기 쉽게 · 이상한 모양 전부 빼") ─────────
# 모든 봇 알림은 보내기 바로 앞에서 tidy()를 거칩니다: 그림 문자 · 꾸밈 기호 · 굵게 표시를 빼고, 영어는 한글로 바꿉니다.
PREFIX = "☆한투"
_PIC = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\u25A0-\u25FF\u2500-\u257F\uFE0F\u200D\u20E3]")
# 종목 이름(LG전자 · NAVER · KODEX 레버리지 등)의 영어는 그대로 둠(사용자 2026-10-12 "종목이 영어는 영어 유지") — 종목이 아닌 영어 낱말만 바꿈
_WORDS = [("ETF", "지수펀드"), ("NAV", "평가액"), ("EMA", "지수 평균선"), ("HTTP", "웹"), ("MIX-0054", "최종 판"), ("MIX54", "최종 판"),
          ("OK", "정상")]
_ERR = re.compile(r"\b[A-Za-z_]*(?:Error|Exception|Timeout|Warning)\b")
_RCODE = re.compile(r"\(?\b[A-Z]{2,}[0-9]{3,}\b\)?")


_KO = [("모의투자(덧붙임)", "레버리지 봇 모의"), ("덧붙임", "레버리지 봇"), ("모의투자(1일봉)", "1일봉 모의"), ("모의투자(15분봉)", "15분봉 모의"),
       ("모의투자(1시간봉)", "1시간봉 모의"), ("모의투자(빈칸 엔진)", "빈칸 엔진 모의"), ("(15:1x 값)", "(장 마감 직전 값)"), ("15:1x", "장 마감 직전")]


def tidy(text):
    """디스코드 한 줄 다듬기 — 그림 문자 · 꾸밈 기호 · 굵게 표시를 빼고, 종목이 아닌 영어 낱말 · 오류 이름 · 거절 코드를 한글로 바꾸거나 뺌(종목 이름의 영어는 그대로)."""
    t = str(text or "")
    if t.lstrip().startswith("※"):
        return ""
    t = t.replace("**", "").replace("__", "").replace("`", "")
    for a, b in _KO:
        t = t.replace(a, b)
    t = re.sub(r"\s*(→|->|⇒)\s*", " 다음 ", t)
    t = t.replace("×", " 곱하기 ").replace("−", "-").replace("–", "-").replace("—", "-")
    t = _PIC.sub("", t)
    t = re.sub(r"[•※☆★|]", "", t)
    t = t.replace("·", ",")
    t = _ERR.sub("오류", t)
    t = _RCODE.sub("", t)
    for a, b in _WORDS:
        t = re.sub(r"(?<![A-Za-z])" + re.escape(a) + r"(?![A-Za-z])", b, t)
    t = re.sub(r"\(\s*\)", "", t)
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r",(\s*,)+", ",", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip(" ,")


def messages(rows, paper=True):
    """알림 줄 목록 → 다듬은 디스코드 메시지 목록. 모의투자 알림이면 메시지마다 맨 앞에 '☆한투'를 붙임."""
    found = []
    for msg in chunks([x for x in (tidy(r) for r in rows) if x]):
        found.append(f"{PREFIX} {msg}" if paper else msg)
    return found


def post(rows, paper=True):
    """디스코드로 보냄(모든 봇이 이것을 씀). 웹훅은 GitHub Secrets의 DISCORD_WEBHOOK_URL에만 있고 어디에도 찍지 않음.
    DISCORD_BUFFER(파일 경로)가 있으면 바로 보내지 않고 그 파일에 모아 둠 → 작업 끝에 flush()로 한 번에 보냄
    (사용자 2026-10-14 "14시34분부터 15시32분까지 비슷한 내용을 여러 번 · 한 번으로 정리해서")."""
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url or not rows:
        return False
    buf = os.environ.get("DISCORD_BUFFER", "").strip()
    if buf and any(str(r).lstrip().startswith("⚠️") for r in rows):
        buf = ""                                        # 급한 경고는 모으지 않고 바로 보냄
    if buf:
        try:
            old = json.loads(Path(buf).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            old = []
        Path(buf).write_text(json.dumps(old + [{"rows": [str(r) for r in rows], "paper": bool(paper)}], ensure_ascii=False),
                             encoding="utf-8")
        return True
    ok = True
    for msg in messages(rows, paper):
        try:
            ok = requests.post(url, json={"content": msg}, timeout=(10, 20)).status_code < 300 and ok
        except requests.RequestException:
            ok = False
    return ok


def flush(buf, head=None):
    """모아 둔 알림을 한 메시지(길면 2000자마다 나눔)로 보내고 파일을 지움. 같은 줄은 한 번만 실음."""
    try:
        got = json.loads(Path(buf).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True                                     # 모은 것이 없음(보낼 것 없음)
    rows, seen, paper = ([head] if head else []), set(), any(x.get("paper", True) for x in got)
    for x in got:
        for r in x.get("rows", []):
            if r not in seen:
                seen.add(r)
                rows.append(r)
    saved = os.environ.pop("DISCORD_BUFFER", None)      # 이번에는 진짜로 보냄
    try:
        ok = post(rows, paper) if len(rows) > (1 if head else 0) else True
    finally:
        if saved is not None:
            os.environ["DISCORD_BUFFER"] = saved
    if ok:
        Path(buf).unlink(missing_ok=True)
    return ok


def main():
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        print("디스코드 웹훅이 설정되지 않아 보내지 않습니다.")
        return 0
    try:
        found = json.loads(Path("study/a_group.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("A그룹 파일을 읽지 못했습니다.")
        return 1
    if os.environ.get("DISCORD_BUFFER", "").strip():   # 저녁 작업도 한 통으로(사용자 2026-10-15 "11시51분 메시지 2개 · 한 번만")
        post(lines(found), paper=False)
        print("A그룹 알림을 모음 파일에 넣었습니다(작업 끝에 한 번에 보냄).")
        return 0
    for msg in messages(lines(found), paper=False):
        try:
            r = requests.post(url, json={"content": msg}, timeout=(10, 20))
        except requests.RequestException:
            print("디스코드에 보내지 못했습니다(연결 오류).")
            return 1
        if r.status_code >= 300:
            print(f"디스코드가 받지 않았습니다 · 응답 {r.status_code}")
            return 1
    print("디스코드로 보냈습니다.")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--flush"]:                   # python notify_discord.py --flush <모음 파일> [머리말]
        sys.exit(0 if flush(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None) else 1)
    sys.exit(main())
