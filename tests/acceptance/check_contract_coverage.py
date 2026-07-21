#!/usr/bin/env python3
"""Fail when a canonical FR/SC loses explicit task traceability."""
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
spec = (ROOT / "specs/001-experiment-repair/spec.md").read_text()
tasks = (ROOT / "specs/001-experiment-repair/tasks.md").read_text()
requirements = sorted(set(re.findall(r"\b(?:FR|SC)-\d{3}\b", spec)))
missing = [key for key in requirements if key not in tasks]
task_ids = re.findall(r"^- \[[ Xx]\] (T\d{3})\b", tasks, re.M)
expected = [f"T{i:03d}" for i in range(1, 149)]
if missing:
    raise SystemExit("requirements missing from task traceability: " + ", ".join(missing))
if task_ids != expected:
    raise SystemExit("task ids are not the exact sequential T001-T148 set")
print(f"PASS: {len(requirements)} requirements traced; {len(task_ids)} sequential tasks present")
