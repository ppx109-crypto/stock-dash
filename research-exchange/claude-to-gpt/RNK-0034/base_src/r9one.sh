#!/bin/bash
# 인자: 이름 · 나머지는 환경 변수 쌍
cd /home/user/stock-dash
export I_DIP=1 I_DOLLAR=2 I_GATE=weakidle20 I_L=20 I_TOP=2 I_CANDS=133690,138230,132030,148070 I_W=1 I_QINV=free I_QPRI=inv I_QTH=0.095 I_DIP_TH=-0.045
name=$1; shift
env "$@" timeout 900 python research/i013.py 2>&1 | grep "함께" | sed 's/1일봉만.*함께/함께/' > /tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/$OUTDIR/$name.out
