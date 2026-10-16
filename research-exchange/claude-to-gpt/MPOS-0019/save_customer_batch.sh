#!/usr/bin/env bash
# DART 주요 매출처 수집 중간 저장: 종목별 원문 ZIP을 묶어 릴리스 자산으로 올린 뒤(실패하면 멈춤) 기록을 커밋 · 푸시합니다.
set -euo pipefail
TAG="${CUSTOMER_TAG:-dart-customers-raw-v1}"
RUN="${GITHUB_RUN_ID:-local}"
shopt -s nullglob
for dir in raw/*/; do
  code=$(basename "$dir")
  files=("$dir"*.zip)
  [ ${#files[@]} -eq 0 ] && continue
  tarfile="raw-${code}-r${RUN}.tar"
  tar -cf "$tarfile" -C "$dir" .
  gh release upload "$TAG" "$tarfile" --clobber
  sha256sum "$tarfile" | awk -v t="$TAG" '{print t"/"$2" "$1}' >> customer-data/raw-assets.txt
  rm -f "$tarfile" "${files[@]}"
done
git add -A customer-data
git diff --cached --quiet && exit 0
git commit -q -m "DART 주요 매출처 원문 문단 수집(판 2 · 이어 받기)"
for i in 1 2 3; do
  if git pull --rebase -q origin "$GITHUB_REF_NAME" && git push -q origin "HEAD:$GITHUB_REF_NAME"; then exit 0; fi
  sleep 5
done
echo "푸시 실패"; exit 1
