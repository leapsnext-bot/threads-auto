#!/usr/bin/env bash
# 変更された記録ファイルをGitHubに保存する（ほかの自動処理と同時に動いても大丈夫なように、やり直し付き）
set -e
MSG="$1"; shift
git config user.name "threads-bot"
git config user.email "threads-bot@users.noreply.github.com"
for f in "$@"; do git add -A -- "$f" 2>/dev/null || true; done
if git diff --cached --quiet; then
  echo "保存する変更はありません"
  exit 0
fi
git commit -q -m "$MSG"
for i in 1 2 3 4 5; do
  if git pull -q --rebase origin main && git push -q origin HEAD:main; then
    echo "記録を保存しました"
    exit 0
  fi
  sleep $((i * 5))
done
echo "記録の保存に失敗しました" >&2
exit 1
