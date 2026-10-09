#!/bin/bash
# MAXRET-0026 실행(2026-10-10 08:21 ~ 08:40 KST) · head e91f88e9
cd /home/user/stock-dash
C=/tmp/maxret-0026-cache.pkl
[ ! -e $C ] && echo "캐시 없음 확인"
env NRL_CACHE=$C Z_ACC_VOL=0.010911 Z_OUT=nav/m1.csv python3 research/z094.py          # 캐시를 만듦(홀로)
for x in "m2 0.021822" "m2.5 0.0272775" "m3 0.032733" "m4 0.043644" "off 0"; do set -- $x
  env NRL_CACHE=$C Z_ACC_VOL=$2 Z_OUT=nav/$1.csv python3 research/z094.py; done          # 같은 캐시(3개씩 나란히)
# 앞 반만으로 고른 판 m3 → 자르기
env NRL_CACHE=$C Z_ACC_VOL=0.032733 Z_TO=20231231 Z_OUT=nav/cut_m3_T20231231.csv python3 research/z094.py
python3 research/z099_eval.py nav nav/cut_m3_T20231231.csv > eval.json
