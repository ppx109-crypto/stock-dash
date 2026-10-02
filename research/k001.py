"""K 1회차 — 코스닥만 따로: 지금 1일봉 규칙(새 82)을 코스닥 101종목 · 코스닥 안 시총 순위 · 코스닥 시장 폭으로(씨앗 8).
판: 그대로 · 시장 폭을 코스피(지금 표) 것으로 · 조용함 문턱을 코스닥 줄로 · 가르침 뺌 · 정배열 문만 · 추세 문만."""
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
import ktools as K

nrl, rule = K.nrl, K.rule
rows = K.build()
pool = [r for r in rows if K.caps.inside(r, rule.TOP) and r["date"] >= "20170101"]
print(f"== K 1회차: 코스닥 {len(K.KQ)}종목 · 줄 {len(pool)} · 하루 평균 {len(pool) / max(1, len({r['date'] for r in pool})):.0f}종목 ==", flush=True)
K.use_breadth(rows, "kq")
K.run("그대로(코스닥 시장 폭)", pool)
K.run("가르침 뺌", pool, holds=lambda r: (rule.holds(r) or nrl.aligned(r)) and not nrl.target_cut(r))
K.run("정배열 문만(+ 가르침)", pool, holds=lambda r: nrl.aligned(r) and nrl.teacher(r) and not nrl.target_cut(r))
K.run("추세 문만(+ 가르침)", pool, holds=lambda r: rule.holds(r) and nrl.teacher(r) and not nrl.target_cut(r))
old = rule._calm
rule._calm = K.calm_kq(rows)
print(f"  (조용함 문턱: 지금 {old:.3f} → 코스닥 줄 {rule._calm:.3f})", flush=True)
K.run("조용함 문턱 코스닥으로", pool)
rule._calm = old
K.use_breadth(rows, "kospi")
K.run("시장 폭을 지금 표(코스피 섞인) 것으로", pool)
print("끝", flush=True)
