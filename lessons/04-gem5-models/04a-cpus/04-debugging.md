# Debugging gem5 SimObjects

Let's prepare to write our own branch predictor by debugging an existing one.

> By the end of this section, you will be able to:
>
> - **Create** a new debugging flag and enable/disable it using a configuration script and a command line option.
> - **Build** gem5 using Kconfig.
> - **Use** `DPRINTF()` statements to print debugging information in the presence of a flag.
> - **Use** C++ `assert` statements and gem5 `fatal` and `panic` statements to verify assumptions and catch user and developer mistakes.
> - **Determine** which build-time configuration and compiler configuration are appropriate for a research goal.

## gem5's build system

Before we talk about gem5's debugging tools, we need to get a few more details on gem5's build system. Your choice of build configuration affects both the speed of your simulations and how easily they can be debugged. 

So far, we've built gem5 by running this command:

```bash
scons build/ALL/gem5.opt -j$(nproc)
```

As it turns out, gem5's build system offers *many* more options than this, and understanding these options helps when debugging SimObjects.

There are many different ways to configure gem5, which all result in different binaries. Broadly, there are two different categories of options: **compiler configurations**, which define the set of optimizations to be used, and **build-time options**, which determine what models will be included in the binary.

> You can see all available options by running `scons` with no arguments within the `gem5/` directory. Be warned: there is quite a bit of output to scroll through!

### Compiler configurations

You can tell which compiler configuration is being used for a gem5 build using the *suffix* attached to `gem5` in the `scons` command. For example, since we've been building `gem5.opt`, we've been building with the `opt` compiler configuration. gem5 provides three compiler configurations:

1. `fast`: This option enables all build optimizations and removes debugging symbols. The resulting binary is small (around 50 MiB), which makes it much faster. Since all debugging symbols are removed, you should **only use this configuration after debugging your models**.

2. `opt`: This option is optimized, but it includes debugging symbols and enables all assertions/panics. The resulting binary is *much* larger than `fast`'s (around 500 MiB). Despite this, `opt` is the most common compiler configuration. Debugging with GDB is mostly usable with `opt`, but some variables may be optimized away.

3. `debug`: This option is *not* optimized (it uses the [`-O1` flag](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)), includes all debugging symbols, and enables all assertions/panics. This configuration is ***much*** slower than `opt` (5-10 times slower), so you should only reach for it if you need to debug your models and `opt` is not enough.

> Overall, choosing a compiler configuration comes down to the phase of development you are in. `debug` and `opt` are useful when actively making changes to the backend, while `fast` is great when the dust has settled.

### Build-time configurations

gem5 includes *many* default build options:

```txt
ALL                       GCN3_X86                  NULL_MOESI_hammer  X86_MESI_Two_Level
ARM                       MIPS                      POWER              X86_MI_example
ARM_MESI_Three_Level      NULL                      RISCV              X86_MOESI_AMD_Base
ARM_MESI_Three_Level_HTM  NULL_MESI_Two_Level       SPARC
ARM_MOESI_hammer          NULL_MOESI_CMP_directory  VEGA_X86
Garnet_standalone         NULL_MOESI_CMP_token      X86
```

As the names suggest, these options determine the ISA(s) and cache coherence protocol that the binary will contain. They're typically written in the form `ISA_Coherence_Protocol`. We've been using the default build configuration `ALL`, which includes every supported ISA and Ruby coherence protocol.

If the default build configurations don't cut it, you can create your own! One way to do this is interactively with **Kconfig**.

> [Kconfig](https://docs.kernel.org/kbuild/kconfig-language.html) is a configuration tool/language also used for the Linux kernel and many other pieces of software with complex build systems. 

To use Kconfig, first make a new build directory using one of the default build options. Let's make a build directory named `my_gem5` and base it off of the `ALL` default configuration:

```bash
scons defconfig build/my_gem5/ build_opts/ALL
```

> While we are running this command from the `gem5` directory to place this directory alongside all the other build directory, this directory can go *anywhere on your system*.

If you navigate to `gem5/build/`, you should now see a directory called `my_gem5` alongside the one called `ALL` that we've been using this whole time. We can now use Kconfig to interactively change our configuration:

```bash
scons menuconfig build/my_gem5/
```

You can use the UP and DOWN arrows to hover over different build configuration options and menus and SPACE/ENTER to select/deselect them. You can exit from a menu by pressing ESC. 

> **Your turn:** Take some time to explore the interactive build tool. Can you figure out how to disable the CHI cache coherence protocol in this configuration?
>
> <details>
> <summary markdown="span"> <b>Answer</b> </summary>
> 
> Navigate to the `Ruby Protocols` menu:
>
> ```bash
> (Top) -> Ruby -> Enable -> Ruby Protocols
> ```
>
> Use the DOWN key to scroll down to the `CHI` protocol, and click SPACE/ENTER to disable it.
> 
> ```bash
> [ ] CHI
> ```
> 
> Then, press Q to quit and Y to save when prompted.
> </details>

<br>

The build configuration that works for you depends on the goals of your work (e.g., do you really need more than one ISA?). Once you have a build configured to your liking, you can build gem5 with it using SCons. You are **NOT REQUIRED** to run the following command, and we will continue to use `ALL` and `gem5.opt` for this bootcamp:

```bash
scons build/my_gem5/gem5.opt -j$(nproc)
```

> As a reminder, `-j$(nproc)` uses all processor cores to build gem5. If you find yourself running into out-of-memory errors on your device, using fewer cores may help.

## `DebugFlags`

Other than selecting the appropriate compiler configuration for debugging with tools like GDB and asserts/panics, you can also enable (and write!) your own `DebugFlags` to use in gem5. Enabling different `DebugFlags` enables the printing of different helpful debugging statements during simulation.

### Using `DebugFlags`

We can print out all existing `DebugFlags` in gem5 using:

```bash
gem5 --debug-help
```

When you do, you should see a *lot* of output that looks something like this (truncated with `[...]` for brevity):

```txt
Base Flags:
    ACPI: ACPI debugging
    AMBA: 
    AMDGPUDevice: 
    AMDGPUMem: 
    AMDGPUSystemHub: 
    [...]
    MinorCPU: Minor CPU-level events
    MinorExecute: Minor Execute stage
    MinorInterrupt: Minor interrupt handling
    MinorMem: Minor memory accesses
    MinorScoreboard: Minor Execute register scoreboard
    MinorTiming: Extra timing for instructions
    MinorTrace: MinorTrace cycle-by-cycle state trace
    [...]
    Writeback: 
    X86: Generic X86 ISA debugging

Compound Flags:
    AnnotateAll: All Annotation flags
        Annotate, AnnotateQ, AnnotateVerbose
    [...]
    Minor: 
        MinorCPU, MinorExecute, MinorInterrupt, MinorMem, MinorScoreboard
    O3CPUAll: 
        Fetch, Decode, Rename, IEW, Commit, IQ, ROB, FreeList, LSQ, LSQUnit, 
        StoreSet, MemDepUnit, DynInst, O3CPU, Activity, Scoreboard, 
        Writeback
    Registers: 
        IntRegs, FloatRegs, VecRegs, VecPredRegs, MatRegs, CCRegs, MiscRegs
    [...]

Formatting Flags:
    FmtFlag: Show the --debug-flag that enabled each debug message
    FmtStackTrace: Print a stack trace after every debug message
    FmtTicksOff: Don't show tick count on debug messages
```
You'll notice that these flags are split into **base flags**, **compound flags**, and **formatting flags**. 

- **Base flags** (like `MinorExecute`) are individual flags, usually associated with a specific SimObject or behavior. 
- **Compound flags** (like `Minor`) enable multiple base flags all at once for convenience, usually to keep track of a whole simulation component.
- **Formatting flags** (like `FmtTicksOff`) control the formatting of debug prints. You can pick whichever formatting flag(s) you want to make your debugging easier.

#### Let's see it in action!

Let's enable some `DebugFlags` for `MinorCPU` so that we can see what's going on in-simulation.

> As a reminder, `MinorCPU` is an implementation of an in-order pipelined CPU.

Open `minor_config.py` to get started. This is the configuration script we'll be running; it runs a very simple binary workload that prints out a given string a set number of times. It uses standard library components you've seen before, but it's missing a processor. 

You will also notice the `branch_pred_processor.py` file; much like in Unit II, we can create new standard library objects to parameterize models. This time, we created a single-core processor using a RISC-V Minor core that exposes the core's **branch predictor** as a configurable parameter under the name `branch_predictor`. Take the time to look over this file and make sure it makes sense to you.

> **Your turn:** Add a `BranchPredProcessor` to `minor_config.py` with a branch predictor instance of `LocalBP()`.
> 
> All imports are already provided for you.
>
> <details>
> <summary markdown="span"> <b>Answer</b> </summary>
> 
> ```python
> processor = BranchPredProcessor(
>   branch_predictor = LocalBP()
> )
> ```
>
> </details>

<br>

> ***Wait, what's `LocalBP`?*** `LocalBP` is a **2-bit saturating counter branch predictor**. It maintains a *local table* of counters indexed by the program counter (PC) value (so that different branches index into different elements of the table). 
>
> When a branch is taken, its counter is *incremented*. When a branch is not taken, its counter is *decremented*. Branches are predicted by reading the value of their 2-bit counter: if it has a value of 2 or 3, the branch is predicted taken. If it has a value of 0 or 1, the branch is predicted not taken.
>
> This kind of predictor is *local* because different branches are not correlated with one another. It does not keep any global history to use in prediction.

If we run this simulation like we always do, with:

```bash
gem5 minor_config.py
```

we can see the simulation's stdout output, alongside some (omitted) warnings.

```txt
1 Hello, gem5!
2 Hello, gem5!
```

Let's enable some debug flags and see what happens. To do this, we just need to run gem5 with the `--debug-flags=` option, providing the names of the flags we want. For now, let's enable the *base flag* `Branch`, which turns on debug prints for some branch prediction information. Since a *lot* of branches are about to be simulated, let's redirect the console output to a file, too.

```bash
gem5 -re --debug-flags=Branch minor_config.py
```

> To add more that one flag, provide a list of flag names inside of square brackets. For example:
> 
> ```bash
> gem5 -re --debug-flags=[Branch, Minor] minor_config.py
> ```
> 
> *Do not run this command!* This will generate a lot more output, and the discussion of the output assumes you've only enabled the `Branch` flag. 

You should see *a lot* of output as the simulator prints out several trace messages for *every branch*. This is why debug flags aren't turned on by default! Still, we can use these flags to learn some information about how branches are predicted. For example, we can peek at every correctly-predicted instruction:

```bash
grep 'Branch predicted correctly' m5out/simout.txt
```

```txt
...
15015636: board.processor.cores.core.fetch2: Branch predicted correctly inst: 0/284.530/2032/8068.8072 pc: 0x3ba14 (jal)
15017301: board.processor.cores.core.fetch2: Branch predicted correctly inst: 0/284.531/2035/8071.8075 pc: 0x246e4 (c_bnez)
15018633: board.processor.cores.core.fetch2: Branch predicted correctly inst: 0/284.532/2037/8073.8077 pc: 0x246f6 (bne)
...
```

Unlike the statistics in `stats.txt`, debugging prints give us additional information such as the current tick, the value of the program counter, and the instruction being executed. In practice, you'll want to enable debugging flags very judiciously and test them on small segments of simulations to keep the output manageable.

### Writing a `DebugFlag`

As you know, the processor in this configuration uses `LocalBP` as its branch predictor. Let's create a new `DebugFlag` for it to more easily trace its behavior. To create and use a new flag, we need to do the following:

- Define the flag,
- Import the auto-generated header file,
- Write `DPRINTF` statements using the flag,
- Rebuild gem5 and run with the new flag.

#### Defining a flag

We can create new `DebugFlags` by defining them in a `SConscript`. We can define a flag in any `SConscript`, but it's best practice to put them in the same `SConscript` that registers the relevant `SimObjects`. Since this flag will print out branch predictor-related statements, let's define it in `gem5/src/cpu/pred/SConscript`.

In this file, you'll find that some debugging flags already exist (including the `Branch` flag we used above!):

```python
DebugFlag('Indirect')
DebugFlag('BTB')
DebugFlag('RAS')
DebugFlag('FreeList')
DebugFlag('Branch')
DebugFlag('Tage')
DebugFlag('LTage')
DebugFlag('TageSCL')
```

These flags are useful, but we don't have one specifically for `LocalBP`. Let's do that here by adding the line:

```python
DebugFlag('LocalBranchPred', 'Traces execution of the LocalBP branch predictor')
```

We must give a defined `DebugFlag` a name, but we can optionally give it a helpful description. We've decided to do that here.

Adding this line to the `SConscript` will auto-generate a `.hh` file defining the debug flag when gem5 is built. We can import this flag into our code by importing `trace.hh` and this auto-generated file. Since we'll be writing our debug print statements for `LocalBP`, we should import the `LocalBranchPredictor` in its source file, `gem5/src/spu/pred/2bit_local.cc`:

```c++
#include "base/trace.hh"
#include "debug/LocalBranchPred.hh" // add this line!
```

> Note that `2bit_local.cc` already imports `trace.hh`; we don't need to import it again!

#### `DPRINTF`

We print debugging statements using the `DPRINTF` function. `DPRINTF` works similarly to the standard C [`printf`](https://cplusplus.com/reference/cstdio/printf/?kw=printf) function:

```c++
DPRINTF(DebugFlag, "format string", ...)
```

`DPRINTF` will only print if the corresponding `DebugFlag` is enabled.

Let's add a a `DPRINTF` statement using our new debug flag. We'll use this statement to track how the counter value for a branch affects its prediction. We can start by looking at `gem5/src/cpu/pred/2bit_local.cc` to see the functions that `LocalBP` defines.

- `lookup`, `updateHistories`, `update`, and `squash` are overridden from `LocalBP`'s parent class, `BPredUnit`. These functions are used to: 
    - Look up a prediction for a branch, 
    - Update the global branch history table, 
    - Update the predictor based on the result of a branch,
    - Squash uncommitted updates in the history table.

> You'll notice that since `LocalBP` is local, `updateHistories` and `squash` don't do much.

- `getPrediction` takes a counter value and transforms it to a taken (1) and not taken (0) boolean value,
- `getLocalIndex` takes a program counter value and transforms it into an index into the local history table.

You'll also notice other `DPRINTF` statements in here! These are related to the `Fetch` `DebugFlag`, which tracks the behavior of the instruction fetch unit (where branch prediction occurs).

> **Your turn:** Add a `DPRINTF` statement for the `LocalBranchPred` `DebugFlag` right before the `lookup()` function returns. This debug print should output the branch address, the counter value, and taken/not taken prediction.
>
> <details>
> <summary markdown="span"> <b>Answer</b> </summary>
> 
> ```c++
> DPRINTF(LocalBranchPred, "Branch address %lu has counter %i; predicted %i\n", branch_addr, counter_val, taken);
> ```
>
> Other phrasing is of course okay, as long as the same information is printed. The rest of this section assumes the above phrasing.
> 
> </details>


#### Rebuilding and running

To see these prints, we need to rebuild gem5:

```bash
scons build/ALL/gem5.opt -j$(nproc)
```

Then, we can run using our new debug flag!

> **Your turn:** Run gem5 using the `minor_config.py` configuration script with the new `LocalBranchPred` debug flag enabled. Redirect the output to files.
>
> <details>
> <summary markdown="span"> <b>Answer</b> </summary>
> 
> ```bash
> gem5 -re --debug-flags=LocalBranchPred minor_config.py
> ```
> 
> </details>

<br>

When we do, we will once again see a *lot* of output in `simout.txt`:

```txt
...
10722600: board.processor.cores.core.branchPred: Branch address 153644 has counter 0; predicted 0
10727262: board.processor.cores.core.branchPred: Branch address 153644 has counter 1; predicted 0
10731924: board.processor.cores.core.branchPred: Branch address 153644 has counter 2; predicted 1
10733922: board.processor.cores.core.branchPred: Branch address 153644 has counter 2; predicted 1
10735920: board.processor.cores.core.branchPred: Branch address 153644 has counter 3; predicted 1
10737918: board.processor.cores.core.branchPred: Branch address 153644 has counter 3; predicted 1
10751904: board.processor.cores.core.branchPred: Branch address 165982 has counter 0; predicted 0
10753236: board.processor.cores.core.branchPred: Branch address 166008 has counter 0; predicted 0
10754901: board.processor.cores.core.branchPred: Branch address 166038 has counter 0; predicted 0
10921734: board.processor.cores.core.branchPred: Branch address 83650 has counter 0; predicted 0
10922400: board.processor.cores.core.branchPred: Branch address 83658 has counter 0; predicted 0
10923066: board.processor.cores.core.branchPred: Branch address 83674 has counter 0; predicted 0
...
```

We can parse this output by focusing on one specific branch address:

```bash
grep '165476' m5out/simout.txt 
```

This allows us to see how a counter for one repeatedly-updated branch changes over time, eventually updating the prediction from not taken to taken:

```txt
 720612: board.processor.cores.core.branchPred: Branch address 165476 has counter 0; predicted 0
 809856: board.processor.cores.core.branchPred: Branch address 165476 has counter 0; predicted 0
 860139: board.processor.cores.core.branchPred: Branch address 165476 has counter 1; predicted 0
1002996: board.processor.cores.core.branchPred: Branch address 165476 has counter 1; predicted 0
1005660: board.processor.cores.core.branchPred: Branch address 165476 has counter 1; predicted 0
1010322: board.processor.cores.core.branchPred: Branch address 165476 has counter 2; predicted 1
1063269: board.processor.cores.core.branchPred: Branch address 165476 has counter 2; predicted 1
1066599: board.processor.cores.core.branchPred: Branch address 165476 has counter 2; predicted 1
1113219: board.processor.cores.core.branchPred: Branch address 165476 has counter 3; predicted 1
1256409: board.processor.cores.core.branchPred: Branch address 165476 has counter 3; predicted 1
1259739: board.processor.cores.core.branchPred: Branch address 165476 has counter 3; predicted 1
```

#### Another way to enable `DebugFlags`

Using a lot of debug flags, or even just one, can make our `gem5` command a bit unwieldy. If you find this to be an issue, you can move `DebugFlag` enabling into the configuration script! To do this, we need to import `flags`:

```python
from m5.debug import flags
```

...and enable our desired flag(s) 

```python
flags["LocalBranchPred"].enable()
```

By adding these two lines, we'll no longer need to use the `--debug-flags` option when running `gem5`:

```bash
gem5 minor_config.py
```

You should see many debug prints in the terminal, just like when we enabled the `LocalBranchPred` flag in the command itself.

## Other debugging facilities in gem5

### Assertions, fatals, and panics

gem5 has a few more debugging facilities available. These are assertions, fatals, and panics:

- An **assertion** is a C++-standard facility designed to catch false programmer assumptions. You can write assertions into your SimObject code using [`assert`](https://cplusplus.com/reference/cassert/assert/?kw=assert) (runtime checking) and [`static_assert`](https://en.cppreference.com/cpp/language/static_assert) (compile-time checking).
- **Fatals** and **panics** are assert-like functions implemented in gem5. Both cause the simulation to end with an error message, but they have different uses in gem5 convention:
    - `fatal` and `fatal_if` are used to catch **user errors** (for example, if a user tries to configure a predictor with a negative number of counter bits).
    - `panic` and `panic_if` are used to catch **developer errors** (for example, if a program invariant is violated)

> Each function and its `if` variant are very similar, and the one you choose to use depends on the structure of your code.
> 
> ```c++
> if (capacity < 0) { fatal("capacity can not be > negative.\n"); }
> // OR
> fatal_if(capacity < 0, "capacity can not be negative.\n");
> ```
 
We can see an example of a `fatal` in the constructor of `LocalBP`:

```c++
if (!isPowerOf2(localPredictorSize)) {
        fatal("Invalid local predictor size!\n");
}
```

We don't want the user to pass in a non-power-of-2 predictor size, so we `fatal` and inform them of the issue.

### Variants of `DPRINTF`

`DPRINTF` is not the only way to create debug prints; it has a few siblings! They are all defined in `gem5/src/base/trace.hh`, and you can find documentation for them [here](https://doxygen.gem5.org/release/current/base_2trace_8hh.html). These are a few examples:

- `DPRINTFR` prints without printing a name (one example of a name is `board.processor.cores.core.branchPred`); this is useful for printing debug statements in non-`SimObject` objects.
- `DPRINTFN` and `DPRINTFNR` don't take a `DebugFlag` as a parameter, so they print whenever debugging is enabled at all (determined by the compiler configuration).
- `DDUMP` prints data in human-readable hex format.

With all of these tools in our belt, we're ready to start writing our own branch predictor.
