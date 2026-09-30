"""1시간봉 67회차 — 65회차에서 두 반 모두 조금 나아진 공시 거르기 둘을 함께: 20일 안 자사주 공시 · 희석 공시(유상증자 · CB · BW · EB)가 있으면 사지 않음.
공시는 접수 다음 날부터 앎(hlab.daily_context의 자사주20 · 희석20, 전 거래일 재료) — 문턱 없음(켜짐/꺼짐)이라 문턱 미래 참조도 없음."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
src = open("research/h065.py", encoding="utf-8").read()
pre = src.split("# ---------- ① 가르는 힘")[0].replace("65회차 (이긴 매매 vs 진 매매 · 거르기)", "67회차 (공시 거르기 둘 함께)")
mid = src.split("# ---------- ② 거르기 ----------")[1].split('print("  ② 거르기')[0]
exec(pre); exec(mid)
run("지금", set())
a, b_ = flag_block("자사주20", 1.0), flag_block("희석20", 1.0)
run("자사주20 · 희석20 둘 다 막음", a | b_)
print("끝", flush=True)
