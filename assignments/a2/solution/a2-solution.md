# Assignment #2: Solution walkthrough

This walkthrough builds the solution to [Assignment #2](../a2.md) in the order of the assignment, one step at a time. Each step shows the code, explains the choices that matter, and ends with **Check it**: what to run, and what you should see. Every number below comes from running these exact files on gem5 v25.0.0.1.

The finished files are next to this one:

| File | What it is |
|---|---|
| `shadow-unit/` | the finished unit: `ShadowUnit.py`, `shadow_unit.hh`, `shadow_unit.cc`, `SConscript` |
| `a2_components.py`, `a2_script.py` | the finished configuration files |
| `cpu-side/src/cpu/o3/` | Part 5: `iew.hh`, `iew.cc`, and `commit.cc` with speculation implemented |
| `run_a2.sh`, `check_a2.py` | run every checkpoint configuration, then check the results against the checkpoint tables |

`shadow_unit.cc` in `shadow-unit/` is the version at the end of Part 3. The Part 1 and Part 2 versions of its functions are shown in full below, in the steps that write them. The unit is modeled on the O3 CPU's functional units: its lanes work like `FUPool`, and its `ShadowCompletion` event like `FUCompletion`.

## Setup

The commands below assume this layout, as in the bootcamp, with `gem5` an alias for `gem5/build/ALL/gem5.opt`:

```txt
gem5/                    gem5 v25.0.0.1
starter_files/           this assignment's starter files
workspace/
├── a2_components.py     from starter_files/
├── a2_script.py         from starter_files/
└── tests/               from starter_files/
```

Copy the CPU side over gem5's files, and your unit into gem5's source tree:

```bash
cp -r starter_files/cpu-side/src/. gem5/src/
mkdir -p gem5/src/bootcamp
cp -r starter_files/shadow-unit gem5/src/bootcamp/
```

**Check it:**

```bash
git -C gem5 status --short src/cpu
```

```txt
 M src/cpu/SConscript
 M src/cpu/o3/BaseO3CPU.py
 M src/cpu/o3/commit.cc
 M src/cpu/o3/cpu.cc
 M src/cpu/o3/cpu.hh
 M src/cpu/o3/dyn_inst.hh
 M src/cpu/o3/iew.cc
 M src/cpu/o3/iew.hh
?? src/cpu/BaseShadowUnit.py
?? src/cpu/base_shadow_unit.hh
```

If `git status` lists any other file under `src/cpu`, that file was changed before, and the build may not behave like the numbers below.

The starter `SConscript` in `shadow-unit/` registers nothing yet, so gem5 builds with the unit's starter files in place. You can build right away for Part 0.

## Part 0: Baseline

Build gem5, then run the five programs without a shadow unit. `-re` puts gem5's output and the program's output in `simout.txt`, in each run's directory:

```bash
cd gem5 && scons build/ALL/gem5.opt -j$(nproc) && cd ../workspace
for p in chain_add chain_mul chain_div indep_add kernel; do
    gem5 -re -d m5out/$p-base a2_script.py --binary tests/$p
done
```

This shell function prints the stats the checkpoints use, for one or more runs. The rest of the walkthrough uses it:

```bash
show() {
    for run in "$@"; do
        echo "== $run"
        grep -E '^simInsts |core\.(numCycles|cpi|ipc|shadow[A-Za-z]+|faults[A-Za-z]+) |shadowUnit\.[A-Za-z]+ ' \
            m5out/$run/stats.txt | awk '{sub("board.processor.cores.core.", "", $1); print "  " $1, $2}'
        grep -h checksum m5out/$run/simout.txt
    done
}
show chain_add-base
```

**Check it:**

```txt
== chain_add-base
  simInsts 1320330
  numCycles 1282221
  cpi 0.971137
  ipc 1.029721
  shadowChecks 0
  shadowReplays 0
  shadowSquashes 0
  shadowCommitStalls 0
  faultsInjected 0
  faultsCommitted 0
checksum: 0x0000000000138800
```

| Program | `simInsts` | `numCycles` | CPI | IPC | Checksum |
|---|---|---|---|---|---|
| `chain_add` | 1,320,330 | 1,282,221 | 0.971 | 1.030 | `0x0000000000138800` |
| `chain_mul` | 264,337 | 770,255 | 2.914 | 0.343 | `0x04614d0adc06a003` |
| `chain_div` | 53,136 | 1,026,020 | 19.31 | 0.052 | `0x0123456789abcdef` |
| `indep_add` | 1,320,344 | 222,615 | 0.169 | 5.931 | `0x0000000000138800` |
| `kernel` | 580,370 | 242,519 | 0.418 | 2.393 | `0xf28b70ce0a5a83ce` |

The chains run at L cycles per chained instruction, and the 2 instructions of loop control in every 66 bring the CPI to about 64/66 of L. `indep_add` comes close to 6 instructions per cycle, not 8: the default functional unit pool has 6 integer ALUs. If your numbers differ from these, check `git status` in gem5 (see [Setup](#setup)) and that `tests/` holds the provided programs.

Every program prints one checksum line, and every later run must print the same one. `kernel`'s is the one Part 3 checks.

## Part 1: The module

### Step 1.1: The declaration

```python
from m5.objects.BaseShadowUnit import BaseShadowUnit
from m5.params import *


class ShadowUnit(BaseShadowUnit):
    type = "ShadowUnit"
    cxx_header = "bootcamp/shadow-unit/shadow_unit.hh"
    cxx_class = "gem5::ShadowUnit"

    num_lanes = Param.Unsigned("Number of shadow executions in flight at once")
    compare_latency = Param.Cycles("Latency of the comparator")
    fault_period = Param.Unsigned(
        0, "Corrupt about one in this many shadow results (0: never)"
    )
    fault_seed = Param.Unsigned(1, "Seed for the shadow fault injector")
```

- A parameter declared with only a description has no default, so gem5 won't create the unit unless the script sets it. That's what you want for `num_lanes` and `compare_latency`: there's no sensible default for either.
- `Param.Cycles` makes `params.compare_latency` a `Cycles` in C++, the type `clockEdge()` takes, so the header can store it as `const Cycles compareLatency`.
- The fault parameters default to "off", so Parts 1 and 2 never see a fault in S.

**Check it:** nothing builds until Step 1.4. Then gem5 generates a C++ struct from this declaration, `ShadowUnitParams`, and the constructor reads it:

```bash
grep -A 8 'struct ShadowUnitParams' gem5/build/ALL/params/ShadowUnit.hh
```

```txt
struct ShadowUnitParams
    : public BaseShadowUnitParams
{
    gem5::ShadowUnit * create() const;
    Cycles compare_latency;
    unsigned fault_period;
    unsigned fault_seed;
    unsigned num_lanes;
};
```

There's one member for each parameter, with the C++ type of its `Param` type. `ShadowUnitParams` extends `BaseShadowUnitParams`, because `ShadowUnit` extends `BaseShadowUnit` in Python.

### Step 1.2: The header

`shadow_unit.hh` is complete. Its lanes copy the O3 CPU's functional units:

| `ShadowUnit` | O3 CPU | |
|---|---|---|
| `laneBusy` | `FUPool::unitBusy` | `src/cpu/o3/fu_pool.hh` |
| `getLane()`, `NoFreeLane` | `FUPool::getUnit()`, `FUPool::NoFreeFU` | `src/cpu/o3/fu_pool.cc` |
| `ShadowCompletion`, with `check`, `lane`, and `unit` | `FUCompletion`, with `inst`, `fuIdx`, and `iqPtr` | `src/cpu/o3/inst_queue.hh` |
| `processShadowDone(check, lane)` | `InstructionQueue::processFUCompletion(inst, fu_idx)` | `src/cpu/o3/inst_queue.cc` |

`ShadowCompletion` is nested in `ShadowUnit`, like `FUCompletion` in `InstructionQueue`, so its `process()` can call the unit's private `processShadowDone()`.

### Step 1.3: The source

**`ShadowCompletion`.** The constructor and `description()` come with the skeleton:

```c++
ShadowUnit::ShadowCompletion::ShadowCompletion(ShadowCheck *_check,
    int _lane, ShadowUnit *_unit)
    : Event(Default_Pri, AutoDelete),
      check(_check), lane(_lane), unit(_unit)
{
}

void
ShadowUnit::ShadowCompletion::process()
{
    unit->processShadowDone(check, lane);
}
```

- `process()` is the one line to write. It hands the event's check and lane back to the unit, as `FUCompletion::process()` calls `iqPtr->processFUCompletion(inst, fuIdx)`.
- `AutoDelete` makes gem5 delete the event after `process()` returns (`Event::release()` in `src/sim/eventq.cc`), so the unit never deletes it.
- The priority is `Default_Pri` (0), where `FUCompletion` uses `Stat_Event_Pri` (90). `FUCompletion` is scheduled one cycle early and runs after the CPU's tick; `ShadowCompletion` runs at the edge of cycle T+L, before it. Both take effect in the same cycle. Giving `ShadowCompletion` priority 90 *and* scheduling it at T+L would hold every lane a cycle too long.

**The constructor:**

```c++
ShadowUnit::ShadowUnit(const ShadowUnitParams &params)
    : BaseShadowUnit(params),
      numLanes(params.num_lanes),
      compareLatency(params.compare_latency),
      faultPeriod(params.fault_period),
      rng(Random::genRandom(params.fault_seed)),
      laneBusy(params.num_lanes, false),
      stats(this)
{
    fatal_if(numLanes == 0, "%s: num_lanes must be at least 1.", name());
}
```

- C++ initializes members in the order the header declares them, whatever order the list is written in, so the list follows that order. Written in another order, it compiles with a `-Wreorder` warning, and a member that reads another one could read it before it's initialized.
- `laneBusy(params.num_lanes, false)` makes one flag per lane, all free.
- `num_lanes = 0` is a mistake in the configuration, not a bug in gem5, so it's a `fatal_if`. A unit with no lanes would reject every check, and the CPU would offer the first one forever.

**`getLane()`:**

```c++
int
ShadowUnit::getLane()
{
    for (unsigned lane = 0; lane < numLanes; ++lane) {
        if (!laneBusy[lane]) {
            laneBusy[lane] = true;
            return lane;
        }
    }
    return NoFreeLane;
}
```

`FUPool::getUnit()` does the same with two extras the lanes don't need. It first checks that some FU can run the op class at all, since every lane can run every instruction. And it starts its search at a different FU each time, round robin, which makes no difference to timing here because all lanes are identical.

**`requestCheck()`, Part 1 version:**

```c++
bool
ShadowUnit::requestCheck(ShadowCheck *check)
{
    int lane = getLane();
    panic_if(lane == NoFreeLane, "%s: no free lane; run Part 1 with more "
             "lanes.", name());

    // S holds its lane for L cycles, like an unpipelined FU.
    schedule(new ShadowCompletion(check, lane, this),
             clockEdge(check->latency));
    ++stats.checks;
    stats.laneCycles += check->latency;

    DPRINTF(ShadowUnit, "[sn:%llu] S starts on lane %d, done in %llu "
            "cycles\n", check->seqNum, lane, uint64_t(check->latency));
    return true;
}
```

- This is the `new FUCompletion` code in `InstructionQueue::scheduleReadyInsts()`, for one check: a new event that carries the check and its lane, scheduled for the cycle S finishes.
- The CPU calls `requestCheck()` from its tick, at the clock edge of cycle T, so `clockEdge(check->latency)` is the edge of cycle T+L.
- Every check gets its own event, so checks with different latencies need nothing special: a `div` and an `add` in flight at once each finish at their own tick.
- The `panic_if` stands in for Part 2's rejection. With `--lanes 64`, it never fires.
- No verdict goes out from here. The CPU side panics if one does (rule 4 and the `inRequestCheck` check in `IEW::recvVerdict()`).

**`processShadowDone()`, Part 1 version:**

```c++
void
ShadowUnit::processShadowDone(ShadowCheck *check, int lane)
{
    // S is done, so its lane is free.
    laneBusy[lane] = false;

    // Part 1: S always agrees with P, so its verdict goes out right away.
    check->match = true;
    ++stats.passes;

    DPRINTF(ShadowUnit, "[sn:%llu] S done on lane %d, verdict: match\n",
            check->seqNum, lane);
    sendVerdict(check);
}
```

- Freeing the lane here matches an unpipelined FU, which `processFUCompletion()` frees when its `FUCompletion` runs. O3 frees it through `freeUnitNextCycle()`, and the FU is actually free when IEW's next tick calls `processFreeUnits()`, at the start of cycle T+L. Freeing the lane in an event that runs before the CPU's tick in cycle T+L has the same effect.
- Each event handles exactly one check, so there's no loop and no re-arming. Two checks that finish at the same tick have two events.

Leave `processCompareDone()` empty until Part 2.

### Step 1.4: The SConscript

```python
Import("*")

SimObject("ShadowUnit.py", sim_objects=["ShadowUnit"])

Source("shadow_unit.cc")

DebugFlag("ShadowUnit", "Shadow unit checks and verdicts")
```

**Check it:** rebuild gem5, and check the parameter struct from Step 1.1. Then check that gem5 knows the debug flag:

```bash
cd gem5 && scons build/ALL/gem5.opt -j$(nproc) && cd ../workspace
gem5 --debug-help | grep ShadowUnit
```

```txt
    ShadowUnit: Shadow unit checks and verdicts
```

Before this step, any run with `--lanes` above 0 stops with `ModuleNotFoundError: No module named 'm5.objects.ShadowUnit'`: the starter `SConscript` doesn't register the unit, so gem5 doesn't know about it. If the build fails in `shadow_unit.cc` instead, check the constructor: every `const` member and both events must be initialized in its list.

### Step 1.5: Connect it

In `a2_components.py`, the CPU's `shadowUnit` parameter takes the unit:

```python
class ShadowO3CPU(RiscvO3CPU):
    def __init__(self, shadow_unit=None):
        super().__init__()
        if shadow_unit is not None:
            self.shadowUnit = shadow_unit
```

In `a2_script.py`, the unit's four parameters come from the command line:

```python
    shadow_unit = ShadowUnit(
        num_lanes=args.lanes,
        compare_latency=args.compare_latency,
        fault_period=args.shadow_fault_period,
        fault_seed=args.seed,
    )
```

`a2_script.py` only creates the unit when `--lanes` is above 0, so with `--lanes 0` the CPU keeps its default, `NULL`, and the run is the baseline.

**Check it:** a run with `--lanes 0` must match its Part 0 run cycle for cycle, and a run with a unit must show the unit in `config.ini`, as a child of the CPU:

```bash
gem5 -re -d m5out/chain_add-l0 a2_script.py --binary tests/chain_add --lanes 0
diff <(grep -v host m5out/chain_add-base/stats.txt) <(grep -v host m5out/chain_add-l0/stats.txt) && echo identical
```

```txt
identical
```

The `host` stats measure the machine that ran gem5, such as its wall-clock time, so they differ between any two runs. Every other stat must match.

Once a run with a unit finishes (Step 1.6), check its `config.ini`:

```bash
grep -A 9 '^\[board.processor.cores.core.shadowUnit\]' m5out/chain_mul-p1/config.ini
grep '^shadowUnit=' m5out/chain_mul-p1/config.ini m5out/chain_mul-base/config.ini
```

```txt
[board.processor.cores.core.shadowUnit]
type=ShadowUnit
children=power_state
clk_domain=board.clk_domain
compare_latency=0
eventq_index=0
fault_period=0
fault_seed=1
num_lanes=64
power_model=
m5out/chain_mul-p1/config.ini:shadowUnit=board.processor.cores.core.shadowUnit
m5out/chain_mul-base/config.ini:shadowUnit=Null
```

The unit's path, `board.processor.cores.core.shadowUnit`, shows that it's a child of the CPU, and its `clk_domain` is the CPU's. Its parameters are the ones from the command line, and the baseline's CPU has no unit.

### Step 1.6: Run it

```bash
for p in chain_add chain_mul chain_div indep_add kernel; do
    gem5 -re -d m5out/$p-p1 a2_script.py --binary tests/$p --lanes 64
done
show chain_add-p1 chain_mul-p1 chain_div-p1 indep_add-p1 kernel-p1
```

**Check it:**

| Program | Part 0 | Part 1 | Expected | `checks`, `passes`, and `shadowChecks` |
|---|---|---|---|---|
| `chain_add` | CPI 0.971 | CPI 1.941 | 2L = 2 (−3.0%) | 1,300,286 |
| `chain_mul` | CPI 2.914 | CPI 5.819 | 2L = 6 (−3.0%) | 260,294 |
| `chain_div` | CPI 19.31 | CPI 38.58 | 2L = 40 (−3.5%) | 52,287 |
| `indep_add` | IPC 5.931 | IPC 4.094 | 4 (+2.3%) | 1,300,367 |
| `kernel` | IPC 2.393 | IPC 1.312 | | 560,393 |

Every program prints its baseline checksum. `rejections` and `mismatches` are 0, and in each run, `checks`, `passes`, and the CPU's `shadowChecks` are the same number: no check was still in flight when the program exited. The chains are 3% below 2L for the same reason as in Part 0, and `indep_add` is 2% above 4 because its loop control runs alongside the chains.

`chain_mul` and `chain_div` also show a large `shadowCommitStalls`: 768,004 and 1,024,015 cycles, half of each run. That's L cycles per chained instruction: of the 2L cycles each one takes, the oldest instruction spends L waiting for its verdict.

Then trace a short window of `chain_mul`, with the command from the assignment:

```bash
gem5 -d m5out/chain_mul-trace --debug-flags=ShadowUnit --debug-file=trace.out \
    --debug-start=10000000 --debug-end=10020000 \
    a2_script.py --binary tests/chain_mul --lanes 64
head -6 m5out/chain_mul-trace/trace.out
```

```txt
10000323: board.processor.cores.core.shadowUnit: [sn:5722] S done on lane 0, verdict: match
10001322: board.processor.cores.core.shadowUnit: [sn:5723] S starts on lane 0, done in 3 cycles
10002321: board.processor.cores.core.shadowUnit: [sn:5723] S done on lane 0, verdict: match
10003320: board.processor.cores.core.shadowUnit: [sn:5724] S starts on lane 0, done in 3 cycles
10004319: board.processor.cores.core.shadowUnit: [sn:5724] S done on lane 0, verdict: match
10005318: board.processor.cores.core.shadowUnit: [sn:5725] S starts on lane 0, done in 3 cycles
```

A cycle is 333 ticks, so divide by 333 to get cycles. The `mul` `[sn:5723]` asks for its check in cycle 30034, T, and its verdict goes back in cycle 30037, T+L: there's no comparator yet, so C = 0. The next `mul` in the chain, `[sn:5724]`, executes and asks for its check in cycle 30040: 2L = 6 cycles after `[sn:5723]`.

Each `mul` takes lane 0 again: its lane is free by the time the next `mul` in the chain executes. Further on, the loop's `addi`, `[sn:5795]`, runs while a `mul` is still in lane 0, and takes lane 1.

## Part 2: Lanes and the comparator

Part 2 changes `requestCheck()` and `processShadowDone()`, and writes `processCompareDone()`.

**`requestCheck()`:** the `panic_if` becomes a rejection:

```c++
    int lane = getLane();
    if (lane == NoFreeLane) {
        DPRINTF(ShadowUnit, "[sn:%llu] rejected: all %u lanes busy\n",
                check->seqNum, numLanes);
        ++stats.rejections;
        return false;
    }
```

This is the `NoFreeFU` case in `scheduleReadyInsts()`: the instruction queue counts it in `fuBusy`, leaves the instruction ready, and tries again next cycle. Here the CPU keeps the check and offers it again next cycle, so the unit doesn't store it. `rejections` counts offers, not checks. The CPU offers its oldest waiting check again every cycle and stops at the first rejection, so `rejections` is about the number of cycles in which a check had to wait.

**`processShadowDone()`:** S finishes and frees its lane, and the check enters the comparator:

```c++
void
ShadowUnit::processShadowDone(ShadowCheck *check, int lane)
{
    // S is done, so its lane is free.
    laneBusy[lane] = false;

    check->shadow = check->golden;

    DPRINTF(ShadowUnit, "[sn:%llu] S done on lane %d, comparing\n",
            check->seqNum, lane);

    // The comparator is pipelined: each check gets its own event.
    schedule(new EventFunctionWrapper([this, check] {
                 processCompareDone(check);
             }, name() + ".compareDone", true),
             clockEdge(compareLatency));
}
```

- The comparator is pipelined, so it needs no busy flags: every check simply gets an event C cycles later. That's how O3 handles a pipelined FU, too: one `FUCompletion` per instruction, with the FU freed the cycle after issue instead of at completion.
- The comparison event is an `EventFunctionWrapper`, as in the event-driven simulation lesson. Its lambda captures `check`, so it plays the role of `ShadowCompletion`'s `check` member, and the third argument, `true`, makes it `AutoDelete`. A second event class would work just as well.
- With C = 0, `clockEdge(compareLatency)` is the current tick. The event runs right after `ShadowCompletion`, still before the CPU's tick: it has the default priority, 0, and the CPU's tick has 50. So C = 0 needs no special case.

**`processCompareDone()`:** compare, count, and send the verdict:

```c++
void
ShadowUnit::processCompareDone(ShadowCheck *check)
{
    check->match = (check->shadow == check->primary);
    if (check->match) {
        ++stats.passes;
    } else {
        ++stats.mismatches;
    }

    DPRINTF(ShadowUnit, "[sn:%llu] verdict: %s\n", check->seqNum,
            check->match ? "match" : "MISMATCH");
    sendVerdict(check);
}
```

The comparison is against `primary`, P's result as the core wrote it, not `golden`. Comparing `shadow` with `golden` would pass every check that only P got wrong.

**Check it:**

```bash
for n in 1 2 3 4 6 8; do
    gem5 -re -d m5out/indep_add-n$n a2_script.py --binary tests/indep_add --lanes $n
done
for p in chain_add chain_mul chain_div; do
    gem5 -re -d m5out/$p-n1 a2_script.py --binary tests/$p --lanes 1
done
gem5 -re -d m5out/chain_add-c2 a2_script.py --binary tests/chain_add --lanes 1 --compare-latency 2
```

| Run | Measured | Expected |
|---|---|---|
| `indep_add`, n = 1 | IPC 1.014 | about 1 |
| `indep_add`, n = 2 | IPC 2.023 | about 2 |
| `indep_add`, n = 3 | IPC 3.028 | |
| `indep_add`, n = 4 | IPC 4.029 | |
| `indep_add`, n = 6 | IPC 4.094 | |
| `indep_add`, n = 8 | IPC 4.094 | Part 1: 4.094 |
| `chain_add`, n = 1 | CPI 1.941 | Part 1: 1.941 |
| `chain_mul`, n = 1 | CPI 5.819 | Part 1: 5.819 |
| `chain_div`, n = 1 | CPI 38.58 | Part 1: 38.58 |
| `chain_add`, n = 1, C = 2 | CPI 3.879 | 2L + C = 4 (−3.0%) |

`mismatches` is 0 in every run. With one lane, `indep_add` has 1,300,301 `rejections`: in almost every cycle, one check waits for the lane.

A stronger check: with plenty of lanes and C = 0, the Part 2 unit must give *exactly* the cycle counts of the Part 1 unit, since a lane is always free and the comparison event runs in the same tick as `ShadowCompletion`. Run the five programs with `--lanes 64`, and compare their `numCycles` with the Part 1 runs: 2,562,188, 1,538,111, 2,050,045, 322,526, and 442,461.

In a trace of `indep_add` with one lane, every cycle looks the same:

```bash
gem5 -d m5out/indep_add-n1-trace --debug-flags=ShadowUnit --debug-file=trace.out \
    --debug-start=10000000 --debug-end=10001400 \
    a2_script.py --binary tests/indep_add --lanes 1
head -8 m5out/indep_add-n1-trace/trace.out
```

```txt
10000323: board.processor.cores.core.shadowUnit: [sn:29809] S done on lane 0, comparing
10000323: board.processor.cores.core.shadowUnit: [sn:29809] verdict: match
10000323: board.processor.cores.core.shadowUnit: [sn:29810] S starts on lane 0, done in 1 cycles
10000323: board.processor.cores.core.shadowUnit: [sn:29812] rejected: all 1 lanes busy
10000656: board.processor.cores.core.shadowUnit: [sn:29810] S done on lane 0, comparing
10000656: board.processor.cores.core.shadowUnit: [sn:29810] verdict: match
10000656: board.processor.cores.core.shadowUnit: [sn:29812] S starts on lane 0, done in 1 cycles
10000656: board.processor.cores.core.shadowUnit: [sn:29813] rejected: all 1 lanes busy
```

At each clock edge, the unit's events run first: the `ShadowCompletion` frees the lane, and with C = 0 the comparison event runs right after it and sends the verdict. Then, in the CPU's tick, the oldest waiting check takes the lane, and the next one is rejected. The CPU stops offering checks at the first rejection, so there's one rejection per cycle. (Sequence numbers skip the instructions that aren't checked, such as the loop's branch.)

With C = 2, the comparator shows up between S finishing and the verdict:

```bash
gem5 -d m5out/chain_add-c2-trace --debug-flags=ShadowUnit --debug-file=trace.out \
    --debug-start=10000000 --debug-end=10004000 \
    a2_script.py --binary tests/chain_add --lanes 1 --compare-latency 2
sed -n '2,5p' m5out/chain_add-c2-trace/trace.out
```

```txt
10000989: board.processor.cores.core.shadowUnit: [sn:8165] S starts on lane 0, done in 1 cycles
10001322: board.processor.cores.core.shadowUnit: [sn:8165] S done on lane 0, comparing
10001988: board.processor.cores.core.shadowUnit: [sn:8165] verdict: match
10002321: board.processor.cores.core.shadowUnit: [sn:8166] S starts on lane 0, done in 1 cycles
```

In cycles: the check starts in 30033 (T), S finishes in 30034 (T+L), the verdict goes out in 30036 (T+L+C), and the next `add` asks for its check in 30037, 2L + C = 4 cycles after the first.

## Part 3: Faults

Part 3 adds four lines to `processShadowDone()`, right after S's result is set:

```c++
        check->shadow = check->golden;
        if (faultPeriod > 0 && rng->random<unsigned>(1, faultPeriod) == 1) {
            check->shadow ^= RegVal(1) << 63;
            ++stats.faultsInjected;
        }
```

- `faultPeriod > 0` comes first, so with the injector off the unit never draws a random number, and `random<unsigned>(1, 0)` is never called.
- `RegVal` is 64 bits, so `RegVal(1) << 63` is the top bit. Writing `1 << 63` would shift a 32-bit `int`, which is undefined.

This is the finished `shadow_unit.cc` in `shadow-unit/`.

**Check it:**

```bash
gem5 -re -d m5out/kernel-pf a2_script.py --binary tests/kernel --lanes 4 --cpu-fault-period 1000
gem5 -re -d m5out/kernel-pf-nounit a2_script.py --binary tests/kernel --cpu-fault-period 1000
gem5 -re -d m5out/kernel-sf a2_script.py --binary tests/kernel --lanes 4 --shadow-fault-period 1000
show kernel-pf kernel-pf-nounit kernel-sf
```

| Run | Checksum | Stats |
|---|---|---|
| `kernel-pf`: unit, faults in P | `0xf28b70ce0a5a83ce`, right | CPU `faultsInjected` 590, `mismatches` 590, `shadowReplays` 590, `faultsCommitted` 0 |
| `kernel-pf-nounit`: no unit, faults in P | `0xa301ab7e3a542512`, wrong | `faultsInjected` 88, `faultsCommitted` 87; the program ends after 92,735 instructions, not 580,370 |
| `kernel-sf`: unit, faults in S | `0xf28b70ce0a5a83ce`, right | unit `faultsInjected` 590, `mismatches` 590, `shadowReplays` 590 |

- With the unit, every fault in P is caught: `mismatches` equals the CPU's `faultsInjected`, and every mismatch is replayed.
- Without it, corrupted results commit and the checksum is wrong. The program even ends early, because a corrupted loop counter ends the loop.
- Faults in S are caught too, and each costs a replay, although P was right.
- Both injectors use seed 1 and draw one random number per result, so the two runs happen to corrupt the same number of results, 590.
- Without a unit, 87 of the 88 corrupted results committed. The other one belonged to an instruction that never committed, such as one on a mispredicted path.

## Part 4: Experiments

Part 4 needs no new code, only runs. They're independent of each other, so you can run them in parallel: add `&` at the end of the `gem5` line, and `wait` after the loop.

This Python function reads one stat from a run. The scripts below use it; put them in the same file, or paste this at the top of each:

```python
C = "board.processor.cores.core."


def stat(run, name):
    for line in open(f"m5out/{run}/stats.txt"):
        if line.startswith(name + " "):
            return float(line.split()[1])
    return 0.0  # stats that are 0 can be missing
```

### Step 4.1: Lanes

```bash
for p in indep_add chain_mul kernel; do
    for n in 1 2 3 4 6 8 16; do
        gem5 -re -d m5out/$p-n$n a2_script.py --binary tests/$p --lanes $n
    done
done
```

```python
for p in ["indep_add", "chain_mul", "kernel"]:
    ell = stat(f"{p}-n16", C + "shadowUnit.laneCycles") / stat(f"{p}-n16", "simInsts")
    ipc16 = stat(f"{p}-n16", C + "ipc")
    print(f"{p}: l = {ell:.3f}, IPC with 16 lanes = {ipc16:.3f}")
    for n in [1, 2, 3, 4, 6, 8]:
        model = min(ipc16, n / ell)
        ipc = stat(f"{p}-n{n}", C + "ipc")
        print(f"  n={n}  measured {ipc:.3f}  model {model:.3f}  {ipc / model - 1:+.1%}")
```

**Check it:**

Each cell is the measured IPC, then the model's:

| Program | ℓ | n = 1 | n = 2 | n = 3 | n = 4 | n = 6 | n = 8 |
|---|---|---|---|---|---|---|---|
| `indep_add` | 0.985 | 1.014 / 1.015 | 2.023 / 2.031 | 3.028 / 3.046 | 4.029 / 4.061 | 4.094 / 4.094 | 4.094 / 4.094 |
| `chain_mul` | 2.922 | 0.172 / 0.172 | 0.172 / 0.172 | 0.172 / 0.172 | 0.172 / 0.172 | 0.172 / 0.172 | 0.172 / 0.172 |
| `kernel` | 2.310 | 0.432 / 0.433 | 0.857 / 0.866 | 1.178 / 1.299 | 1.269 / 1.312 | 1.312 / 1.312 | 1.312 / 1.312 |

Only one point is off by more than 5%: `kernel` with n = 3, 9.3% below the model. `chain_mul` never needs more than one lane.

### Step 4.2: Comparator latency

```bash
for p in chain_add chain_mul; do
    for c in 0 1 2 4 8; do
        gem5 -re -d m5out/$p-n16-c$c a2_script.py --binary tests/$p --lanes 16 --compare-latency $c
    done
done
for c in 0 2 4; do
    gem5 -re -d m5out/indep_add-n16-c$c a2_script.py --binary tests/indep_add --lanes 16 --compare-latency $c
done
```

**Check it:**

| C | `chain_add` CPI | 2L + C | `chain_mul` CPI | 2L + C |
|---|---|---|---|---|
| 0 | 1.941 | 2 | 5.819 | 6 |
| 1 | 2.910 | 3 | 6.787 | 7 |
| 2 | 3.879 | 4 | 7.755 | 8 |
| 4 | 5.818 | 6 | 9.692 | 10 |
| 8 | 9.696 | 10 | 13.566 | 14 |

Every point is 3.0% to 3.1% below 2L + C, the 64/66 from the loop control: (2L + C) × 64/66 matches every point to within 0.1%. `indep_add` with 16 lanes measures 4.094, 2.055, and 1.372 for C = 0, 2, and 4, about 2% to 3% above 8 / (2L + C) = 4, 2, and 1.333.

### Step 4.3: The cost of a fault

The runs without faults are the ones from Step 4.2:

```bash
for p in chain_add chain_mul; do
    for c in 0 2 4; do
        gem5 -re -d m5out/$p-n16-c$c-f a2_script.py --binary tests/$p --lanes 16 \
            --compare-latency $c --cpu-fault-period 10000
    done
done
```

```python
for p, L in [("chain_add", 1), ("chain_mul", 3)]:
    for c in [0, 2, 4]:
        lost = stat(f"{p}-n16-c{c}-f", C + "numCycles") - stat(f"{p}-n16-c{c}", C + "numCycles")
        replays = stat(f"{p}-n16-c{c}-f", C + "shadowReplays")
        print(f"{p} C={c}: {lost / replays:.2f} cycles per fault, model L + C = {L + c}")
```

**Check it:**

```txt
chain_add C=0: 0.99 cycles per fault, model L + C = 1
chain_add C=2: 3.00 cycles per fault, model L + C = 3
chain_add C=4: 4.88 cycles per fault, model L + C = 5
chain_mul C=0: 3.00 cycles per fault, model L + C = 3
chain_mul C=2: 5.00 cycles per fault, model L + C = 5
chain_mul C=4: 7.00 cycles per fault, model L + C = 7
```

The runs have 124 faults (`chain_add`) and 23 faults (`chain_mul`). Other seeds give the same numbers to within about 0.1 cycle; for example, `--seed 2` gives 2.89 for `chain_add` with C = 2.

The model: the verdict of the faulty instruction arrives in cycle T+L+C, as a passing verdict would have. Instead of writing the instruction back, the CPU executes it again in that cycle and asks for a new check, whose verdict arrives L + C cycles later. Only then do its dependents wake up, so the chain loses L + C cycles.

## Part 5 (extra): Speculative checking

### Step 5.1: Speculate

Part 5 changes three CPU files in `gem5/src/cpu/o3/`. The solution's versions are in `cpu-side/src/cpu/o3/`; to compare them with the CPU side the students start from:

```bash
diff -u starter_files/cpu-side/src/cpu/o3/iew.cc solution/cpu-side/src/cpu/o3/iew.cc
```

To see where these functions are called, read `IEW::executeInsts()` in the CPU side. When P executes an instruction that's checked, `requestShadowCheck()` sets `inst->shadowPending`. Then:

```c++
            if (inst->shadowPending && !shadowSpeculative) {
                // Base design: hold the result until its check passes.
                updateExeInstStats(inst);
                continue;
            } else if (inst->shadowPending) {
                shadowWriteBackEarly(inst);
            } else {
                inst->setExecuted();

                instToCommit(inst);
            }
```

And when a verdict arrives, `processShadowVerdicts()` drops it if the instruction was squashed, and otherwise calls `shadowVerdictSpeculative()` when speculation is on.

**`IEW::shadowWriteBackEarly()`**, in `iew.cc`: write back right away, as stock gem5 does.

```c++
void
IEW::shadowWriteBackEarly(const DynInstPtr &inst)
{
    // Part 5: write P back now, so its dependents wake up. The instruction
    // stays shadowPending, and commit won't commit it until the verdict.
    inst->setExecuted();
    instToCommit(inst);
}
```

This is the same as the stock path in the `else` branch. The only difference is that `shadowPending` stays set, and commit checks it.

**`Commit::markCompletedInsts()`**, in `commit.cc`: don't mark an instruction ready while its verdict is pending.

```c++
            // Mark the instruction as ready to commit. Shadow checking,
            // Part 5: an instruction still waiting for its verdict can't
            // commit yet; its verdict will mark it.
            if (fromIEW->insts[inst_num]->shadowPending) {
                fromIEW->insts[inst_num]->shadowReachedCommit = true;
            } else {
                fromIEW->insts[inst_num]->setCanCommit();
            }
```

`markCompletedInsts()` sees each instruction once, when IEW's write-back reaches commit. If the verdict already passed, `shadowPending` is clear and the instruction is marked as usual. If not, `shadowReachedCommit` records that the verdict has to mark it.

**`IEW::shadowVerdictSpeculative()`**, in `iew.cc`, with a helper for the squash:

```c++
void
IEW::shadowVerdictSpeculative(const DynInstPtr &inst, bool match)
{
    if (match) {
        inst->shadowPending = false;
        if (inst->shadowReachedCommit)
            inst->setCanCommit();
        return;
    }

    // Leave it shadowPending, so commit can't commit it before the squash
    // reaches commit.
    if (squashDueToShadowMismatch(inst, inst->threadNumber))
        ++cpu->cpuStats.shadowSquashes;
}

bool
IEW::squashDueToShadowMismatch(const DynInstPtr &inst, ThreadID tid)
{
    DPRINTF(IEW, "[tid:%i] [sn:%llu] Shadow mismatch, squashing it and "
            "younger insts, PC: %s\n", tid, inst->seqNum, inst->pcState());

    // Like a memory-order violation: the instruction itself is squashed
    // too, and fetched again from its PC.
    if (!toCommit->squash[tid] ||
            inst->seqNum <= toCommit->squashedSeqNum[tid]) {
        toCommit->squash[tid] = true;
        toCommit->squashedSeqNum[tid] = inst->seqNum;
        set(toCommit->pc[tid], inst->pcState());
        toCommit->mispredictInst[tid] = NULL;
        toCommit->includeSquashInst[tid] = true;
        wroteToTimeBuffer = true;
        fetchRedirect[tid] = true;
        return true;
    }
    return false;
}
```

The helper is declared in `iew.hh`, next to the two functions above:

```c++
    /** Part 5: squash inst and everything younger, and refetch inst.
     *  Returns false if an older squash this cycle already covers it. */
    bool squashDueToShadowMismatch(const DynInstPtr &inst, ThreadID tid);
```

- **The two orders.** If the verdict passes before the instruction reaches commit, clearing `shadowPending` is enough: `markCompletedInsts()` marks it when it gets there. If the verdict comes after, `shadowReachedCommit` is set, and the verdict marks it with `setCanCommit()`.
- **The mismatch.** The squash is a request to commit, through the time buffer, and takes a cycle to get there. Leaving `shadowPending` set guarantees that commit can't retire the wrong result before then.
- **The squash.** IEW asks commit to squash the way `squashDueToMemOrder()` does: `squashedSeqNum` and `includeSquashInst = true` squash the instruction itself and everything younger, and `pc` makes fetch start again at the instruction. It's refetched, executed again, and checked again. A branch squash uses `includeSquashInst = false`, because the branch itself was right; here, the instruction's own result is wrong. There's no mispredicted branch, so `mispredictInst` is `NULL`, and the branch predictor isn't updated.
- **An older squash wins.** If IEW already asked for a squash in this cycle, for an older instruction, it covers this one too, so the request isn't overwritten and isn't counted. That's the same test as in `squashDueToMemOrder()`. Setting `fetchRedirect` keeps a branch that's *younger* than this instruction from replacing the request later in the same cycle, as for a memory-order violation in `executeInsts()`.
- **Squashed instructions.** `processShadowVerdicts()` already drops the verdicts of instructions that were squashed, so `shadowVerdictSpeculative()` never sees one.

**Check it:** rebuild gem5. First, with speculation off, the CPU must behave exactly as before: rerun a few checkpoints from Parts 1 to 3 into new directories, and compare their `numCycles` with the old runs. They must be equal, not just close:

```bash
gem5 -re -d m5out/indep_add-n2-again a2_script.py --binary tests/indep_add --lanes 2
gem5 -re -d m5out/chain_mul-n1-again a2_script.py --binary tests/chain_mul --lanes 1
gem5 -re -d m5out/chain_add-c2-again a2_script.py --binary tests/chain_add --lanes 1 --compare-latency 2
for run in indep_add-n2 chain_mul-n1 chain_add-c2; do
    grep -h core.numCycles m5out/$run/stats.txt m5out/$run-again/stats.txt | awk '{print $2}' | paste -sd' '
done
```

```txt
652702 652702
1538195 1538195
5122194 5122194
```

Then the Part 5 checkpoint:

```bash
for p in chain_add chain_mul chain_div indep_add; do
    gem5 -re -d m5out/$p-spec a2_script.py --binary tests/$p --lanes 64 --speculative
done
gem5 -re -d m5out/kernel-spec-pf a2_script.py --binary tests/kernel --lanes 4 \
    --cpu-fault-period 1000 --speculative
```

| Run | `numCycles` | Baseline |
|---|---|---|
| `chain_add-spec` | 1,282,221 | 1,282,221 |
| `chain_mul-spec` | 770,255 | 770,255 |
| `chain_div-spec` | 1,026,046 | 1,026,020 (+0.003%) |
| `indep_add-spec` | 222,615 | 222,615 |

`kernel-spec-pf` prints the right checksum, `0xf28b70ce0a5a83ce`, and `faultsCommitted` is 0. It has 606 `mismatches` and 605 `shadowSquashes`: one mismatch didn't need a squash of its own: its instruction was already squashed, or an older squash in the same cycle covered it. The CPU's `faultsInjected` is 663. The other 57 corrupted results belonged to instructions that were squashed before the unit took their checks.

`chain_div-spec` still has 1,024,015 `shadowCommitStalls`, as many as in Part 1, but runs at baseline speed (Q5.1).

### Step 5.2: Comparator latency, again

```bash
for p in chain_add indep_add; do
    for c in 0 2 4 8 16 32 64; do
        gem5 -re -d m5out/$p-spec-n16-c$c a2_script.py --binary tests/$p --lanes 16 \
            --compare-latency $c --speculative
    done
done
```

| C | `chain_add` IPC | `indep_add` IPC | `indep_add` `rename.ROBFullEvents` | `indep_add` `rename.IQFullEvents` |
|---|---|---|---|---|
| 0 | 1.030 | 5.931 | 0 | 18,321 |
| 2 | 1.030 | 5.931 | 0 | 18,321 |
| 4 | 1.030 | 5.931 | 0 | 18,321 |
| 8 | 1.030 | 5.931 | 0 | 18,321 |
| 16 | 1.030 | 5.930 | 0 | 18,320 |
| 32 | 1.030 | 4.832 | 33,211 | 0 |
| 64 | 1.030 | 2.721 | 3,271 | 0 |

Little's law gives the predictions. With about IPC × (L + C) instructions waiting for their verdicts in the ROB, `indep_add` fills its 192 entries when 5.93 × (1 + C) ≈ 192, at C ≈ 31. `chain_add` would need C ≈ 185, far beyond this sweep. From C = 32, rename blocks on the full ROB instead of the full instruction queue, and at C = 64 the ROB caps IPC below 192 / (L + C) = 192 / 65 ≈ 2.95. The cycles each instruction spends in the ROB before it executes and after its verdict bring it down to the measured 2.72.

### Step 5.3: The cost of a fault, again

The runs without faults for this step are the ones from Step 5.2, for C = 0, 2, and 4:

```bash
for p in chain_add chain_mul; do
    for c in 0 2 4; do
        gem5 -re -d m5out/$p-spec-n16-c$c-f a2_script.py --binary tests/$p --lanes 16 \
            --compare-latency $c --cpu-fault-period 10000 --speculative
    done
done
for c in 0 2 4; do  # chain_mul wasn't in Step 5.2
    gem5 -re -d m5out/chain_mul-spec-n16-c$c a2_script.py --binary tests/chain_mul --lanes 16 \
        --compare-latency $c --speculative
done
```

```python
for p, L in [("chain_add", 1), ("chain_mul", 3)]:
    for c in [0, 2, 4]:
        lost = (stat(f"{p}-spec-n16-c{c}-f", C + "numCycles")
                - stat(f"{p}-spec-n16-c{c}", C + "numCycles"))
        squashes = stat(f"{p}-spec-n16-c{c}-f", C + "shadowSquashes")
        print(f"{p} C={c}: {lost / squashes:.2f} cycles per fault, so D = {lost / squashes - 2 * L - c:.1f}")
```

```txt
chain_add C=0: 17.82 cycles per fault, so D = 15.8
chain_add C=2: 19.57 cycles per fault, so D = 15.6
chain_add C=4: 21.52 cycles per fault, so D = 15.5
chain_mul C=0: 22.04 cycles per fault, so D = 16.0
chain_mul C=2: 23.38 cycles per fault, so D = 15.4
chain_mul C=4: 25.38 cycles per fault, so D = 15.4
```

**The model.** The faulty instruction executes in cycle T, and its mismatch verdict arrives in cycle V = T+L+C. Without the fault, the next instruction in the chain would have executed in T+L, since with speculation dependents don't wait for verdicts. With it, everything from the faulty instruction on is squashed; the refetched copy issues in V+D and executes in V+D+L, and the next instruction in V+D+2L. The chain loses (V+D+2L) − (T+L) = **2L + C + D** cycles per fault. That's L + D cycles more than a replay in the base design, which loses L + C.

**Measuring D.** Find a mismatch with the `ShadowUnit` flag, then trace the pipeline around it, with the window from the assignment:

```bash
gem5 -d m5out/mm --debug-flags=ShadowUnit --debug-file=trace.out \
    a2_script.py --binary tests/chain_add --lanes 16 --cpu-fault-period 10000 --speculative
grep -m 2 MISMATCH m5out/mm/trace.out
```

The second mismatch is `[sn:6633]`, at tick 2490507. Trace from 150,000 ticks before it to 20,000 after:

```bash
gem5 -d m5out/pipeview --debug-flags=O3PipeView --debug-file=pipeview.out \
    --debug-start=2340507 --debug-end=2510507 \
    a2_script.py --binary tests/chain_add --lanes 16 --cpu-fault-period 10000 --speculative
grep -A 6 ':0x000110f0:' m5out/pipeview/pipeview.out
```

Each record has the tick of every stage. The faulty `add` is at PC `0x110f0`, and its refetched copy is the next record for that PC that was fetched after the mismatch. In cycles from the mismatch verdict:

| Stage | Faulty `add` `[sn:6633]` | Refetched copy `[sn:6749]` |
|---|---|---|
| fetch | −112 | +4 |
| decode | −69 | +13 |
| rename | −68 | +14 |
| dispatch | −63 | +16 |
| issue | −2 | **+16** |
| complete | −1 | +17 |
| retire | squashed | +19 |

So D = 16. Fetch starts again 4 cycles after the verdict, and the refetched instructions get past decode 13 cycles after it. The same trace of a `chain_mul` mismatch gives D = 16 too, with the refetched `mul` completing at +19, L = 3 cycles after it issues. That's 2L + C + 16: 18 cycles per fault for `chain_add` and 22 for `chain_mul` with C = 0. The measurements above are within 0.7 cycles of it.

The faulty `add` was fetched 112 cycles before its verdict, because the instruction queue is full of the chain. O3PipeView only records instructions that it saw being fetched. That's why the trace starts 150,000 ticks, 450 cycles, before the mismatch: a window that starts at the mismatch has no record of the faulty instruction.

### Step 5.4: Break-even

Speculation is faster when it saves more per instruction than it loses per fault. With f faults per committed instruction, the two designs take the same time when

$$\text{CPI}_\text{base} + f \cdot \text{cost}_\text{base} = \text{CPI}_\text{spec} + f \cdot \text{cost}_\text{spec}
\quad\Rightarrow\quad
f = \frac{\text{CPI}_\text{base} - \text{CPI}_\text{spec}}{\text{cost}_\text{spec} - \text{cost}_\text{base}}$$

With C = 0, from Steps 4.2, 4.3, 5.2, and 5.3:

| Program | CPI, base design | CPI, speculation | Cost per fault, base design | Cost per fault, speculation | Break-even f |
|---|---|---|---|---|---|
| `chain_add` | 1.941 | 0.971 | 0.99 | 17.82 | 0.058: 1 fault every 17 instructions |
| `chain_mul` | 5.819 | 2.914 | 3.00 | 22.04 | 0.153: 1 fault every 6.6 instructions |

In the models, the numerator is about L × 64/66 and the denominator is L + D, so f ≈ L / (L + D) × 64/66. Every fault rate in this assignment is far below both. Even a fault period of 50 is about a third of `chain_add`'s break-even rate, and the checkpoints' 1 in 1,000 is 58 times below it.

## Run every checkpoint at once

`run_a2.sh` runs every configuration in the checkpoint tables into `out/`, and `check_a2.py` checks the results with the tolerances from the assignment. Run them from the directory that has `a2_script.py`, `a2_components.py`, and `tests/`, with a gem5 built with the solution's unit and the solution's CPU files. Without Part 5, the Part 5 checks fail, and everything else should pass.

```bash
cp solution/run_a2.sh solution/check_a2.py workspace/
cd workspace
GEM5=../gem5/build/ALL/gem5.opt JOBS=8 ./run_a2.sh
./check_a2.py
```

```txt
PASS  Part 0  chain_add: CPI about 1
PASS  Part 0  chain_mul: CPI about 3
...
PASS  Part 5  CPU faults: right checksum, faultsCommitted = 0
PASS  Part 5  CPU faults: 0 < shadowSquashes <= mismatches

0 check(s) failed
```

All 41 checks pass with the solution.
