"""MPOS-0024 무성과 단계 영수증(GPT #455 판 3 답 5): 코드 · 설계 · 입력 지문 + 실행 명령 + 시험별 결과(기대 · 실제) + 결함 넣기 + 배관 점검.
DESIGN.md는 PR 폴더(research-exchange/claude-to-gpt/MPOS-0024/)에 있으므로 그 지문은 PR 갈래에서 넣음(EX_DESIGN 환경 변수 경로)."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


steps = {}
for name, cmd in (("합성 시험", ["python3", "self24.py"]), ("결함 넣기", ["python3", "mut24.py"]), ("배관 점검", ["python3", "plumb24.py"])):
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    steps[name] = {"명령": " ".join(cmd) + "  (폴더 research/husd)", "끝 상태": r.returncode}
self_out = json.load(open(HERE / "self24_out.json"))
mut = json.load(open(HERE / "mut24_out.json"))
plumb = json.load(open(HERE / "plumb24_out.json"))
code = {f: sha(HERE / f) for f in ("sleeve.py", "self24.py", "mut24.py", "plumb24.py", "receipt24.py")}
if os.environ.get("EX_DESIGN"):
    code["DESIGN.md"] = sha(os.environ["EX_DESIGN"])
rec = {"코드 · 설계 지문": code, "입력 지문": {"cash_path_base.json": sha(HERE / "cash_path_base.json")},
       "파이썬": sys.version.split()[0], "단계": steps,
       "합성 시험": {"PASS": sum(x["판정"] == "PASS" for x in self_out["행"]), "전체": len(self_out["행"]), "행": self_out["행"],
                 "허용 오차": "금액 비교 1e−12 ~ 1e−15(NAV 단위) · 자금 불능 판정 문턱 slack + K < −1e−10"},
       "결함 넣기": {"잡힘": sum(v["잡힘"] for v in mut.values()), "전체": len(mut), "행": mut},
       "배관 점검(실제 BASE 경로 + 상수 값 · 성과 아님)": plumb,
       "판정 구분": "합성 시험 PASS = 엔진이 기대대로 셈(반례에서 FUNDING_INFEASIBLE을 잡음 포함) · 후보 자금 자격과 다름"}
json.dump(rec, open(HERE / "receipt24.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: rec[k] for k in ("코드 · 설계 지문", "단계")}, ensure_ascii=False, indent=1))
print("합성", rec["합성 시험"]["PASS"], "/", rec["합성 시험"]["전체"], "· 결함", rec["결함 넣기"]["잡힘"], "/", rec["결함 넣기"]["전체"])
sys.exit(0 if all(s["끝 상태"] == 0 for s in steps.values()) and rec["결함 넣기"]["잡힘"] == rec["결함 넣기"]["전체"] else 3)
