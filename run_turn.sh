#!/usr/bin/env bash
# One public turn: run it, commit it, push it. Fired by language-loop.timer every 15 minutes.
set -e
cd "$(dirname "$0")"
git pull --rebase -q origin main   # pick up engine/prompt changes pushed from the Mac
python3 loop.py --turns 1 >> state/loop.log 2>&1
git add -A
if ! git diff --cached --quiet; then
  T=$(python3 -c 'import json; print(json.load(open("state/conversation.json"))[-1]["turn"])')
  git -c user.name="language-loop" -c user.email="isorabins@gmail.com" commit -qm "turn $T"
  git push -q origin main
fi
