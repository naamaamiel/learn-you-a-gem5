# Simulation statistics

Since Unit I, we've been checking our simulations by reading `stats.txt`. Let's look at how gem5 builds that file, and then add statistics of our own to `HelloSimObject`.

> By the end of this section, you will be able to:
>
> - **Navigate** a `stats.txt` file: its dumps, its naming hierarchy, and the parts of each line.
> - **Trace** a statistic back to the code that defines it.
> - **Add** statistics to a SimObject using `statistics::Group` and `ADD_STAT`, with units and descriptions.
> - **Choose** a statistic type that fits what you want to measure.
> - **Dump** and **reset** statistics from a configuration script to measure only part of a simulation.

## Reading `stats.txt`

Debug prints tell us *what happened*, one event at a time. Statistics tell us *how much* happened: counters, rates, and distributions that gem5's models update during simulation and write out at the end. They're how we compare one configuration with another, and they're usually what goes into a paper's plots.

Let's look at the `stats.txt` from the last section's `minor_config.py` run. If you didn't keep yours, there's a copy in `workspace/04-gem5-models/04a-cpus/04-debugging/completed/m5out/stats.txt`.

### Dumps

Every time gem5 writes its statistics, it writes a **dump**: a block of lines between two markers.

```txt
---------- Begin Simulation Statistics ----------
...
---------- End Simulation Statistics   ----------
```

gem5 writes one dump when the simulation ends. If something else asks for a dump earlier, `stats.txt` has more than one block. You saw this in the [communication](../../03-intermediate-features/04-communication.md) and [KVM fast-forwarding](../../05-advanced-topics/01-kvm-fast-forwarding.md) sections, where exit events dumped and reset the statistics. We'll write our own dumps and resets at the end of this section.

> The end-of-simulation dump is set up by `m5.simulate()`. The first time it's called, it registers `stats.dump` to run when gem5 exits (see `gem5/src/python/m5/simulate.py`).

### Lines

Each line has the same parts:

```txt
<name>   <value>   [<percent> <cumulative percent>]   # <description> (<unit>)
```

For example:

```txt
simInsts                                         8700                       # Number of instructions simulated (Count)
board.processor.cores.core.ipc               0.101160                       # IPC: instructions per cycle (core level) ((Count/Cycle))
board.processor.cores.core.branchPred.lookups_0::DirectCond         2534     70.21%     89.14% # Number of BP lookups (Count)
```

- The **name** says where the statistic lives in the simulated system. More on this below.
- The **value** is everything counted since the statistics were last reset. Normally, that's since the start of the simulation.
- The two **percentages** only appear for some statistics, such as the branch predictor lookups above. 70.21% of all lookups were for direct conditional branches, and the branch types listed so far add up to 89.14% of them.
- The **description** and **unit** come from the code that defines the statistic. A unit like `(Count/Cycle)` is a rate: instructions per cycle.

The first lines of every dump are global statistics, such as `simSeconds`, `simTicks`, `simInsts`, and `hostSeconds`. They describe the whole simulation, so they don't belong to any one component.

### Names follow the SimObject tree

Every other name is a path through the tree of SimObjects that your configuration script built. You can see that tree in `config.ini`, where each SimObject lists its `children`:

```txt
[root]
children=board
[board]
children=cache_hierarchy clk_domain dvfs_handler memory processor workload
[board.processor]
children=cores
[board.processor.cores]
children=core
[board.processor.cores.core]
children=branchPred decoder executeFuncUnits interrupts isa mmu power_state tracer workload
```

So `board.processor.cores.core.branchPred.BTBHitRatio` is the statistic `BTBHitRatio` of the SimObject at `board.processor.cores.core.branchPred`: the CPU's branch predictor. The root itself isn't part of the name.

A few more naming rules:

- **Vectors of SimObjects** get a number on each element, but only if there's more than one. The processor in `minor_config.py` has one core, so its path is `board.processor.cores.core`. The `X86DemoBoard` in Unit I had two, so its stats were under `board.processor.cores0` and `board.processor.cores1`.
- **Groups inside a SimObject.** A SimObject can split its statistics into named groups. For example, the CPU keeps per-thread statistics in groups named `commitStats0`, `fetchStats0`, and so on, which gives names like `board.processor.cores.core.commitStats0.numInsts`.
- **`::` splits a statistic into parts.** It can separate:
  - the elements of a vector: `blockedCycles::no_mshrs`, and a `::total` line if the vector asks for one,
  - the summary and buckets of a distribution: `bytesPerActivate::samples`, `::mean`, `::stdev`, `::0-127`, `::128-255`, …,
  - a breakdown by requestor: `l1dcaches.demandHits::processor.cores.core.data` counts the L1 data cache's hits for the core's data accesses.
- **Two-dimensional statistics** combine both: in `lookups_0::DirectCond`, `_0` is the row (thread 0), and `DirectCond` is the column (the branch type).

> **Your turn:** Find the code that defines `board.processor.cores.core.branchPred.BTBHitRatio`. What kind of statistic is it, and how is its value computed?
>
> <details>
> <summary markdown="span"> <b>Answer</b> </summary>
>
> The last part of the name is the statistic's name in the code, so we can search for it:
>
> ```bash
> grep -rn "BTBHitRatio" gem5/src/cpu/pred/
> ```
>
> It's declared in `gem5/src/cpu/pred/bpred_unit.hh`, in `BPredUnit`, the base class of every branch predictor. It's defined in `bpred_unit.cc`:
>
> ```c++
> ADD_STAT(BTBHitRatio, statistics::units::Ratio::get(), "BTB Hit Ratio",
>          BTBHits / BTBLookups),
> ```
>
> It's a **formula**: gem5 divides `BTBHits` by `BTBLookups` when it writes the dump. The path agrees: `branchPred` is the CPU's branch predictor parameter, and `LocalBP` extends `BPredUnit`.
>
> </details>

<br>

### Other output formats

The `--stats-file` option chooses where statistics go, and in what format:

```bash
gem5 --stats-file=my_stats.txt minor_config.py                                    # another file name in m5out/
gem5 --stats-file="text://stats.txt?desc=False&spaces=False" minor_config.py      # no descriptions, no alignment
```

`gem5 --stats-help` lists every format and its options.

> Some of gem5's own documentation separates options with `;`, as in `?desc=False;spaces=False`. Recent versions of Python no longer accept `;` there, so use `&`.

There's also a JSON format (`json://stats.json`), but it has catches:

- It's written to the directory you ran gem5 from, not to `m5out/`.
- It keeps only the last dump.
- It leaves out formulas.

We'll stick with `stats.txt`.

## Statistics in gem5's code

### Every SimObject is a statistics group

Statistics live in **groups**: objects of the class `statistics::Group`, defined in `gem5/src/base/stats/group.hh`. A group holds statistics and other groups, and that nesting is what builds the names in `stats.txt`.

Every SimObject is a group. Here's the start of the `SimObject` class, in `gem5/src/sim/sim_object.hh`:

```c++
class SimObject : public EventManager, public Serializable, public Drainable,
                  public statistics::Group, public Named
```

When you call `m5.instantiate()`, gem5 adds each SimObject's group to its parent's group, under the SimObject's name. So the group tree is the SimObject tree, and the names in `stats.txt` are paths through it.

Most SimObjects don't add statistics to themselves directly. Instead, they declare a struct of statistics that extends `statistics::Group`, and create it with the SimObject as its parent. Here's a shortened version of the branch predictor's, from `gem5/src/cpu/pred/bpred_unit.hh`:

```c++
class BPredUnit : public SimObject
{
    ...
  protected:
    struct BPredUnitStats : public statistics::Group
    {
        BPredUnitStats(BPredUnit *bp);

        statistics::Vector2d lookups;
        ...
        statistics::Scalar BTBLookups;
        statistics::Scalar BTBHits;
        statistics::Formula BTBHitRatio;
        ...
    } stats;
};
```

The struct's constructor calls `statistics::Group(bp)`, without a name, so its statistics are **merged** into the branch predictor's own group. That's why the name is `branchPred.BTBLookups`, and not `branchPred.stats.BTBLookups`. Passing a name as well, as in `statistics::Group(parent, "commitStats0")`, creates a **named subgroup** instead. That's how the CPU's per-thread groups get their names.

### `ADD_STAT`

Each statistic needs a parent group, a name, a unit, and a description. The `ADD_STAT` macro, from `gem5/src/base/stats/group.hh`, fills in the first two for you:

```c++
#define ADD_STAT(n, ...) n(this, #n, __VA_ARGS__)
```

So in a group's constructor, this:

```c++
ADD_STAT(BTBLookups, statistics::units::Count::get(), "Number of BTB lookups"),
```

means "construct `BTBLookups` with this group as its parent, the name `"BTBLookups"`, a unit, and a description". So with `ADD_STAT`, a statistic's name in `stats.txt` is the name of its variable.

A **formula** takes one more argument: the expression it computes, like `BTBHits / BTBLookups` in the answer above.

The unit is one of the classes in `gem5/src/base/stats/units.hh`:

| Unit | Use it for |
|---|---|
| `statistics::units::Count` | numbers of things: instructions, misses, hellos |
| `statistics::units::Cycle`, `Tick`, `Second` | time |
| `statistics::units::Byte`, `Bit` | amounts of data |
| `statistics::units::Ratio` | one count divided by another of the same kind, like a hit rate |
| `statistics::units::Rate<A, B>` | A per B, like `Rate<Count, Cycle>` for IPC |
| `statistics::units::Watt`, `Joule`, `Volt`, `DegreeCelsius` | power models |
| `statistics::units::Unspecified` | only when nothing else fits |

> Older gem5 code, and some of the pages on gem5.org, use `Stats::` instead of `statistics::` and leave out the unit. That's the old interface. New code should use `statistics::` and always give a unit.

### Statistic types

gem5 has several kinds of statistics, all declared in `gem5/src/base/statistics.hh`. These are the ones you'll use most, with an example of each from our `stats.txt`:

| Type | What it records | Example |
|---|---|---|
| `Scalar` | a single counter you update: `++`, `+=`, or `=` | `branchPred.BTBLookups` |
| `Vector` | an array of counters, one per index; `init(n)` sets its size | `l1dcaches.blockedCycles::no_mshrs` |
| `Vector2d` | a two-dimensional array of counters | `branchPred.lookups_0::DirectCond` |
| `Formula` | an expression of other statistics, computed when the stats are dumped | `branchPred.BTBHitRatio`, `core.ipc` |
| `Value` | a value read from a variable or a function when the stats are dumped | `simTicks`, `finalTick` |
| `Distribution` | samples of a quantity, sorted into fixed buckets, with their mean and standard deviation | `l2bus.snoopFanout` |
| `Histogram` | like `Distribution`, but its buckets grow to fit the samples | `dram.bytesPerActivate` |
| `Average` | the average of a quantity over time, per tick | `mem_ctrl.avgRdQLen` |

`statistics.hh` has a few more, such as `SparseHistogram` and `StandardDeviation`.

> Prefer a `Formula` over computing a ratio yourself. A formula is computed at the moment of the dump, from the values that are being dumped, so it's always consistent with them, even after a reset. Also, `Average` is an average *per tick*, not per event: an average latency per request is a `Formula`, total latency divided by the number of requests.

### Configuring statistics

Some statistics need more than a name and a description. These functions configure a statistic, and they return the statistic itself, so you can chain them:

| Function | What it does |
|---|---|
| `init(...)` | sizes a `Vector` (`init(n)`), a `Vector2d` (`init(x, y)`), or a `Distribution` (`init(min, max, bucket_size)`). Required for these types, before their first use. |
| `subname(i, name)`, `ysubnames(names)` | names the elements of a vector, or the columns of a `Vector2d` |
| `flags(...)` | changes how it's printed (see below) |
| `precision(p)` | prints `p` digits after the decimal point |
| `prereq(stat)` | prints it only if `stat` isn't zero |

The flags are defined in `gem5/src/base/stats/info.hh`:

| Flag | Effect |
|---|---|
| `statistics::total` | adds a `::total` line to a vector |
| `statistics::pdf`, `statistics::cdf` | adds the percent and cumulative percent columns |
| `statistics::nozero` | doesn't print it if it's zero |
| `statistics::nonan` | doesn't print it if it's not a number, for example a formula that divides by zero |

The branch predictor configures its vectors in the body of its stats constructor, in `bpred_unit.cc`:

```c++
lookups
    .init(bp->numThreads, enums::Num_BranchType)
    .flags(total | pdf);
lookups.ysubnames(enums::BranchTypeStrings);
```

That's where every detail of `lookups_0::DirectCond 2534 70.21% 89.14%` comes from:
- `init()` makes one row per thread (`_0`) and one column per branch type.
- `ysubnames()` names the columns (`DirectCond`).
- `pdf` adds the two percentages.
- `total` adds the `lookups_0::total` line.

> Configure statistics in the group's constructor, as here, unless the configuration depends on something that isn't ready yet, such as the size of another SimObject. `statistics::Group` also has a `regStats()` method you can override, which gem5 calls after every SimObject has been created.

## Let's add statistics to `HelloSimObject`!

We'll give `HelloSimObject` three statistics:

1. `hellosSaid`, a `Scalar` that counts the hellos it has printed.
2. `hellosLeft`, a `Value` that reports how many are still to come.
3. `helloRate`, a `Formula`: hellos per simulated second.

Start from your `HelloSimObject` at the end of the [event-driven simulation](02-event-driven-sim.md) section, the `EventFunctionWrapper` version, in `gem5/src/bootcamp/hello-sim-object/`. The finished files are in `workspace/04-gem5-models/04a-cpus/04b-statistics/completed/`.

### The header file

First, include the statistics header in `hello_sim_object.hh`:

```c++
#include "base/statistics.hh"
```

Then declare the stats struct as a private member of `HelloSimObject`, after `remainingHellos`:

```c++
  private:
    EventFunctionWrapper nextHelloEvent;
    int remainingHellos;

    struct HelloSimObjectStats : public statistics::Group
    {
        HelloSimObjectStats(HelloSimObject *parent);

        statistics::Scalar hellosSaid;
        statistics::Value hellosLeft;
        statistics::Formula helloRate;
    } stats;
```

This declares the struct and a member named `stats` in one go, like `BPredUnitStats` above.

### The source file

In `hello_sim_object.cc`, construct `stats` in `HelloSimObject`'s constructor, with the `HelloSimObject` as its parent. Members are initialized in the order they're declared, so it goes last:

```c++
HelloSimObject::HelloSimObject(const HelloSimObjectParams& params):
    SimObject(params),
    nextHelloEvent([this](){ processHello(); },
                   name() + "HelloEvent"),
    remainingHellos(params.num_hellos),
    stats(this)
{
    ...
}
```

Next, write the stats struct's constructor. For now, it only adds `hellosSaid`:

```c++
HelloSimObject::HelloSimObjectStats::HelloSimObjectStats(
    HelloSimObject *parent)
    : statistics::Group(parent),
      ADD_STAT(hellosSaid, statistics::units::Count::get(),
               "Number of hellos said")
{
}
```

`statistics::Group(parent)` has no name, so the struct merges into `HelloSimObject`'s group, and the statistic will be called `hello.hellosSaid`.

Last, count each hello in `processHello()`:

```c++
    // Decrement hellos remaining, and count this hello
    remainingHellos--;
    stats.hellosSaid++;
```

> **Your turn:** Add `hellosLeft`. It should report `remainingHellos` whenever the statistics are dumped. Hint: a `Value` gets its value from a function you give it with `functor()`. `simTicks` and `finalTick` are set up this way, in `gem5/src/sim/root.cc`.
>
> <details>
> <summary markdown="span"> <b>Answer</b> </summary>
>
> Add it to the constructor's initializer list, after `hellosSaid`:
>
> ```c++
>       ADD_STAT(hellosLeft, statistics::units::Count::get(),
>                "Number of hellos left to say")
> ```
>
> Then give it a function in the constructor's body. A lambda that captures `parent` can read `remainingHellos`: the stats struct is a member of `HelloSimObject`, so it can use its private members.
>
> ```c++
> {
>     hellosLeft.functor([parent]() { return parent->remainingHellos; });
> }
> ```
>
> </details>

<br>

> **Your turn:** Add `helloRate`, the number of hellos said per simulated second, with the unit `statistics::units::Rate<statistics::units::Count, statistics::units::Second>`. Hint: gem5's `simSeconds` statistic is available to C++ code as `simSeconds`, declared in `gem5/src/sim/stats.hh`.
>
> <details>
> <summary markdown="span"> <b>Answer</b> </summary>
>
> Include the header that declares `simSeconds` in `hello_sim_object.cc`:
>
> ```c++
> #include "sim/stats.hh"
> ```
>
> Then add the formula to the initializer list, after `hellosLeft`. The last argument is the expression:
>
> ```c++
>       ADD_STAT(helloRate, statistics::units::Rate<
>                    statistics::units::Count, statistics::units::Second>::get(),
>                "Hellos said per simulated second",
>                hellosSaid / simSeconds)
> ```
>
> </details>

<br>

### Let's run this thing!

Rebuild gem5, and run `hello_sim_object_config.py`, the configuration script from the event-driven simulation section:

```bash
scons build/ALL/gem5.opt -j$(nproc)
gem5 hello_sim_object_config.py
```

The output is the same as before, but `m5out/stats.txt` now has three new lines (shown here with some of the global statistics):

```txt
simSeconds                               18446744.073710                       # Number of seconds simulated (Second)
simTicks                                 18446744073709551616                       # Number of ticks simulated (Tick)
...
hello.hellosSaid                                    4                       # Number of hellos said (Count)
hello.hellosLeft                                    0                       # Number of hellos left to say (Count)
hello.helloRate                              0.000000                       # Hellos said per simulated second ((Count/Second))
```

`hellosSaid` and `hellosLeft` are right: four hellos said, none left. But `simSeconds` says we simulated for 18 million seconds, and `helloRate` is 0.

That's not a bug in our statistics. `m5.simulate()` without an argument runs until there's nothing left to do. After the last hello at tick 2000, the only event left is the one that ends the simulation, which `m5.simulate()` scheduled at the largest possible tick. So gem5 jumps straight to it, and `simTicks` ends up as 2<sup>64</sup>.

> Always sanity-check the global statistics, such as `simTicks` and `simInsts`, before you trust a rate. Most real configuration scripts end the simulation with an exit event, or give `m5.simulate()` a number of ticks.

## Dumping and resetting statistics

To measure only part of a simulation, we can control the statistics from the configuration script, with two functions:

- `m5.stats.dump()` writes a dump of every statistic, as it is now.
- `m5.stats.reset()` sets every statistic back to its starting value. Everything after it is counted from zero.

Open `workspace/04-gem5-models/04a-cpus/04b-statistics/hello_stats_config.py`. It simulates our four hellos in two halves of 1250 ticks: `m5.simulate(1250)` runs 1250 more ticks, and returns.

> **Your turn:** At the `TODO`, write a dump of the statistics so far, and reset them, so that the second dump only covers the second half.
>
> <details>
> <summary markdown="span"> <b>Answer</b> </summary>
>
> ```python
> m5.stats.dump()
> m5.stats.reset()
> ```
>
> </details>

<br>

Run it:

```bash
gem5 hello_stats_config.py
```

Now `stats.txt` has two dumps:

```txt
---------- Begin Simulation Statistics ----------
simSeconds                                   0.000000                       # Number of seconds simulated (Second)
simTicks                                         1250                       # Number of ticks simulated (Tick)
finalTick                                        1250                       # Number of ticks from beginning of simulation (restored from checkpoints and never reset) (Tick)
...
hello.hellosSaid                                    2                       # Number of hellos said (Count)
hello.hellosLeft                                    2                       # Number of hellos left to say (Count)
hello.helloRate                            1600000000                       # Hellos said per simulated second ((Count/Second))

---------- End Simulation Statistics   ----------

---------- Begin Simulation Statistics ----------
simSeconds                                   0.000000                       # Number of seconds simulated (Second)
simTicks                                         1250                       # Number of ticks simulated (Tick)
finalTick                                        2500                       # Number of ticks from beginning of simulation (restored from checkpoints and never reset) (Tick)
...
hello.hellosSaid                                    2                       # Number of hellos said (Count)
hello.hellosLeft                                    0                       # Number of hellos left to say (Count)
hello.helloRate                            1600000000                       # Hellos said per simulated second ((Count/Second))

---------- End Simulation Statistics   ----------
```

The first dump is our `m5.stats.dump()`, at tick 1250. The second is the one gem5 writes at the end. Let's compare them:

- `hellosSaid` is 2 in both: the reset set it back to 0 at tick 1250, so the second dump only counts the hellos at ticks 1500 and 2000.
- `hellosLeft` isn't reset. A `Value` doesn't store anything; it just reads `remainingHellos` at each dump.
- `simTicks` is 1250 in both, because it counts ticks since the last reset. `finalTick` is never reset, so it tells you where in the simulation each dump was taken.
- `helloRate` is 2 hellos in 1250 ticks, 1.6 billion hellos per simulated second, in both halves. The formula is computed at each dump, from that dump's values. `simSeconds` prints as `0.000000` only because it's printed with six decimal places; the formula uses its full value.

> This dump-and-reset pattern is how you measure a **region of interest**. In a standard library simulation, you don't call these functions yourself: by default, the `Simulator` resets the statistics when the workload signals the start of its region of interest, and dumps them at its end, as in the [communication](../../03-intermediate-features/04-communication.md) section.

### What happens in a reset

`m5.stats.reset()` calls `resetStats()` on every SimObject, and every statistic sets itself back to its starting value. If your SimObject keeps state that a statistic depends on, override `resetStats()` to reset that state too, and call the parent class's version. `Root` does this to make `simTicks` count from the last reset: it remembers the tick of the reset, and `simTicks` subtracts it from the current tick (see `RootStats::resetStats()` in `gem5/src/sim/root.cc`).

gem5 also resets every statistic once on its own, the first time you call `m5.simulate()`, right after every SimObject's `startup()`. So anything a SimObject counts before then, for example in its constructor, isn't in the first dump.

## Common mistakes

| Symptom | Likely cause |
|---|---|
| `error: no matching function for call to '...HelloSimObjectStats::HelloSimObjectStats()'` | the stats member isn't constructed in the SimObject's constructor: add `stats(this)` to its initializer list |
| `warn: One of the stats is a legacy stat.` | some statistic was created without a parent group. You've seen this one in every simulation since Unit I: a few of gem5's own models still do it. Make sure yours always have a parent. |
| a statistic is missing from `stats.txt` | it has the `nozero` flag, or a `prereq`, and its value is zero |
| a formula prints `nan` | it divided by zero, for example a hit rate with no accesses |
| rates that make no sense | check `simTicks` and `simInsts` first: did the simulation run for as long as you think? |
| numbers that include the warm-up | reset the statistics at the start of the region you want to measure |

## Reading statistics from Python

You can also read statistics in the configuration script itself, which is handy for printing a summary or checking a result. `get_simstat()` turns the current statistics into Python objects:

```python
from m5.stats.gem5stats import get_simstat

simstat = get_simstat([root])
print(simstat.hello.hellosSaid.value)
```

Like the JSON format, it leaves out formulas: `simstat.hello.helloRate` is `None`. For anything that goes in a report, use `stats.txt`.

With statistics of our own, we're ready for the branch predictor project, where you'll check your predictor against statistics like `branchPred.mispredictDueToPredictor`.
