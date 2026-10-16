#!/usr/bin/env bash
# tools/save_customer_batch.sh 합성 시험(가짜 gh · 로컬 git): 같은 실행 재시도에 다른 내용 → 새 이름(덮어쓰기 없음) ·
# 같은 내용 다시 → 올리지 않고 재사용 · customer-data 없을 때 빈 저장 · tar 내용 지문이 결정적.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
W=$(mktemp -d); mkdir -p "$W/bin" "$W/assets"
cat > "$W/bin/gh" <<EOF
#!/usr/bin/env bash
A="$W/assets"
if [ "\$1 \$2" = "release view" ]; then
  name=\$(printf '%s' "\$7" | sed -n 's/.*name=="\([^"]*\)".*/\1/p')
  [ -e "\$A/\$name" ] && stat -c %s "\$A/\$name"; exit 0
fi
if [ "\$1 \$2" = "release upload" ]; then
  [ -e "\$A/\$(basename "\$4")" ] && { echo exists; exit 1; }
  cp "\$4" "\$A/"; echo up >> "$W/uploads.txt"; exit 0
fi
exit 9
EOF
chmod +x "$W/bin/gh"
git init -q --bare "$W/remote.git"; git clone -q "$W/remote.git" "$W/work" 2>/dev/null; cd "$W/work"
git config user.email t@t; git config user.name t; git commit -q --allow-empty -m init; git push -q origin HEAD:main 2>/dev/null
mkdir -p tools; cp "$ROOT/tools/save_customer_batch.sh" tools/
export PATH="$W/bin:$PATH" GITHUB_REF_NAME=main GITHUB_RUN_ID=77
bash tools/save_customer_batch.sh                                   # customer-data 없음 · ZIP 없음
mkdir -p raw/000001; echo AAA > raw/000001/r1.zip; bash tools/save_customer_batch.sh
mkdir -p raw/000001; echo BBB > raw/000001/r2.zip; GITHUB_RUN_ATTEMPT=2 bash tools/save_customer_batch.sh
mkdir -p raw/000001; echo AAA > raw/000001/r1.zip; bash tools/save_customer_batch.sh
[ "$(ls "$W/assets" | wc -l)" = 2 ] || { echo "자산 수 틀림"; exit 1; }
[ "$(wc -l < "$W/uploads.txt")" = 2 ] || { echo "올림 수 틀림"; exit 1; }
[ "$(wc -l < customer-data/raw-assets.jsonl)" = 3 ] || { echo "목록 줄 수 틀림"; exit 1; }
[ "$(sed -n 1p customer-data/raw-assets.jsonl | cut -d, -f1)" = "$(sed -n 3p customer-data/raw-assets.jsonl | cut -d, -f1)" ] || { echo "같은 내용 다른 이름"; exit 1; }
[ -z "$(ls raw/000001)" ] || { echo "ZIP 안 지워짐"; exit 1; }
echo "저장 시험 통과"
