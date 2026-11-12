"""MPOS-0019 원문 보관 대조: 릴리스 자산을 내려받아 ① tar 지문 = raw-assets.jsonl ② 안의 ZIP 지문 = jsonl · customer-data 기록
③ 기록의 '받음' 보고서마다 보관된 ZIP이 있는지 셉니다. --receipt 이면 입력 자료 지문과 묶은 영수증을 씀. 수익률 · 연결 풀이는 보지 않습니다(건수 · 지문만 출력)."""
import hashlib
import io
import json
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from customer_sample import input_digest  # noqa: E402

BASE = "https://github.com/ppx109-crypto/stock-dash/releases/download/"
CACHE = Path(next((a for a in sys.argv[1:] if not a.startswith("--")), "/tmp/customer_raw"))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    start = input_digest()
    rows = [json.loads(x) for x in Path("customer-data/raw-assets.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    kept, bad = {}, []
    for r in rows:
        name = r["asset"].split("/", 1)[1]
        path = CACHE / name
        if not path.exists():
            path.write_bytes(urllib.request.urlopen(BASE + r["asset"], timeout=120).read())
        blob = path.read_bytes()
        if sha(blob) != r["tar_sha256"] or len(blob) != r["bytes"]:
            bad.append(("tar 지문", name))
            continue
        listed = dict(z.split(":") for z in r["zips"].split(","))
        with tarfile.open(fileobj=io.BytesIO(blob)) as t:
            inside = {Path(m.name).stem: sha(t.extractfile(m).read()) for m in t.getmembers() if m.isfile()}
        if inside != listed:
            bad.append(("묶음 안 ZIP", name))
        for rcept, h in inside.items():
            kept.setdefault((r["code"], rcept), set()).add(h)
    need = missing = mismatch = 0
    for p in sorted(Path("customer-data").glob("[0-9]*.json")):
        body = json.loads(p.read_text(encoding="utf-8"))
        for f in body.get("filings", []):
            if f.get("state") != "받음":
                continue
            need += 1
            got = kept.get((body["code"], f["rcept_no"]))
            if not got:
                missing += 1
            elif f["zip_sha256"] not in got:
                mismatch += 1
    end = input_digest()
    if end != start:
        bad.append(("대조 도중 입력 자료가 바뀜", ""))
    out = {"자산": len(rows), "자산 문제": len(bad), "받음 보고서": need, "보관 없음": missing, "지문 불일치": mismatch,
           "문제 예": bad[:5]}
    ok = not bad and not missing and not mismatch
    print(json.dumps(out, ensure_ascii=False))
    if "--receipt" in sys.argv:
        out.update(ok=ok, input_sha256=start, input_sha256_end=end, verifier_sha256=sha(Path(__file__).read_bytes()),
                   at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
        Path("research/customer_verify_receipt.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
