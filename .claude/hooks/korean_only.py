#!/usr/bin/env python3
"""한국어만 쓰기 자동 검사(사용자 2026-10-16 "영어로 자꾸 답변하는 이유 확인하고 한국말로만 나오게해줘").
원인: 클로드의 생각 과정이 영어라, 긴 작업 중 화면에 보이는 안내 · 답에 영어 문장이 새어 나옴. 지침만으로는 못 막아 자동 검사를 둠.
- Stop(답을 끝낼 때): 이번 차례에 쓴 글에 영어 문장 줄이 있으면 끝내지 못하게 막고 "한국어로 다시 써라"를 돌려줌(같은 차례 두 번째는 통과 · 끝없는 되풀이 방지).
- PostToolUse(도구를 쓴 뒤): 바로 앞 안내 글이 영어면 다음 글에서 한국어로 바로잡으라는 알림을 붙임(한 글에 한 번).
영어 문장 줄 = 코드 · 경로 · 주소 · 식별자(숫자 · _ · 대문자만)를 뺀 뒤, 한글이 하나도 없고 영어 단어가 5개 이상인 줄."""
import hashlib
import json
import os
import re
import sys

HANGUL = re.compile(r"[가-힣]")
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]+")
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".korean_only_seen")


def clean(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\S*[/\\]\S*", " ", text)                      # 경로
    text = re.sub(r"\b\S*[_0-9]\S*\b", " ", text)                  # 식별자 · 숫자 섞인 말
    return text


def english_lines(text):
    out = []
    for line in clean(text).splitlines():
        words = [w for w in WORD.findall(line) if not w.isupper()]
        if len(words) >= 5 and not HANGUL.search(line):
            out.append(line.strip()[:80])
    return out


def turn_texts(path):
    """이번 차례(마지막 사용자 글 뒤)의 클로드 글 조각들."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for l in fh:
            try:
                rows.append(json.loads(l))
            except ValueError:
                continue
    texts = []
    for d in reversed(rows):
        m = d.get("message") or {}
        c = m.get("content")
        if d.get("type") == "user":
            if isinstance(c, str) or (isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "text" for b in c)):
                break
            continue
        if d.get("type") == "assistant" and isinstance(c, list):
            for b in reversed(c):
                if isinstance(b, dict) and b.get("type") == "text":
                    texts.append(b.get("text") or "")
    return list(reversed(texts))


def main():
    try:
        inp = json.load(sys.stdin)
    except ValueError:
        return
    path = inp.get("transcript_path")
    if not path or not os.path.exists(path):
        return
    texts = turn_texts(path)
    ev = inp.get("hook_event_name")
    if ev == "Stop":
        if inp.get("stop_hook_active"):
            return
        bad = [x for t in texts for x in english_lines(t)]
        if bad:
            print(json.dumps({"decision": "block", "reason": "사용자 지침 위반: 화면에 보이는 글에 영어 문장이 있습니다 → 같은 내용을 한국어로만 다시 쓰세요"
                              f"(필요 없으면 생략). 걸린 줄: {bad[:3]}"}, ensure_ascii=False))
    elif ev == "PostToolUse" and texts:
        last = texts[-1]
        bad = english_lines(last)
        h = hashlib.sha256(last.encode()).hexdigest()[:16]
        seen = set(open(STATE).read().split()) if os.path.exists(STATE) else set()
        if bad and h not in seen:
            with open(STATE, "a") as f:
                f.write(h + "\n")
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext":
                              f"사용자 지침 위반: 바로 앞 안내가 영어였습니다({bad[:2]}). 다음 글에서 한국어로 바로잡고, 앞으로 화면에 보이는 글은 한국어로만 쓰세요."}},
                             ensure_ascii=False))


if __name__ == "__main__":
    main()
