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
    out = [f"📊 **A그룹 {day}** · {len(picks)}종목 · 폭 {found.get('breadth', '-')}%"]
    for one in picks:
        out.append(f"• {one.get('name')} · {'·'.join(one.get('갈래') or [])} · {_won(one.get('종가'))}")
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
        return f"{icon} 자리 바꾸기 {_name(text)} → {to.group(1).strip() if to else '?'}" + (f" ({gain.group(1)})" if gain else "")
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
        return (f"✅ {m.group(1)} {_name(body)}" + (f" {slot.group(1)}칸" if slot else "")
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
        code = re.search(r"([A-Z0-9]{6,10})\.?$", status)
        tail = (" ✅" + (" (살 수 있는 만큼으로 줄임)" if "줄임" in status else "")) if ok else (" ❌ 거절" + (f"({code.group(1)})" if code else ""))
        return f"🧪 {m.group(2)} {name}" + (f" {qty.group(1)}주" if qty else "") + tail
    m = re.match(r"🧪 모의투자\(([^)]*)\) (매수|매도) 건너뜀 · (.+)$", line)
    if m:
        return f"⏭️ {m.group(2)} {_name(m.group(3))} 건너뜀({m.group(3).split(' · ')[-1]})"
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
    msg, found = "", []
    for row in rows:
        if len(msg) + len(row) + 1 > LIMIT:
            found.append(msg)
            msg = ""
        msg += row + "\n"
    if msg:
        found.append(msg)
    return found


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
    for msg in chunks(lines(found)):
        try:
            r = requests.post(url, json={"content": msg}, timeout=(10, 20))
        except requests.RequestException:
            print("디스코드에 보내지 못했습니다(연결 오류).")
            return 1
        if r.status_code >= 300:
            print(f"디스코드가 받지 않았습니다 · HTTP {r.status_code}")
            return 1
    print("디스코드로 보냈습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
