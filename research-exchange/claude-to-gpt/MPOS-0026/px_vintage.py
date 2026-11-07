"""MPOS-0026 후속(손익 안 봄): 표 생성 입력 판(b8365547 · 2026-09-25 02:37 UTC · ROWMASK 출처 확인 판) 대 고정 나무(9743cb802) 가격 파일 비교.
대상 207940 · 095340(+ 507종목 전체에서 값이 다른 종목 수). 같은 날의 종가가 다른 날 수 · 범위 · 비율(새 ÷ 옛)의 모양."""
import json
import subprocess
import sys

OLD, NEW = "b8365547", "9743cb802"


def load(rev, code):
    r = subprocess.run(["git", "show", f"{rev}:price-data/{code}.json"], capture_output=True)
    if r.returncode:
        return None
    b = json.loads(r.stdout)
    rows = b.get("rows") or b.get("closes") or []
    return {str(r[0]): float(r[1]) for r in rows if r[1]}


names = subprocess.run(["git", "ls-tree", "--name-only", NEW, "price-data/"], capture_output=True, text=True).stdout.split()
out, ndiff = {}, []
for f in names:
    code = f.split("/")[-1][:-5]
    if not code.isdigit():
        continue
    a, b = load(OLD, code), load(NEW, code)
    if a is None or b is None:
        continue
    common = sorted(set(a) & set(b))
    diff = [d for d in common if abs(a[d] - b[d]) > 1e-6 * max(1, abs(a[d]))]
    if diff:
        ndiff.append(code)
    if code in ("207940", "095340") or (diff and len(ndiff) <= 3):
        r = [b[d] / a[d] for d in diff]
        out[code] = {"옛 날 수 · 새 날 수": [len(a), len(b)], "옛 첫 날 · 새 첫 날": [min(a), min(b)], "같은 날 값 다름": len(diff),
                     "다른 날 범위": [diff[0], diff[-1]] if diff else None,
                     "새 ÷ 옛 비율 최소 · 최대": [round(min(r), 6), round(max(r), 6)] if r else None,
                     "예(날 · 옛 · 새)": [(d, a[d], b[d]) for d in diff[:3]]}
out["값이 다른 종목 수"] = len(ndiff)
out["값이 다른 종목"] = ndiff[:30]
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
