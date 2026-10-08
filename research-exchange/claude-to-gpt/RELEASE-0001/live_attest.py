"""RELEASE-0001 실제 GitHub 사후 검사(PR을 연 뒤에만 씀). 같은 PR의 본문 · head · 커밋 메시지 · comment만 읽고,
매치 문자열 없이 개수 · 코드 · SHA만 출력합니다. 결과 가지에는 아무것도 쓰지 않습니다.
사용:
  python3 -I live_attest.py check <pr> <연 때 head> <연 때 커밋 수> [comment_id]
  python3 -I live_attest.py correct <pr>      # 실제 본문을 받아 footer 줄만 일반 표기로(1회)
  python3 -I live_attest.py comment <pr> <receipt json 파일>   # 9키 receipt comment 올림 → comment id 출력
  python3 -I live_attest.py fixcomment <comment_id>             # comment의 자동 footer만 1회 보정
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import attest as A
REPO = "repos/ppx109-crypto/stock-dash"

def gh(*args, data=None):
    p = subprocess.run(["gh", "api", *args] + (["--input", "-"] if data is not None else []),
                       input=json.dumps(data) if data is not None else None, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("gh 실패: " + p.stderr.strip()[:200].replace("\n", " "))
    return json.loads(p.stdout) if p.stdout.strip() else None

def check(pr, head0, n0, cid=None):
    at = A.Attest()
    pull = gh(f"{REPO}/pulls/{pr}")
    commits = gh(f"{REPO}/pulls/{pr}/commits?per_page=100")
    snap = {"pr": int(pr), "fetched_after_open": True, "postcheck_source": "github", "body": pull.get("body") or "",
            "head_sha": pull["head"]["sha"], "expected_head": head0,
            "commits": [{"sha": c["sha"], "message": c["commit"]["message"]} for c in commits], "commits_at_open": int(n0),
            "comment_found": True}
    cmt = None
    if cid:
        try:
            c = gh(f"{REPO}/issues/comments/{cid}")
            cmt = {"found": True, "private_session_count": at.scan(c.get("body") or ""),
                   "receipt_keys_present": all(f"- {k}:" in (c.get("body") or "") for k in A.RECEIPT_KEYS)}
        except SystemExit:
            cmt = {"found": False}
        snap["comment_found"] = cmt["found"]
    ev = at.evaluate(snap)
    _, _, _, correctable = at.correct(snap["body"])
    out = {"pr": int(pr), "state": pull["state"], "draft": pull["draft"], "head_sha": snap["head_sha"],
           "head_same": snap["head_sha"] == head0, "commits_now": len(commits), "commits_at_open": int(n0), **ev,
           "body_correctable": correctable, "comment": cmt, "body_updated_at": pull.get("updated_at")}
    if not cid:
        out["codes"] = [c for c in out["codes"] if c != "COMMENT_NOT_CONFIRMED"]
    print(json.dumps(out, ensure_ascii=False))

def correct(pr):
    at = A.Attest()
    body = gh(f"{REPO}/pulls/{pr}").get("body") or ""
    new, changed, after, ok = at.correct(body)
    if not changed or not ok:
        print(json.dumps({"corrected": False, "changed": changed, "after_count": after, "correctable": ok})); return
    gh("-X", "PATCH", f"{REPO}/pulls/{pr}", data={"body": new})
    print(json.dumps({"corrected": True, "after_count": after}))

def comment(pr, path):
    at = A.Attest()
    r = json.load(open(path, encoding="utf-8"))
    chk = at.check_receipt(r)
    if not chk["valid"]:
        raise SystemExit("receipt 무효: " + ",".join(chk["codes"]))
    c = gh(f"{REPO}/issues/{pr}/comments", data={"body": A.receipt_text(r)})
    print(json.dumps({"comment_id": c["id"], "posted": True}))

def fixcomment(cid):
    at = A.Attest()
    body = gh(f"{REPO}/issues/comments/{cid}").get("body") or ""
    new, changed, after, ok = at.correct(body)
    if changed and ok:
        gh("-X", "PATCH", f"{REPO}/issues/comments/{cid}", data={"body": new})
    print(json.dumps({"comment_corrected": bool(changed and ok), "after_count": after}))

if __name__ == "__main__":
    cmd, *rest = sys.argv[1:]
    {"check": check, "correct": correct, "comment": comment, "fixcomment": fixcomment}[cmd](*rest)
