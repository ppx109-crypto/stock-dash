#!/bin/bash
cd /home/user/stock-dash
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/imp
jobs=()
for cap in 0 10 15 20; do for park in 0 1; do for m in 1.0 1.5 2.0; do [ -s "$S/nav/cap${cap}_park${park}_m${m}.csv" ] || jobs+=("$cap $park $m"); done; done; done
echo "다시 돌릴 판 ${#jobs[@]}"
run() {
  set -- $1
  cap=$1; park=$2; m=$3
  name="cap${cap}_park${park}_m${m}"
  vol=$(python3 -c "print(0.010911*$m)")
  sc=$(python3 -c "print($cap/100)")
  NRL_CACHE=/tmp/nrl-cache.pkl Z_ACC_VOL=$vol Z_STOCK_CAP=$sc Z_PARK=$park Z_OUT=$S/nav/$name.csv python3 research/z092.py > $S/log/$name.log 2>&1
  echo "$name 끝 $?"
}
export -f run; export S
mkdir -p $S/nav $S/log
printf '%s\n' "${jobs[@]}" | xargs -P 4 -I{} bash -c 'run "{}"'
