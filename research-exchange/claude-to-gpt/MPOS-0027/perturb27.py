"""미래 독립 합성 대조 장부(PREREG 2판 3절): QCUT(2021-12-31) 뒤에 판 매매의 손익 부호를 뒤집고, QCUT 앞에 사서 뒤에 판 매매는 판 날을
같은 종목 줄에서 3거래일 뒤로 미룸. 산 날 · 종목 · 칸은 그대로 → z100g의 QCUT까지 요청 · 배정 · NAV가 같아야 함.
python3 perturb27.py 원장부 새장부 가격캐시(nrl pkl)"""
import json
import pickle
import sys

Q = "20211231"
led = json.load(open(sys.argv[1]))
lanes = pickle.load(open(sys.argv[3], "rb"))[1]
out = []
for c, b, e, p, s in led:
    if e > Q:
        p = -p
        if b <= Q:
            d = lanes[c]["날"]
            k = d.index(e)
            e = d[min(k + 3, len(d) - 1)]
    out.append([c, b, e, p, s])
json.dump(out, open(sys.argv[2], "w"))
print("바꾼 매매", sum(1 for x, y in zip(led, out) if x != y), "/", len(led))
