"""한투 접근토큰을 작업끼리 같이 쓰게 하는 보관함(사용자 2026-10-05 "출입증을 하루 한 번만 받아서 같이 쓰도록").
저장소가 공개라 토큰을 그냥 Actions 캐시에 두지 않음 → GitHub Secrets의 앱 시크릿에서 만든 열쇠로 잠가서(openssl AES-256 · pbkdf2) 넣음.
비밀값이 없는 작업(포크의 PR 등)은 꺼내도 풀 수 없음. 토큰 · 키 · 계좌는 화면에 찍지 않음.
open  : 캐시에서 꺼낸 잠긴 파일을 풀어 $RUNNER_TEMP/kis-token.json · kis-paper-token.json에 둠(없거나 못 풀면 그냥 넘어감 → 봇이 새로 받음)
close : 그 파일이 새로 생기거나 바뀌었으면 다시 잠가 보관함에 넣고 changed=true를 남김(그때만 캐시에 저장)"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

TEMP = Path(os.environ.get("RUNNER_TEMP", "/tmp"))
BOX = TEMP / "kis-token-box"
SEEN = TEMP / "kis-token-seen"
ITEMS = (("kis-token", "REAL_SECRET"), ("kis-paper-token", "PAPER_SECRET"))


def _pass(secret):
    return hashlib.sha256(("kis-token-box:" + secret).encode()).hexdigest()


def _run(args, secret):
    env = {**os.environ, "BOX_PASS": _pass(secret)}
    return subprocess.run(["openssl", "enc", *args, "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-pass", "env:BOX_PASS"],
                          env=env, capture_output=True).returncode == 0


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def open_box():
    SEEN.mkdir(parents=True, exist_ok=True)
    for name, var in ITEMS:
        secret = os.environ.get(var, "")
        enc, plain = BOX / f"{name}.enc", TEMP / f"{name}.json"
        if secret and enc.exists() and not plain.exists():
            if _run(["-d", "-in", str(enc), "-out", str(plain)], secret):
                os.chmod(plain, 0o600)
                print(f"{name}: 보관함에서 꺼냄")
            else:
                plain.unlink(missing_ok=True)
                print(f"{name}: 풀지 못함(새로 받음)")
        (SEEN / name).write_text(_digest(plain))


def close_box():
    changed = False
    BOX.mkdir(parents=True, exist_ok=True)
    for name, var in ITEMS:
        secret = os.environ.get(var, "")
        plain = TEMP / f"{name}.json"
        before = (SEEN / name).read_text() if (SEEN / name).exists() else ""
        if secret and plain.exists() and _digest(plain) != before:
            if _run(["-salt", "-in", str(plain), "-out", str(BOX / f"{name}.enc")], secret):
                changed = True
                print(f"{name}: 새 토큰을 잠가 보관함에 넣음")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    {"open": open_box, "close": close_box}[sys.argv[1]]()
