#!/bin/bash
# 바깥 입력 감사 판 2 — 정확한 명령 기록
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad
cd $S/m54tree
CAPS_ADJ=0 NRL_CACHE=/tmp/maxret-0026-cache.pkl PYTHONHASHSEED=0 EX_HC=$S/mpos27/honest_cache.py EX_REPO=/home/user/stock-dash EX_FULL=$S/hc/full.json.pkl EX_OUT=$S/hc3/avail2.json python3 $S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py $S/hc3/avail2.mods.json $S/mpos27/avail_audit.py > $S/hc3/avail2.log 2>&1; echo "감사 끝 $?"
