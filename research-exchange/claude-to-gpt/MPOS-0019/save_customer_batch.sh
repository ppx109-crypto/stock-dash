#!/usr/bin/env bash
# DART 주요 매출처 수집 중간 저장(판 3 · GPT #444 round 2 반영)
# 1) 종목별 원문 ZIP을 묶어 내용 지문 이름(raw-<종목>-<sha256 앞 16자>.tar)으로 릴리스에 올림 — 덮어쓰기 안 함.
#    같은 이름이 이미 있으면 크기까지 같을 때만 '이미 있음'으로 보고, 다르면 멈춤.
# 2) 올린 자산의 이름 · 크기를 릴리스 목록에서 다시 확인한 뒤에만 raw-assets.jsonl에 적고 ZIP을 지움.
# 3) 그다음 기록을 커밋 · 푸시(세 번 실패하면 멈춤). customer-data가 아직 없으면 빈 저장으로 넘어감.
set -euo pipefail
TAG="${CUSTOMER_TAG:-dart-customers-raw-v1}"
shopt -s nullglob
mkdir -p customer-data
for dir in raw/*/; do
  code=$(basename "$dir")
  files=("$dir"*.zip)
  [ ${#files[@]} -eq 0 ] && continue
  tmp="raw-${code}.tar"
  tar --sort=name --mtime='2000-01-01' --owner=0 --group=0 --numeric-owner -cf "$tmp" -C "$dir" .
  tsha=$(sha256sum "$tmp" | cut -c1-64)
  size=$(stat -c %s "$tmp")
  name="raw-${code}-${tsha:0:16}.tar"
  mv "$tmp" "$name"
  have=$(gh release view "$TAG" --json assets --jq ".assets[] | select(.name==\"$name\") | .size" || true)
  if [ -z "$have" ]; then
    gh release upload "$TAG" "$name"
    have=$(gh release view "$TAG" --json assets --jq ".assets[] | select(.name==\"$name\") | .size")
  fi
  if [ "$have" != "$size" ]; then echo "자산 크기 불일치 $name"; exit 1; fi
  members=$(for f in "${files[@]}"; do printf '%s:%s\n' "$(basename "$f" .zip)" "$(sha256sum "$f" | cut -c1-64)"; done | paste -sd, -)
  printf '{"asset":"%s/%s","tar_sha256":"%s","bytes":%s,"code":"%s","run":"%s","attempt":"%s","zips":"%s"}\n' \
    "$TAG" "$name" "$tsha" "$size" "$code" "${GITHUB_RUN_ID:-local}" "${GITHUB_RUN_ATTEMPT:-1}" "$members" >> customer-data/raw-assets.jsonl
  rm -f "$name" "${files[@]}"
done
git add -A customer-data
git diff --cached --quiet && exit 0
git commit -q -m "DART 주요 매출처 원문 문단 수집(판 3 · 이어 받기)"
for i in 1 2 3; do
  if git pull --rebase -q origin "$GITHUB_REF_NAME" && git push -q origin "HEAD:$GITHUB_REF_NAME"; then exit 0; fi
  sleep 5
done
echo "푸시 실패"; exit 1
