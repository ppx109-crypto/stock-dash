"""H-PRESENCE 길이 문턱 셈: 표 생성 시점(2026-09-25 02:46 UTC · features.json) 가격 바 수가 121 ~ 180인 종목 = 정직한 판(horizons=(0,))이면 120번째 바부터 줄이 생겼을 종목."""
import json, os, sys
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import nrl  # noqa: E402
import rule  # noqa: E402
END = "20260925"
out = []
for c, b in nrl.prices.items():
    ds = [d for d, _ in b["rows"] if d <= END]
    if 121 <= len(ds) <= 180:
        out.append({"종목": c, "첫 날": ds[0], "바 수(09-25까지)": len(ds), "120번째 바 날": ds[119]})
every = sorted(len([d for d, _ in b["rows"] if d <= END]) for b in nrl.prices.values())
res = {"길이 문턱에 걸린 종목": out, "건수": len(out), "가격 종목 수": len(every), "바 수 ≤ 120": sum(1 for n in every if n <= 120)}
json.dump(res, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
