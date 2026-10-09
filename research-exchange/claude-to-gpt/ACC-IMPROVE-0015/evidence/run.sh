#!/bin/bash
cd /home/user/stock-dash
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/imp15
run() {
  name=$1; shift
  env NRL_CACHE=/tmp/nrl-cache.pkl Z_ACC_VOL=0.010911 "$@" Z_OUT=$S/nav/$name.csv python3 research/z093.py > $S/log/$name.log 2>&1
  echo "$name 끝 $?"
}
export -f run; export S
cat <<L | xargs -P 4 -L 1 bash -c 'run "$@"' _
F
drop_1d Z_DROP=1d
drop_15m Z_DROP=15m
drop_basket Z_DROP=basket
drop_engine Z_DROP=engine
drop_inverse Z_DROP=inverse
basket_bear Z_BASKET_BEAR=1
svol30 Z_STOCK_VOL=0.03
svol40 Z_STOCK_VOL=0.04
L
