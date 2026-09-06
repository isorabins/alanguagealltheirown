#!/usr/bin/env bash
# One public turn: run it, commit it, push it. Fired by language-loop.timer every 15 minutes.
# Body lives in main() so bash parses the WHOLE file before executing a line — the mid-run
# `git pull` below can rewrite this script on disk, and without the wrap bash keeps reading
# the old buffered bytes at shifted offsets (turn 76 ran a stale script exactly this way).
set -e
record_turn() {
  # Stage only loop-owned public state, never local journals or unrelated code.
  local paths=() f
  for f in state/conversation.json state/rulebook.json state/meta.json \
    state/conversations.json state/public-collaboration.json state/public-runtime.json \
    state/public-language.json state/public-exam-progress.json state/pending-notice.txt \
    viewer/bootstrap.js viewer/preview.json viewer/state.js; do
    if [ -f "$f" ] || git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then paths+=("$f"); fi
  done
  if [ "${#paths[@]}" -gt 0 ]; then git add -A -- "${paths[@]}"; fi
  if [ "${#paths[@]}" -gt 0 ] && ! git diff --cached --quiet -- "${paths[@]}"; then
    local turn
    turn=$(python3 -c 'import json; c=json.load(open("state/conversation.json")); print(c[-1]["turn"] if c else 0)')
    git -c user.name="language-loop" -c user.email="isorabins@gmail.com" commit --only -qm "turn $turn" -- "${paths[@]}"
  fi
}
main() {
  cd "$(dirname "$0")"
  git rebase --abort 2>/dev/null || true              # clear any wreckage from a prior interrupted run
  # Recover complete interrupted work before Git requires a clean checkout.
  python3 loop.py --recover >> state/loop.log 2>&1
  record_turn
  git pull --rebase -X theirs -q origin main          # replay local turns onto remote code; generated-state races resolve to newest turn
  if [ "$(git rev-list --count origin/main..HEAD)" -gt 0 ]; then git push -q origin main; fi
  timeout 8s python3 collab_sync.py pull >> state/collaboration-sync.log 2>&1 || true
  python3 loop.py --turns 1 >> state/loop.log 2>&1
  timeout 8s python3 collab_sync.py push >> state/collaboration-sync.log 2>&1 || true
  record_turn
  git push -q origin main
}
main "$@"
