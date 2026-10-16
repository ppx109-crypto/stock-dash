"""세 판 '하위 %' 덧붙임 글(사용자 2026-10-16 "매일 발송 글에 하위 % 넣어줘").

- 잠긴 daily3.py(sha256 74260101…)는 바꾸지 않고, 그 결과(history.json) 뒤에 짧은 글을 하나 더 보냄.
- 과거 기준: 개발 기간 183일(01-08 ~ 10-12) 날별 손익 — parts1_out.json(신뢰형 · 균형형) · split1_out.json(v12a 4봇).
  만들 때 본 자료라 과거가 실제보다 좋게 나올 수 있음(글에 적음).
- 오늘 · 최근 4 · 10 · 20거래일 합이 과거 같은 길이 구간 가운데 하위 몇 %인지(같거나 나쁜 구간 비율).
  10 · 20일 합에는 10-12까지의 개발 기간 날이 섞임. 하위 10% 이하면 '약세'.
- --send 이면 discord-send.yml로 보냄. 계좌 금액 · 번호 없음 · 규칙 값 없음.
"""
import json
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
SCR = D.parents[1]
REPO = "/home/user/stock-dash"


def series():
    po = json.load(open(SCR / "parts1_out.json"))
    so = json.load(open(SCR / "split1_out.json"))["판별 날별"]
    T, B = po["후보"]["T"], po["후보"]["B"]
    base = T["VT1+P2T-e"]["날별"]
    return {"신뢰형": {d: base[d] + B["P2R"]["날별"][d] for d in base},
            "균형형": {d: T["VT1+P2T-e+VE+VT2+M12_s1.0"]["날별"][d] + B["VR+P2R"]["날별"][d] for d in base},
            "v12a 4봇": so["대조 v12a"]}


def roll(x, n):
    return [sum(x[i - n + 1:i + 1]) for i in range(n - 1, len(x))]


def main(send):
    ref = series()
    H = json.load(open(D / "history.json"))
    last = H["last"]
    lines = [f"📐 세 판 하위 % {last[4:6]}-{last[6:]} (과거 개발 183일 같은 길이 구간 대비 · 낮을수록 나쁨)"]
    weak = []
    for k, r in ref.items():
        hd = sorted(r)
        hist = [r[d] for d in hd]
        live = [H["days"][k][d] for d in sorted(H["days"][k]) if d > hd[-1]]
        ser = hist + live
        parts = []
        for n, name in ((1, "오늘"), (4, "4일"), (10, "10일"), (20, "20일")):
            cur = sum(ser[-n:])
            past = roll(hist, n)
            pct = sum(1 for p in past if p <= cur) / len(past) * 100
            parts.append(f"{name} {cur:+.2f}p 하위 {pct:.0f}%")
            if pct <= 10:
                weak.append(k)
        lines.append(f"· {k}: " + " · ".join(parts))
    weak = list(dict.fromkeys(weak))
    lines.append(f"⚠️ 약세(하위 10% 이하): {' · '.join(weak)}" if weak else "약세 없음(모두 하위 10% 위)")
    lines.append("(과거는 만들 때 본 자료라 실제보다 좋게 나올 수 있음 · 10 · 20일 합에는 10-12까지 개발 날 포함)")
    text = "\n".join(lines)[:1900]
    (D / "pct_message.txt").write_text(text, encoding="utf-8")
    print(text)
    if send:
        body = D / "pct_dispatch.json"
        json.dump({"ref": "main", "inputs": {"text": text}}, open(body, "w"), ensure_ascii=False)
        r = subprocess.run(["gh", "api", "--method", "POST",
                            "repos/ppx109-crypto/stock-dash/actions/workflows/discord-send.yml/dispatches",
                            "--input", str(body)], capture_output=True, text=True, cwd=REPO)
        print("보내기 요청", "성공" if r.returncode == 0 else "실패 " + r.stderr[:200])
        return 0 if r.returncode == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--send" in sys.argv))
