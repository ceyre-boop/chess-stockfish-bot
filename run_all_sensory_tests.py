#!/usr/bin/env python3
"""Run all sensory tests sequentially and report results.

This script executes the five test scripts under `tests_live/` using
`subprocess.run`, captures stdout/stderr, and prints a summary of
which tests passed or failed.

Run with:
    python run_all_sensory_tests.py

The script does NOT execute the tests on import; it only defines and
runs them when invoked as __main__.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import os
from typing import Dict, List


TEST_SCRIPTS: List[str] = [
    "tests_live/test_alpaca_intraday.py",
    "tests_live/test_mt5_ticks_and_candles.py",
    "tests_live/test_polygon_daily.py",
    "tests_live/test_multi_provider_alignment.py",
    "tests_live/test_realtime_visualizer.py",
]


def run_test(path: Path) -> Dict[str, object]:
    header = f"=== RUNNING: {path} ==="
    print(header)
    print()

    try:
        # Ensure subprocesses can import local packages by setting PYTHONPATH
        env = os.environ.copy()
        repo_root = Path(__file__).parent.resolve()
        prev = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(repo_root) + (os.pathsep + prev if prev else "")

        completed = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            env=env,
        )
    except Exception as exc:
        print(f"Error launching {path}: {exc}")
        return {"path": str(path), "ok": False, "error": str(exc), "stdout": "", "stderr": ""}

    # Print stdout then stderr in a readable block
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    print("--- STDOUT ---")
    if stdout:
        print(stdout.strip())
    else:
        print("(no stdout)")

    print("--- STDERR ---")
    if stderr:
        print(stderr.strip())
    else:
        print("(no stderr)")

    ok = completed.returncode == 0
    status_line = f"=== RESULT: {'OK' if ok else 'FAIL'} (exit_code={completed.returncode}) ==="
    print()
    print(status_line)
    print()

    return {"path": str(path), "ok": ok, "returncode": completed.returncode, "stdout": stdout, "stderr": stderr}


def main():
    root = Path(__file__).parent.resolve()
    results = []
    for rel in TEST_SCRIPTS:
        script_path = (root / rel).resolve()
        if not script_path.exists():
            print(f"Test script not found: {script_path}")
            results.append({"path": str(script_path), "ok": False, "error": "not found"})
            continue

        res = run_test(script_path)
        results.append(res)

    # Summary
    passed = [r for r in results if r.get("ok")]
    failed = [r for r in results if not r.get("ok")]

    print("\n=== TEST SUITE SUMMARY ===")
    print(f"Total tests: {len(results)}")
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFailed tests:")
        for r in failed:
            print(f" - {r.get('path')} (error/returncode: {r.get('returncode') or r.get('error')})")


if __name__ == '__main__':
    main()
