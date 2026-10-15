"""연구 실행 도구(rxkit · 2026-10-15 MPOS-0008 시간 낭비 원인 조치) — 다음 연구부터 공통으로 씀.
원인 → 조치:
 ① 단계 명령을 한 번도 만들어 보지 않고 긴 셈을 돌림 → 실행 오류로 10분 뒤 멈춤   → dry(): 모든 단계의 일감(명령 · 환경 · 출력)을 먼저 다 만들어 보고,
                                                                                     smoke 일감 하나씩을 실제로 짧게 돌려 본 뒤에만 본 셈
 ② 영수증이 코드 파일 전체 지문에 묶여, 셈과 무관한 한 줄 고침에도 처음부터 다시     → 단계마다 '그 단계가 쓰는 파일'만 묶음(stage_code) · 결과 파일 지문은 그대로 검사
 ③ 단계를 차례로만 돌림(자르기 장부는 build만 있으면 되는데 bases 끝까지 기다림)     → run_dag(): 앞 단계가 끝난 일감부터 바로 다음 일감 시작 · 일꾼 = CPU 수
 ④ 판정 코드에 `값 or 숫자`(0을 결측처럼) 같은 함정                                   → lint(): 판정 · 비교 코드의 `or -1e9` · `or 0` 꼴과 dict 중복 열쇠 위험 꼴을 찾아냄
 ⑤ 사전등록을 내기 전 스스로 반대 검토가 없음 → GPT가 설계 결함을 잡을 때까지 왕복   → review_prompt(): 점검표(docs/RESEARCH-SELF-UPGRADE.md §2)로 대리 검토자에게 줄 글을 만듦
"""
import hashlib
import json
import os
import re
import subprocess
import time

CPU = max(1, (os.cpu_count() or 2))


def sha(f):
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# ───────── ② 단계별 코드 묶음 영수증 ─────────
def stage_code(files):
    return {os.path.basename(f): sha(f) for f in files}


def write_receipt(path, code, rows):
    json.dump({"코드": code, "때(한국)": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() + 9 * 3600)), "줄": rows}, open(path, "w"), ensure_ascii=False, indent=1)
    bad = [k for k, v in rows.items() if v.get("판정") != "PASS"]
    return bad


def check_receipt(path, code):
    """없음 · 그 단계 코드 지문 다름 · FAIL · 결과 파일 바뀜 → 까닭 목록(빈 목록이면 통과)."""
    if not os.path.exists(path):
        return ["영수증 없음"]
    r = json.load(open(path))
    why = []
    if r.get("코드") != code:
        why.append("그 단계 코드가 바뀜")
    for k, v in r.get("줄", {}).items():
        if v.get("판정") != "PASS":
            why.append(f"{k} FAIL")
        for f, h in v.get("파일", {}).items():
            if not os.path.exists(f) or sha(f) != h:
                why.append(f"{k} 파일 바뀜/없음")
    return why


# ───────── ③ 의존 순서대로 · 끝나는 대로 다음 일감 ─────────
def run_dag(jobs, workers=CPU, log=print, poll=2.0):
    """jobs: {이름: dict(cmd, env, cwd, out(기록 파일), after=[앞 일감 이름], clean=[시작 전 지울 파일])}.
    앞 일감이 rc 0으로 끝나면 바로 시작 · 앞 일감 실패면 '건너뜀'(rc None). 돌려줌 {이름: rc}."""
    rc, run = {}, {}
    todo = dict(jobs)
    while todo or run:
        for n, j in list(todo.items()):
            if len(run) >= workers:
                break
            deps = j.get("after", [])
            if any(d in rc and rc[d] != 0 for d in deps):
                rc[n] = None
                del todo[n]
                log(f"{n} 건너뜀(앞 일감 실패)")
                continue
            if all(rc.get(d) == 0 for d in deps):
                for f in j.get("clean", []):
                    if os.path.exists(f):
                        os.remove(f)
                fh = open(j["out"], "w")
                run[n] = (subprocess.Popen(j["cmd"], env=j.get("env"), cwd=j.get("cwd"), stdout=fh, stderr=subprocess.STDOUT), fh)
                del todo[n]
        for n, (p, fh) in list(run.items()):
            if p.poll() is not None:
                fh.close()
                rc[n] = p.returncode
                del run[n]
                log(f"{n} rc {p.returncode}")
        if run or todo:
            time.sleep(poll)
    return rc


# ───────── ① 마른 실행 ─────────
def dry(builders, smoke=None, timeout=600, log=print):
    """builders: {단계: 일감을 만드는 함수} — 모두 불러 명령 · 환경이 만들어지는지(예외 · 빈 명령 · 문자열 아닌 환경 값) 확인.
    smoke: {이름: 일감 dict} — 실제로 짧게 돌려 rc 0인지(긴 셈 전에 실행 오류를 몇 분 안에 잡음). 돌려줌: 문제 목록."""
    bad = []
    for st, fn in builders.items():
        try:
            js = fn()
        except Exception as e:                                    # noqa: BLE001
            bad.append(f"{st}: 일감 만들기 실패 {type(e).__name__}: {e}")
            continue
        for n, j in js.items():
            if not j.get("cmd"):
                bad.append(f"{st}/{n}: 빈 명령")
            env = j.get("env") or {}
            nonstr = [k for k, v in env.items() if not isinstance(v, str)]
            if nonstr:
                bad.append(f"{st}/{n}: 문자열 아닌 환경 값 {nonstr[:3]}")
    for n, j in (smoke or {}).items():
        try:
            r = subprocess.run(j["cmd"], env=j.get("env"), cwd=j.get("cwd"), capture_output=True, text=True, timeout=timeout)
            if r.returncode != 0:
                bad.append(f"smoke {n}: rc {r.returncode} · {(r.stderr or r.stdout)[-300:]}")
        except subprocess.TimeoutExpired:
            log(f"smoke {n}: {timeout}초 안에 오류 없이 돎(시간 넘어 멈춤 = 시작은 정상)")
    return bad


# ───────── ④ 함정 찾기 ─────────
PATTERNS = [
    (re.compile(r"\bor\s+-?\d+(\.\d+)?(e-?\d+)?\b"), "`값 or 숫자` — 0을 결측처럼 바꿈(명시적 None 검사 쓰기)"),
    (re.compile(r"dict\(.*\*\*[A-Za-z_][A-Za-z0-9_.]*.*\b[A-Z][A-Z0-9_]{2,}\s*=(?!=)"), "`dict(**X, KEY=…)` — X에 KEY가 있으면 실행 오류(먼저 만들고 update)"),
]


def lint(paths, allow=()):
    """판정 · 실행 코드의 함정 꼴. allow: '파일:줄' 허용 목록(이유를 사전등록에 적은 것만)."""
    hits = []
    for p in paths:
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            s = line.split("#", 1)[0]
            for rx, why in PATTERNS:
                if rx.search(s) and f"{os.path.basename(p)}:{i}" not in allow:
                    hits.append(f"{os.path.basename(p)}:{i}: {why} → {line.strip()[:90]}")
    return hits


# ───────── ⑤ 내기 전 반대 검토 글 ─────────
def review_prompt(task_dir, checklist="/home/user/stock-dash/docs/RESEARCH-SELF-UPGRADE.md"):
    return (f"너는 GPT 검토자처럼 엄격한 반대 검토자다. 폴더 {task_dir}의 사전등록(PREREG.md)과 코드 전부를 읽고, "
            f"{checklist}의 §2 실수 점검표 항목마다 이 과제에 해당하는지 · 지켜졌는지를 파일 · 줄로 확인하라. 특히 "
            "① 장부 · 주문 순서가 미래 값(청산 날 · 손익)에 영향을 받는지 ② 한도(칸 · 돈) 불변식 ③ 자르기 시험이 순서 · 계좌 prefix까지 보는지 · FAIL이면 멈추는지 "
            "④ 사전등록의 '틀렸다고 볼 조건'이 모두 판정 코드에 있는지 ⑤ 0 · 결측 · 반올림 ⑥ 고정 코드 밖 import ⑦ 단계 명령이 실제로 만들어지는지(마른 실행) "
            "⑧ 비용 · 스트레스가 실제로 어디에 걸리는지. 결함은 '파일:줄 · 반례 · 고칠 방법'으로, 없으면 '없음'으로 쉬운 한국어로 답하라. 코드는 고치지 말 것.")
