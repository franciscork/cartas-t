#!/usr/bin/env python3
"""Measure test suite timing in fast and slow modes.

Run with: PYTHONIOENCODING=utf-8 python _measure_suite_timing.py
"""
import glob
import os
import time
import unittest


def _run_suite(env_value):
    if env_value is not None:
        os.environ["RUN_SLOW_TESTS"] = env_value
    else:
        os.environ.pop("RUN_SLOW_TESTS", None)
    start = time.perf_counter()
    loader = unittest.TestLoader()
    suite = loader.discover(".", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start
    return result, elapsed


def _run_one(name, env_value):
    if env_value is not None:
        os.environ["RUN_SLOW_TESTS"] = env_value
    else:
        os.environ.pop("RUN_SLOW_TESTS", None)
    start = time.perf_counter()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(name)
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    elapsed = time.perf_counter() - start
    return result, elapsed


print("=" * 60)
print("SIMMOON Test Suite — Timing Harness")
print("=" * 60)
print()

# 1) FAST suite
print(">>> FAST suite (no RUN_SLOW_TESTS) <<<")
r_fast, t_fast = _run_suite(None)
print(f"  tests_run = {r_fast.testsRun}")
print(f"  skipped   = {len(r_fast.skipped)}")
print(f"  failures  = {len(r_fast.failures)}")
print(f"  errors    = {len(r_fast.errors)}")
print(f"  ok        = {r_fast.wasSuccessful()}")
print(f"  elapsed   = {t_fast:.3f}s ({int(t_fast*1000)}ms)")
print()

# 2) SLOW suite
print(">>> SLOW suite (RUN_SLOW_TESTS=1) <<<")
r_slow, t_slow = _run_suite("1")
print(f"  tests_run = {r_slow.testsRun}")
print(f"  skipped   = {len(r_slow.skipped)}")
print(f"  failures  = {len(r_slow.failures)}")
print(f"  errors    = {len(r_slow.errors)}")
print(f"  ok        = {r_slow.wasSuccessful()}")
print(f"  elapsed   = {t_slow:.3f}s ({int(t_slow*1000)}ms)")
print(f"  delta     = +{t_slow - t_fast:.3f}s (+{int((t_slow-t_fast)*1000)}ms)")
print()

# 3) Per-file (fast)
print(">>> Per-file timing (FAST) <<<")
total = 0.0
for f in sorted(glob.glob("test_*.py")):
    name = f[:-3]  # strip .py
    r, elapsed = _run_one(name, None)
    total += elapsed
    status = "OK" if r.wasSuccessful() else "FAIL"
    print(f"  {f}: {elapsed*1000:.0f}ms  "
          f"({r.testsRun} tests, {len(r.skipped)} skipped, {status})")
print(f"  ----")
print(f"  sum of per-file = {total:.3f}s "
      f"(discover overhead: {t_fast - total:.3f}s)")
print()

# 4) 1MB test isolated
print(">>> 1MB test isolated (RUN_SLOW_TESTS=1) <<<")
r_1mb, t_1mb = _run_one("test_build_markdown_factorygames.test_extreme_content_1mb", "1")
print(f"  elapsed = {t_1mb:.3f}s")
print(f"  ok      = {r_1mb.wasSuccessful()}")
print()

print("=" * 60)
print("Summary")
print("=" * 60)
print(f"FAST suite:  {int(t_fast*1000):>6}ms  ({r_fast.testsRun} tests, {len(r_fast.skipped)} skipped)")
print(f"SLOW suite:  {int(t_slow*1000):>6}ms  ({r_slow.testsRun} tests, {len(r_slow.skipped)} skipped)")
print(f"  1MB test:  {int(t_1mb*1000):>6}ms  (isolated)")
print(f"  delta:    +{int((t_slow-t_fast)*1000):>5}ms  "
      f"({100*(t_slow-t_fast)/t_fast:.1f}% slower)")
