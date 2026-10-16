#!/usr/bin/env python3
"""Compare the runs in out/ with the checkpoint tables of Assignment 2."""
import os
import re
import sys

CORE = "board.processor.cores.core."
UNIT = CORE + "shadowUnit."
cache = {}


class Stats(dict):
    """A missing stat reads as NaN, so every check that uses it fails."""

    def __missing__(self, key):
        return float("nan")


def st(run):
    """The first value of every stat in out/<run>/stats.txt."""
    if run not in cache:
        vals = Stats()
        path = f"out/{run}/stats.txt"
        if not os.path.exists(path):
            print(f"MISSING  {path}")
        else:
            with open(path) as f:
                for line in f:
                    m = re.match(r"(\S+)\s+(-?[\d.]+(?:e[-+]?\d+)?)\s", line)
                    if m:
                        vals.setdefault(m.group(1), float(m.group(2)))
        cache[run] = vals
    return cache[run]


def checksum(run):
    path = f"out/{run}/simout.txt"
    if not os.path.exists(path):
        return [f"<no {path}>"]  # never equal to another run's checksum
    with open(path) as f:
        return [line for line in f if "checksum" in line.lower()]


def close(a, b, tol):
    return abs(a - b) <= tol * abs(b)


failed = 0


def check(ok, what):
    global failed
    failed += not ok
    print(("PASS  " if ok else "FAIL  ") + what)


CHAINS = [("chain_add", 1), ("chain_mul", 3), ("chain_div", 20)]  # (name, L)
MICRO = [p for p, _ in CHAINS] + ["indep_add"]

# Part 0: baseline sanity
for p, lat in CHAINS:
    check(close(st(f"{p}-base")[CORE + "cpi"], lat, 0.10),
          f"Part 0  {p}: CPI about {lat}")
good = checksum("kernel-base")
check(any("checksum" in line.lower() for line in good),
      "Part 0  kernel: prints a checksum")

# Part 1: plenty of lanes, C = 0. Each result is held until its verdict, so
# a dependent chain takes 2L cycles per instruction.
for p, lat in CHAINS:
    check(close(st(f"{p}-p1")[CORE + "cpi"], 2 * lat, 0.05),
          f"Part 1  {p}: CPI within 5% of 2L = {2 * lat}")
check(close(st("indep_add-p1")[CORE + "ipc"], 4, 0.05),
      "Part 1  indep_add: IPC within 5% of 4")
for p in MICRO:
    run = st(f"{p}-p1")
    check(run.get(UNIT + "rejections", 0) == 0
          and run.get(UNIT + "mismatches", 0) == 0,
          f"Part 1  {p}: no rejections, no mismatches")
    check(run[UNIT + "checks"] == run[CORE + "shadowChecks"],
          f"Part 1  {p}: unit and CPU agree on the number of checks")
    check(0 <= run[UNIT + "checks"] - run[UNIT + "passes"] <= 64,
          f"Part 1  {p}: passes = checks, up to checks in flight")

# Part 2: lanes and the comparator
for n in (1, 2):
    check(close(st(f"indep_add-n{n}")[CORE + "ipc"], n, 0.05),
          f"Part 2  indep_add: IPC within 5% of {n} with {n} lanes")
check(close(st("indep_add-n8")[CORE + "ipc"],
            st("indep_add-p1")[CORE + "ipc"], 0.05),
      "Part 2  indep_add: IPC within 5% of Part 1 with 8 lanes")
for p, _ in CHAINS:
    check(close(st(f"{p}-n1")[CORE + "cpi"], st(f"{p}-p1")[CORE + "cpi"],
                0.05),
          f"Part 2  {p}: CPI within 5% of Part 1 with 1 lane")
check(close(st("chain_add-c2")[CORE + "cpi"], 4, 0.05),
      "Part 2  chain_add: CPI within 5% of 2L + C = 4 with 1 lane, C = 2")
part2 = ([f"indep_add-n{n}" for n in (1, 2, 3, 4, 6, 8)]
         + [f"{p}-n1" for p, _ in CHAINS] + ["chain_add-c2"])
check(all(st(r).get(UNIT + "mismatches", 0) == 0 for r in part2),
      "Part 2  no mismatches without faults")

# Part 3: faults
pf, nu, sf = st("kernel-pfaults"), st("kernel-pfaults-nounit"), st("kernel-sfaults")
check(checksum("kernel-pfaults") == good and pf[CORE + "faultsCommitted"] == 0,
      "Part 3  CPU faults, unit on: right checksum, faultsCommitted = 0")
check(0 < pf[UNIT + "mismatches"] <= pf[CORE + "faultsInjected"],
      "Part 3  CPU faults, unit on: 0 < mismatches <= CPU faultsInjected")
check(0 < pf[CORE + "shadowReplays"] <= pf[UNIT + "mismatches"],
      "Part 3  CPU faults, unit on: 0 < shadowReplays <= mismatches")
check(checksum("kernel-pfaults-nounit") != good
      and nu[CORE + "faultsCommitted"] > 0,
      "Part 3  CPU faults, no unit: wrong checksum, faultsCommitted > 0")
check(checksum("kernel-sfaults") == good,
      "Part 3  shadow faults: right checksum")
check(0 <= sf[UNIT + "faultsInjected"] - sf[UNIT + "mismatches"] <= 64,
      "Part 3  shadow faults: every injected fault is a mismatch")
check(0 < sf[CORE + "shadowReplays"] <= sf[UNIT + "mismatches"],
      "Part 3  shadow faults: 0 < shadowReplays <= mismatches")

# Part 5 (extra): speculative checking. Plenty of lanes and C = 0 hide the
# check completely; a mismatch squashes instead of replaying.
for p in MICRO:
    check(close(st(f"{p}-spec")[CORE + "numCycles"],
                st(f"{p}-base")[CORE + "numCycles"], 0.01),
          f"Part 5  {p}: numCycles within 1% of the baseline")
ks = st("kernel-spec-pfaults")
check(checksum("kernel-spec-pfaults") == good
      and ks[CORE + "faultsCommitted"] == 0,
      "Part 5  CPU faults: right checksum, faultsCommitted = 0")
check(0 < ks[CORE + "shadowSquashes"] <= ks[UNIT + "mismatches"],
      "Part 5  CPU faults: 0 < shadowSquashes <= mismatches")

print(f"\n{failed} check(s) failed")
sys.exit(1 if failed else 0)
