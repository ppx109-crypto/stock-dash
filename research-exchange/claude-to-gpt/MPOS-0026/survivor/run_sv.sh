#!/bin/bash
# 생존 편향 판(SURVIVOR.md) — 캐시 두 개 · 정확한 명령 기록
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad
cd $S/m54tree
b(){ CAPS_ADJ=0 NRL_CACHE=/tmp/maxret-0026-cache.pkl PYTHONHASHSEED=0 EX_HC=$S/mpos27/honest_cache.py EX_SV=$1 EX_OUT=$S/sv/nrl_$1.pkl EX_OUT_T=$S/sv/side_$1.pkl EX_TMP=$S/sv/tmp_$1 python3 $S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py $S/sv/build_$1.mods.json $S/mpos27/survivor_build.py > $S/sv/build_$1.log 2>&1; echo "$1 끝 $?"; rm -rf $S/sv/tmp_$1; }
SECONDS=0
b A & b B & wait
echo "${SECONDS}초 끝"
# --- 장부 · 바탕(따로 실행) ---
# 장부: led(){ CAPS_ADJ=0 NRL_CACHE=$S/sv/nrl_$2.pkl PYTHONHASHSEED=0 EX_HC=$S/mpos27/honest_cache.py EX_MODE=HONEST EX_FULL=$S/sv/side_$2.pkl EX_TEACH=$3 EX_OUT=$S/sv/led_$1.json python3 tree_run.py $S/sv/led_$1.mods.json honest_ledger.py; }  led A A "" · led B0 B "" · led Bp B rate · led B1 B all
# 바탕: run_base.sh와 같은 환경 · NRL_CACHE=$S/sv/nrl_(A|B).pkl · Z_D1_LED=$S/sv/led_칸.json · Z_OUT=$S/sv/base_칸.csv
