#!/usr/bin/env bash
# One public turn: run it, commit it, push it. Fired by language-loop.timer every 15 minutes.
set -e
cd "$(dirname "$0")"
git rebase --abort 2>/dev/null || true              # clear any wreckage from a prior interrupted run
git pull --rebase -X theirs -q origin main          # replay local turns onto remote code; generated-state races resolve to the newest turn
python3 loop.py --turns 1 >> state/loop.log 2>&1
python3 tweet.py >> state/tweet.log 2>&1 || true   # changelog to X; failure never blocks the turn
git add -A
if ! git diff --cached --quiet; then
  T=$(python3 -c 'import json; print(json.load(open("state/conversation.json"))[-1]["turn"])')
  git -c user.name="language-loop" -c user.email="isorabins@gmail.com" commit -qm "turn $T"
  git push -q origin main
fi
