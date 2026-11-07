"""MPOS-0027 바탕 대조(PREREG 2판 2-A · 3 · 4절 · 손익 요약 없음).
python3 c27_nav.py 출력.json 기준csv 기준evt [이름 csv evt 자르는날]…
- 기준 csv: 날마다 회계 보존식 NAV = 현금 + 일봉 + 분봉15 + 바구니 + 엔진 + 인버스(csv는 원 단위 반올림 → 허용 |차이| ≤ 6원).
  예비 = min(현금, 그날 1일봉 몫)이라 현금 안에 든 값(z100g 473줄) → 보존식에서 빼고 '예비 ≤ 현금'을 따로 검사(사전등록 2판 4절 식의 실수 · 결과 본 뒤 고침).
- 비교 판마다: 자르는 날까지 csv 모든 칸 같음 · 1일봉 요청 · 배정 · 이유 같음(날 ≤ c) · 매수 낸 돈 같음."""
import csv
import json
import sys

out = {}
base_csv, base_evt = sys.argv[2], sys.argv[3]
rows = list(csv.DictReader(open(base_csv)))
parts = ("현금", "일봉", "분봉15", "바구니", "엔진", "인버스")
gap = max(abs(float(r["NAV"]) - sum(float(r[k]) for k in parts)) for r in rows)
out["기준 회계 보존식 최대 |차이|(원)"] = gap
out["기준 회계 보존식 통과(≤ 6원)"] = gap <= 6
out["예비 ≤ 현금(모든 날)"] = all(float(r["예비"]) <= float(r["현금"]) + 1 for r in rows)
out["기준 행 · 첫 · 끝"] = [len(rows), rows[0]["날"], rows[-1]["날"]]
E0 = json.load(open(base_evt))
out["기준 요청 이유별"] = {}
for q in E0["요청"]:
    out["기준 요청 이유별"][q["이유"]] = out["기준 요청 이유별"].get(q["이유"], 0) + 1
out["기준 매매(낸 돈 기록) · 끝까지 보유"] = [len(E0["매매"]), sum(1 for t in E0["매매"] if t["끝까지보유"])]
args = sys.argv[4:]
for j in range(0, len(args), 4):
    name, c_csv, c_evt, cut = args[j:j + 4]
    R = list(csv.DictReader(open(c_csv)))
    a = [r for r in rows if r["날"] <= cut]
    b = [r for r in R if r["날"] <= cut]
    E1 = json.load(open(c_evt))
    # 장부 줄 번호 k는 판 날 순서라 c 뒤 매매가 바뀌면 c 앞 매매 번호도 밀림(미래에 기대는 열쇠) → 비교에서 뺌(판 1 비교 도구 결함 · 결과 본 뒤 고침)
    qa = [{x: v for x, v in q.items() if x != "k"} for q in E0["요청"] if q["날"] <= cut]
    qb = [{x: v for x, v in q.items() if x != "k"} for q in E1["요청"] if q["날"] <= cut]
    pa = sorted((t["종목"], t["산날"], t["낸돈"]) for t in E0["매매"] if t["산날"] <= cut)
    pb = sorted((t["종목"], t["산날"], t["낸돈"]) for t in E1["매매"] if t["산날"] <= cut)
    first = next((r["날"] for r, s in zip(a, b) if r != s), None)
    out[name] = {"자르는 날": cut, "csv(c까지) 모든 칸 같음": a == b, "행 수": [len(a), len(b)], "처음 다른 날": first,
                 "요청 · 배정 · 이유(c까지) 같음": [x == y for x, y in [(qa, qb)]][0], "요청 수": [len(qa), len(qb)],
                 "매수 낸 돈(c까지 산 것) 같음": pa == pb, "c 뒤 처음 다른 날(적용 증거)": next((r["날"] for r, s in zip(rows, R) if r != s), None)}
    out[name]["같음"] = out[name]["csv(c까지) 모든 칸 같음"] and out[name]["요청 · 배정 · 이유(c까지) 같음"] and out[name]["매수 낸 돈(c까지 산 것) 같음"]
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
