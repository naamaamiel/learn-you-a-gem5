# Writing a gem5 branch predictor

Finally, it's time to write our own branch predictor!

> By the end of this section, you will be able to:
>
> - **Extend** an existing gem5 SimObject to enable new simulation functionality.

## Branch predictor project

Throughout the last few sections, you've gotten more familiar with gem5 branch predictors and how they work. In this section, you will implement your own simple addition to the branch predictor interface then complicate it slightly.

> This section is a **project section**: this means it is largely structured around independent programming. Give your best effort on your own, then check in with the solutions.

## Reminder: the branch predictor interface

As we've seen in the previous section, the gem5 branch predictor interface as defined in the `BPredUnit` class revolves around three main methods:

```c++
bool lookup(ThreadID tid, 
            Addr branch_addr, 
            void * &bp_history)
```

The `lookup()` function is called on a every branch in the code. It returns the prediction for the branch: 1 for taken, 0 for not taken.

```c++
void update(ThreadID tid, 
            Addr branch_addr, 
            bool taken, 
            void *&bp_history, 
            bool squashed, 
            const StaticInstPtr & inst, 
            Addr target)
```

The `update()` function is called to update the predictor based on the result of a branch. This function gets some more information about the branch instruction and what path it took in the code.

```c++
void updateHistories(ThreadID tid, 
                     Addr pc, 
                     bool uncond, 
                     bool taken,
                     Addr target, 
                     const StaticInstPtr &inst,
                     void * &bp_history)
```

The `updateHistories()` function is used to update a branch's **history table** based on the result of the branch.

> In this section, we will be focusing on simpler branch predictors that do not make use of the history table, so we'll leave this function blank.

When creating your own branch predictor, you'll need to override these methods with implementations that match your predictor's intended behavior. You are also free to define any *helper methods* to keep your code clean.

> Don't forget to follow gem5 style best practices!

## Part 0: Configuration script

As you build your branch predictor, you will want to test it out in-simulation. The `BranchPredProcessor` (processor with swappable branch predictor) component from the previous section is provided along with `minor_config.py` (renamed `simulate_branch_pred.py`); you will use these as a base for a new configuration script to test your new branch predictor on.

We'll be testing our branch predictor on the [`riscv-cce`](https://resources.gem5.org/resources/riscv-cce?version=1.0.0) binary and only running for 10,000,000 instructions.

>
> **Your turn**: Modify `simulate_branch_pred.py` to use the `riscv-cce` binary workload instead of `riscv-print-this`. Adjust the simulation to run for 10,000,000 instructions.
>
> <details markdown="span">
> <summary> <b>Answer</b> </summary>
> 
> ```python
> board.set_se_binary_workload(
>     binary = obtain_resource("riscv-cce"),
> )
> ```
>
> ```python
> sim.schedule_max_insts(10_000_000)
> ```
>
> </details>

## Part 1: Basic prediction

About the most basic branch predictor possible is a predictor that always predicts the same thing. In this case, we want to predict every branch as **not taken**. Your branch predictor should...

1. Follow the class hierarchy of existing gem5 branch predictors,
2. Be usable in configuration scripts using the Python class `HelloBP`,
3. Predict "not taken" for every branch,
4. Optionally, include a debugging flag named `HelloBranchPred` that prints out a helpful debugging message when `update()` and `lookup()` are called.

You should create your branch predictor in the `gem5/src/bootcamp` directory in a new subdirectory called `branch-pred`. You can verify your implementation against the statistics of our solution (when running the `riscv-cce` binary workload for 10,000,000 instructions):

```txt
board.processor.cores.core.branchPred.mispredictDueToPredictor_0::total       526359
```

If you'd like to attempt this on your own, no need to read the hints below! If you get stuck, the following tips might help:

>
> <details markdown="span">
> <summary> <b>Recommended workflow</b> </summary>
> 
> 1. Create the three required files for a SimObject: a Python declaration file, a C++ header file, and a C++ source file.
>
> 2. Implement the Python declaration file first. At this step, you'll need to think about the appropriate Python class name, parent class, and header file name; you'll also need to consider whether the predictor needs any parameters.
>
> 3. Next, implement the header file. You'll need to think about the method signatures you'll need for this implementation. You can always come back to this header file to add private helper functions or fields if you find it necessary.
>
> 4. Implement the source file next; the bulk of the work here is filling in the constructor and class functions. Remember that this is a pretty simple predictor!
>
> 5. Create and write the SConscript file. If you choose to write a debugging flag, remember that you need to declare it here.
>
> 6. Compile, fix any errors, repeat!
>
> 7. Import your new branch predictor into the `simulate_branch_pred.py` configuration script and use it in the simulated processor.
>
> 8. Run, verify, debug, repeat!
> </details>

<br>

>
> <details markdown="span">
> <summary> <b>Hints and reminders</b> </summary>
> 
> - The appropriate Python class name for this predictor is `HelloBP`, and it should inherit from the `BPredUnit` class.
>
> -  You can use other simple branch predictors (for example, `2bit_local.hh` and `2bit_local.cc`, the header and source files for `LocalBP`) for inspiration; all branch predictors are declared in the same Python file (`gem5/src/cpu/pred/BranchPredictor.py`).
>
> - You should override the three main interface functions in your implementation, though some of them might be blank or very minimal.
>
> - There is likely no need for private helper functions or fields.
>
> - Remember that while you'll verify your stats on the `riscv-cce` workload, there's no reason not to use a lighter-weight benchmark for quick testing.
>
> </details>

<br>

> For **file implementations**, refer to the `completed` directory in this lesson's workspace. This simple branch predictor is implemented under he `simple-branch-pred` directory.

>
> <details markdown="span">
> <summary> <b>gem5 compilation command</b> </summary>
> 
> Run the following from the `gem5/` directory:
>
> ```bash
> scons build/ALL/gem5.opt -j$(nproc)
> ```
>
> </details>

<br>

>
> <details markdown="span">
> <summary> <b>Command for running the configuration script</b> </summary>
> 
> Run the following:
>
> ```bash
> gem5 -re simulate_branch_pred.py
> ```
>
> As a reminder, the `-re` flag redirects `stdout` and `stderr` to files; this is especially useful for reading debug flag output.
>
> </details>

<br>

Congratulations on completing the first part of the project! Now to add some complexity to our predictor.

## Part 2: Tracking not takens

Turns out that predicting everything as not taken is not a great prediction strategy. Let's adjust the predictor to do the following:

1. Take a parameter `localPredictorSize` (default value: 512) that determines the size of the predictor,
2. Keep track of the addresses of branches that were previously not taken; the maximum number of tracked branch addresses (multiplied by the size of an address) should equal `localPredictorSize`,
3. When predicting a branch, predict the branch as "not taken" if it is found in the list of last seen not taken branches and "taken" otherwise,
4. When the result of a branch is available, add its address to the tracked branches if the branch was not squashed and not taken. If there's no room for the new entry, evict the least recently seen branch address.

Like before, you can verify your implementation against the statistics of our solution (when running the `riscv-cce` binary workload for 10,000,000 instructions):

```txt
board.processor.cores.core.branchPred.mispredictDueToPredictor_0::total       523023
```

> You can see that this is a small improvement over the previous version!

Once again, if you'd like some more implementation advice, please read on!

>
> <details markdown="span">
> <summary> <b>Recommended workflow</b> </summary>
> 
> 1. Adding a parameter involves changing the declaration and source files: modify these first to define the parameter (declaration) then use it (source).
> 
> 2. Implement your data structure for tracking not taken branches as a private field: this involves changing the header file.
>
> 3. Modify the `lookup()` function to check the contents of this data structure and make a prediction.
> 
> 4. Modify the `update()` function to add a branch address into the data structure if applicable (or indicate it as the last seen branch if it is already being tracked). Remember to evict the *least recently seen* branch address when needed.
>
> 5. Compile, fix any errors, repeat!
>
> 6. Import your new branch predictor into the `simulate_branch_pred.py` configuration script and use it in the simulated processor.
>
> 7. Run, verify, debug, repeat!
> </details>

<br>

>
> <details markdown="span">
> <summary> <b>Hints and reminders</b> </summary>
> 
> - The C++ [`list` class](https://cplusplus.com/reference/list/list/) is useful for maintaining the list of the last seen not taken branches. Try treating this list like a queue of sorts to track least-recently seen status.
>
> -  You may want to define a few additional private fields (for example, one that tracks the maximum size of the list in number of elements).
>
> - As you modify your predictor, remember that the parameters struct only updates when the code is compiled; don't be alarmed by IDE errors about non-existent fields before compiling.
>
> - Adding multiple debugging statements in a single function (especially the `update()` function) is useful to track what happens to an address and verify assumptions. Indenting all statements other than the first in a function makes the debugging output more readable.
>
> </details>

<br>

> For **file implementations**, refer to the `completed` directory in this lesson's workspace. This simple branch predictor is implemented under he `not-taken-branch-pred` directory.

>
> <details markdown="span">
> <summary> <b>gem5 compilation command</b> </summary>
> 
> Run the following from the `gem5/` directory:
>
> ```bash
> scons build/ALL/gem5.opt -j$(nproc)
> ```
>
> </details>

<br>

>
> <details markdown="span">
> <summary> <b>Command for running the configuration script</b> </summary>
> 
> Run the following:
>
> ```bash
> gem5 -re simulate_branch_pred.py
> ```
>
> As a reminder, the `-re` flag redirects `stdout` and `stderr` to files; this is especially useful for reading debug flag output.
>
> </details>

<br>

Congratulations! You've now implemented your very own branch predictor that adapts over time. Branch predictors in gem5 get more complicated than this; feel free to read through the existing implementations and compare them to the one you just created.

Implementing other SimObjects follows a similar structure to what you did here: examining the existing interface, extending a relevant parent class, and filling in overridden interface functions. gem5 is highly *extensible*: as you've seen, under this programming model, new SimObjects under a common base class can be used just like existing ones!
