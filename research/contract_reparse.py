"""보관 원문 ZIP으로 DART 공급계약 본문 칸을 판 k2로 다시 뽑아 contract-data에 덧붙입니다(DART API는 부르지 않음).

- 원문: 릴리스 dart-contracts-raw-v1의 종목별 묶음(raw-<종목>-<지문16>.tar) · 목록 contract-data/raw-assets.jsonl.
- 확인 사슬: ① 릴리스 자산 이름 · 크기 · 서버 지문(digest) = 목록의 tar_sha256 ② 받은 파일 sha256 = tar_sha256
  ③ 묶음 안 ZIP sha256 = 목록 zips = 공시 기록 zip_sha256 ④ ZIP 안 파일 sha256 = 공시 기록 members. 하나라도 어긋나면 아무것도 안 씀.
- 받은 묶음은 새 빈 임시 폴더에 두고(풀지 않고 메모리에서 읽음), 다 쓴 묶음은 바로 지움. 끝나면 폴더도 지움.
- 각 공시(state=받음)에 parser_k2="k2" · fields_k2 · why_k2(빈 칸 · 이상값 이유)를 덧붙임. k1 칸(parser · fields)은 그대로 둠.
- 요약: contract-data/_k2_summary.json(k1 대 k2 채움률 · 이상값 수 · 확인 사슬 수).

실행: python research/contract_reparse.py   (gh api로 자산 목록 · curl로 공개 내려받기 주소)
"""
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from collections import Counter
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_parse_k2 as k2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "contract-data"
TAG = "dart-contracts-raw-v1"
REPO = "ppx109-crypto/stock-dash"
K1_KEYS = ("계약금액", "최근매출액", "매출액대비%", "시작일", "종료일", "상대")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, check=True)
    return json.loads(r.stdout)


def release_assets():
    rel = gh(f"repos/{REPO}/releases/tags/{TAG}")
    assets, page = {}, 1
    while True:
        rows = gh(f"repos/{REPO}/releases/{rel['id']}/assets?per_page=100&page={page}")
        for a in rows:
            assets[a["name"]] = a
        if len(rows) < 100:
            return assets
        page += 1


def norm(key, v):
    """k1 · k2 비교용: 날짜 '.'→'-', %는 수로."""
    if key in ("시작일", "종료일"):
        return v.replace(".", "-")
    if key == "매출액대비%":
        try:
            return Decimal(v)
        except Exception:
            return v
    return v


def k1_pct_bad(v):
    try:
        x = Decimal(v)
    except Exception:
        return True
    return x < 0 or x > 1000


def main():
    rows = [json.loads(x) for x in (OUT / "raw-assets.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    files = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(OUT.glob("[0-9]*.json"))}
    filing = {f["rcept_no"]: (code, f) for code, body in files.items() for f in body["filings"] if f.get("state") == "받음"}
    need = sum(r["bytes"] for r in rows)
    work = Path(tempfile.mkdtemp(prefix="contract-raw-"))
    free = shutil.disk_usage(work).free
    print(f"자산 {len(rows)}개 · 합 {need / 1e6:.1f}MB · 디스크 여유 {free / 1e9:.1f}GB · 임시 폴더 {work}", flush=True)
    if free < need * 2 + 1e9:
        print("디스크 여유 모자람 · 멈춤")
        return 2
    assets = release_assets()
    chain = Counter()
    got = {}
    t0 = time.time()
    try:
        for n, r in enumerate(rows, 1):
            name = r["asset"].split("/", 1)[1]
            a = assets.get(name)
            if not a or a["size"] != r["bytes"] or a.get("digest") != "sha256:" + r["tar_sha256"]:
                raise SystemExit(f"릴리스 자산 불일치 {name}")
            chain["자산 이름 · 크기 · 서버 지문"] += 1
            path = work / name
            subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(path), a["browser_download_url"]], check=True)
            data = path.read_bytes()
            if sha(data) != r["tar_sha256"]:
                raise SystemExit(f"받은 묶음 지문 불일치 {name}")
            chain["받은 묶음 지문"] += 1
            want = dict(x.split(":") for x in r["zips"].split(","))
            with tarfile.open(fileobj=io.BytesIO(data)) as t:
                members = {m.name.lstrip("./")[:-4]: m for m in t.getmembers() if m.isfile() and m.name.endswith(".zip")}
                if set(members) != set(want):
                    raise SystemExit(f"묶음 안 ZIP 목록 불일치 {name}")
                for no, m in members.items():
                    zb = t.extractfile(m).read()
                    code, f = filing.get(no, (None, None))
                    if sha(zb) != want[no] or f is None or f.get("zip_sha256") != want[no] or code != r["code"]:
                        raise SystemExit(f"ZIP 지문 · 기록 불일치 {no}")
                    chain["ZIP 지문 = 목록 = 공시 기록"] += 1
                    with zipfile.ZipFile(io.BytesIO(zb)) as z:
                        raws = []
                        for mm, rec in zip(z.namelist(), f["members"]):
                            b = z.read(mm)
                            if mm != rec["name"] or sha(b) != rec["sha256"]:
                                raise SystemExit(f"ZIP 안 파일 지문 불일치 {no} {mm}")
                            raws.append(b)
                        if len(raws) != len(f["members"]):
                            raise SystemExit(f"ZIP 안 파일 수 불일치 {no}")
                    chain["ZIP 안 파일 지문"] += 1
                    got[no] = k2.parse_members(raws, f.get("kind"))
            path.unlink()
            if n % 25 == 0:
                print(f"{n}/{len(rows)} 묶음 · {len(got)}건 · {time.time() - t0:.0f}초", flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if set(got) != set(filing):
        raise SystemExit(f"원문 없는 공시 {len(set(filing) - set(got))}건 · 원문만 있는 것 {len(set(got) - set(filing))}건")

    fill = {"k1": Counter(), "k2": Counter()}
    bad = Counter()
    diff = Counter()
    why_count = Counter()
    for code, body in files.items():
        for f in body["filings"]:
            if f.get("state") != "받음":
                continue
            fields, why = got[f["rcept_no"]]
            f["parser_k2"] = k2.PARSER
            f["fields_k2"] = fields
            f["why_k2"] = why
            for key in K1_KEYS:
                v1, v2 = f["fields"].get(key), fields.get(key)
                fill["k1"][key] += v1 is not None
                fill["k2"][key] += v2 is not None
                if v1 == "-":
                    bad[f"k1 {key} 값이 '-'"] += 1
                if v1 is not None and v2 is not None and norm(key, v1) != norm(key, v2):
                    diff[key] += 1
            fill["k2"]["해지금액"] += fields.get("해지금액") is not None
            p1 = f["fields"].get("매출액대비%")
            if p1 is not None and k1_pct_bad(p1):
                bad["k1 % 0~1000 밖"] += 1
            p2 = fields.get("매출액대비%")
            if p2 is not None and Decimal(p2) > 1000:
                bad["k2 % 1000 넘음(검산 맞아 둠)"] += 1
            for key, w in why.items():
                why_count[f"{key} · {re.split(r'[(0-9' + chr(39) + ']', w)[0].strip()}"] += 1
        (OUT / f"{code}.json").write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    total = len(filing)
    summary = {
        "parser": k2.PARSER, "at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "filings": total, "assets": len(rows), "chain": dict(chain),
        "fill": {v: {key: f"{c} ({c / total:.1%})" for key, c in fill[v].items()} for v in fill},
        "anomaly": dict(bad), "k1_k2_both_filled_but_differ": dict(diff), "why_k2": dict(why_count.most_common()),
    }
    (OUT / "_k2_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
