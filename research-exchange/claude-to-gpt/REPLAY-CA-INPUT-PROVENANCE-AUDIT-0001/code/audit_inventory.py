"""REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001 · 정적 감사: 고정 검색어 match 전부를 분류(저장소 코드 실행 없음).
python3 -I audit_inventory.py <git 저장소 경로> <출력 폴더>
git 객체만 읽음(ls-tree · grep · show · rev-parse). 줄 본문은 저장하지 않고 sha256만 남김. 네트워크 함수 막음."""
import hashlib
import json
import re
import socket
import subprocess
import sys
from collections import Counter
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
REPO, OUT = Path(sys.argv[1]), Path(sys.argv[2])
H = "6261e5a100607b36fa033b8a2ce710482cf8ccfa"
PR114_DIR = "research-exchange/claude-to-gpt/REPLAY-CA-QUANTITY-MUTATION-GATE-0001/"
S2 = {86: "916bc678", 88: "a5891f5b", 90: "f2e59846", 92: "8f9a1d93", 94: "63942ef7", 96: "e6c4f9d5", 98: "c5abe694",
      100: "c16010b1", 102: "b940b283", 104: "ad13f077", 106: "dacbcb09", 108: "ca440842", 110: "2c7c268b", 112: "9e88dba8"}
FIXED = ["corporate_action", "m_qty", "m_price", "apply_date", "split", "reverse_split", "bonus_issue", "rights", "dividend",
         "adjusted", "event_id", "revision", "available_at", "src"]
SUPP = ["rcept_no", "ORG_ADJ", "price_basis", "effective_date", "수정주가", "액면분할", "무상증자", "권리락", "nstk_ascnt"]
CTX = re.compile(r"액면|분할|병합|무상|감자|수정주가|원주가|권리|배당|corporate|reverse_split|bonus|m_qty|m_price|apply_date|ORG_ADJ|rights|dividend|available_at|adjusted")
NET = re.compile(r"requests\.|urlopen|httpx|\.request\(")
WRITE = re.compile(r"write_text|json\.dump|open\([^)]*['\"]w")


def git(*a, binary=False):
    p = subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(REPO), *a], capture_output=True)
    return p.returncode, (p.stdout if binary else p.stdout.decode("utf-8", "replace"))


def resolve(short):
    rc, out = git("rev-parse", short)
    assert rc == 0, short
    return out.strip()


def grep(commit, term, pathspec=None):
    args = ["grep", "-n", "-I", "-F", "-e", term, commit] + (["--", pathspec] if pathspec else [])
    rc, out = git(*args)
    rows = []
    for ln in out.splitlines():
        rest = ln[len(commit) + 1:]
        path, line, text = rest.split(":", 2)
        rows.append((path, int(line), text))
    return rc, rows


_cache = {}


def blob_info(commit, path):
    k = (commit, path)
    if k not in _cache:
        _, raw = git("show", f"{commit}:{path}", binary=True)
        _, b = git("rev-parse", f"{commit}:{path}")
        text = raw.decode("utf-8", "replace")
        blocks, cur = [], None                                       # 클래스 정의 구간(들여쓰기 블록)
        for i, l in enumerate(text.splitlines(), 1):
            if l.startswith("class "):
                cur = [i, i]
                blocks.append(cur)
            elif cur and (l.startswith((" ", "\t")) or not l.strip()):
                cur[1] = i
            elif cur:
                cur = None
        _cache[k] = {"blob": b.strip(), "sha256": hashlib.sha256(raw).hexdigest(), "net": bool(NET.search(text)),
                     "write": bool(WRITE.search(text)), "class_blocks": blocks}
    return _cache[k]


def classify_exchange(path, line, info):
    name = path.rsplit("/", 1)[-1]
    if "/code/" in path and path.endswith(".py"):
        inside = any(a <= line <= b for a, b in info["class_blocks"])
        return ("consumer", "합성 장부 클래스 정의 구간") if inside else ("test", "합성 fixture · 하네스")
    if "/evidence/" in path:
        return "data", "합성 파생 증거"
    if path.endswith(".md") or name in ("manifest.json", "receipt.json") or "/schema" in path:
        return "doc", "보고 · 계약 · 목록"
    return None, "규칙 없음"


def classify_repo(path, info):
    name = path.rsplit("/", 1)[-1]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if path.startswith("tests/") or "/tests/" in path or re.fullmatch(r"test_.*\.py", name):
        return "test", "시험 경로"
    if ext in ("md", "txt"):
        return "doc", "문서"
    if ext in ("json", "csv", "jsonl", "log", "tsv"):
        return "data", "자료 파일"
    if ext in ("yml", "yaml"):
        return "transformer", "워크플로 조립"
    if ext in ("py", "html", "js", "sh"):
        if info["net"]:
            return "producer", "네트워크 호출 흔적"
        if info["write"]:
            return "transformer", "파일 쓰기 흔적"
        return "consumer", "읽기 · 판정만"
    return None, "규칙 없음"


def relevance(token, text):
    if CTX.search(text):
        return True, "기업행위 · 가격 기준 문맥 낱말"
    if token == "split" and re.search(r"\.split\(|rsplit|splitlines", text):
        return False, "문자열 나누기"
    if token == "src":
        return False, "기업행위 사건 칸 아님(출처 경로 · 변수 · HTML 속성 등)"
    return False, "기업행위 문맥 낱말 없음"


rows, counts, files = [], [], {}
scopes = [("S1", None, H, None)] + [("S2", pr, resolve(sh), None) for pr, sh in S2.items()]
for scope, pr, commit, _ in scopes:
    if scope == "S2":
        rc, out = git("diff", "--name-only", resolve("origin/main"), commit, "--", "research-exchange/claude-to-gpt")
        dirs = sorted({"/".join(p.split("/")[:3]) + "/" for p in out.split()})
        assert len(dirs) == 1, (pr, dirs)
        spec = dirs[0]
    else:
        spec = None
    for term_set, terms in (("fixed14", FIXED), ("supp9", SUPP)):
        for t in terms:
            rc, found = grep(commit, t, spec)
            counts.append({"scope": scope, "pr": pr, "commit": commit, "pathspec": spec, "term_set": term_set, "token": t,
                           "git_grep_exit": rc, "lines": len(found), "files": len({p for p, _, _ in found})})
            for path, line, text in found:
                info = blob_info(commit, path)
                files[f"{commit}:{path}"] = {"scope": scope, "pr": pr, "path": path, "blob": info["blob"], "sha256": info["sha256"]}
                if scope == "S2" or path.startswith(PR114_DIR):
                    cls, why = classify_exchange(path, line, info)
                    rel, rwhy, actual = True, "기업행위 합성 계약 자료", False
                else:
                    cls, why = classify_repo(path, info)
                    rel, rwhy = relevance(t, text)
                    actual = cls not in ("test", "doc") and cls is not None
                rows.append({"scope": scope, "pr": pr, "commit": commit[:12], "path": path, "line": line, "token": t, "term_set": term_set,
                             "class": cls or "UNCLASSIFIED", "class_basis": why, "ca_relevant": rel, "relevance_basis": rwhy,
                             "actual_path": actual, "line_sha256": hashlib.sha256(text.encode()).hexdigest(), "blob": info["blob"]})

fx = [r for r in rows if r["term_set"] == "fixed14"]
summary = {"rows_total": len(rows), "rows_fixed14": len(fx), "rows_supp9": len(rows) - len(fx),
           "unclassified": sum(r["class"] == "UNCLASSIFIED" for r in rows),
           "fixed14_by_class": dict(Counter(r["class"] for r in fx)),
           "fixed14_by_scope": dict(Counter(r["scope"] for r in fx)),
           "fixed14_S1_ca_relevant_actual": sum(r["scope"] == "S1" and r["ca_relevant"] and r["actual_path"] for r in fx),
           "files_hashed": len(files), "repo_code_executed": 0, "external_calls": 0}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "INVENTORY.json").write_text("{\n\"summary\": " + json.dumps(summary, ensure_ascii=False) + ",\n\"files\": [\n"
                                    + ",\n".join(json.dumps(v, ensure_ascii=False) for _, v in sorted(files.items())) + "\n],\n\"matches\": [\n"
                                    + ",\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n]\n}\n")
(OUT / "evidence").mkdir(exist_ok=True)
(OUT / "evidence" / "search-counts.json").write_text(json.dumps(counts, ensure_ascii=False, indent=1) + "\n")
s1rel = sorted({(r["path"], r["class"]) for r in fx if r["scope"] == "S1" and r["ca_relevant"] and not r["path"].startswith(PR114_DIR)})
print(json.dumps(summary, ensure_ascii=False))
print("S1 밖-PR114 기업행위 관련 파일(고정 14):", json.dumps(s1rel, ensure_ascii=False))
print("S1 보충 9 기업행위 관련 실제 경로 파일:", json.dumps(sorted({(r["path"], r["class"]) for r in rows if r["scope"] == "S1" and r["term_set"] == "supp9"
                                                       and r["ca_relevant"] and r["actual_path"]}), ensure_ascii=False))
