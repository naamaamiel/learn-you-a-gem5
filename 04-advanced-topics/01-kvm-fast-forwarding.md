# KVM fast-forwarding

This is the first of a few sections on how to deal with the fact that simulation is ***slow***. It's not our fault, it's the nature of simulation!

> By the end of this section, you will be able to:  
>
> - **Set up** KVM fast-forwarding for simulation.
> - **Determine** whether KVM fast-forwarding is an appropriate technique for a given simulation need.
>

## Get to the point... faster

The reality is that there are often large parts of the simulation that we *need*... but don't really care about. You want to know how your system performs under your specific benchmark, not how quickly it can boot Linux.

Ideally, we would only simulate in high fidelity and collect detailed statistics during our **region of interest (ROI)** and just speed through the rest without collecting any information we don't care about.

![A timeline comprised of 5 roughly equally-sized sections: kernel boot, OS setup, benchmark load, ROI, cleanup. The ROI section is colored in blue, and the rest are gray. In a key below the timeline, the gray sections are labeled "don't care" and the blue section is labeled "!!!!!!!!".](img/kvm-roi.png)

Good news! This is possible with KVM fast-forwarding.

## What's KVM fast-forwarding?

As you might remember when we covered CPU basics earlier in the bootcamp, KVM (which stands for Kernel Virtual Machine) is a CPU model available in gem5. KVM CPUs just use the **host's CPU** to execute the code, which makes them ***really fast***.

The idea behind KVM fast-forwarding is to take advantage of this really fast execution by using a KVM CPU during the boring sections of simulation and only bringing in a timing CPU model for the region of interest. The result is a simulation that runs a lot faster and still yields helpful statistics about the region of interest.

## Sounds great, how do I do it?

Using KVM fast-forwarding requires us to:

1) Indicate where in the workload our region of interest lies,
2) Have a way of switching between CPUs,
3) Switch between CPUs when we hit the indicated region of interest.

Let's go through an example to show how KVM fast-forwarding is done. Copy the `kvm_time.py` file from the bootcamp resources.

### Exit events for KVM fast-forwarding

The workload you use for KVM fast-forwarding must be annotated using m5ops to indicate the beginning and end of the ROI. The most common way to do this is to include a `workbegin` at the beginning of the ROI and a `workend`  at the end.

Since KVM CPUs use the host CPU to execute code, and the host CPU has no idea what m5ops are, it will not recognize any instruction-mode m5ops. Instead, you must use the address mode versions; more on this in the m5ops section of the bootcamp.

One workload that is already annotated in this way is the Class A EP benchmark in the NPB benchmark suite. Let's use that for this example.

> **Your turn:** Fill in `TODO (1)` in `kvm_time.py` to obtain the `"npb-ep-a"` workload and pass it to the simulation board.
>
> <details>
> <summary> <b>Answer</b> </summary>
>
> ```python
> board.set_workload(obtain_resource("npb-ep-a"))
> ```
>
> </details>

<br>

### SwitchableProcessor

A `SwitchableProcessor` is a component that allows for a processor to switch between cores during execution, as long as your system uses `SimpleCores`. You can give a `SwitchableProcessor` any number of cores to switch between, then tell is to switch to a specific core using the `switch_to_processor()` function.

![A diagram of a SwitchableProcessor and a SimpleSwitchableProcessor. The SwitchableProcessor has a dictionary of SimpleCores labeled "A", "B", ... "Z". The SimpleCore labeled "B" is highlighted and labeled with a code segment that says "switch_to_processor("B")". The SimpleSwitchableProcessor has two CPUTypes.TYPEs labeled "starting_core_type" and "switch_core_type". The switch_core_type is highlighted and labeled with a code segment that says "switch()".](img/gem5-switchable-proc.png)

For the purposes of KVM fast-forwarding, we only need two cores: a `KVM` core for fast-forwarding and a `TIMING` core for the ROI. Thankfully, there already exists a component that does this for us! The `SimpleSwitchableProcessor` class only takes two cores types: a starting and switch core type, then allows you to switch between them using the `switch()` function. 

> **Your turn:** Fill in `TODO (2)` in `kvm_time.py` to initialize `processor` as a `SimpleSwitchableProcessor` with a starting core type of `CPUTypes.KVM`, a switch core type of `CPUTypes.TIMING`, the ISA that matches your host machine's ISA, and 2 cores.
>
> <details>
> <summary> <b>Answer</b> </summary>
> 
> ```python
> processor = SimpleSwitchableProcessor(
>   starting_core_type = CPUTypes.KVM,
>   switch_core_type = CPUTypes.TIMING,
>   isa = ISA.X86, # For example...
>   num_cores = 2
> )
> ```
>
> </details>

<br>

### Exit event handlers

We can customize the behavior of the `workbegin` and `workend` exit event handlers to switch between the cores in our `SimpleSwitchableProcessor`. We want the `workbegin` handler, which indicates the beginning of the ROI, to do the following:

1) Dump the current statistics from the KVM fast-forwarding segment,
2) Switch from the KVM CPU to the timing CPU,
3) Reset the statistics,
4) Fall back to simulation.

This way, we have some information about what happened during fast-forwarding, and we prepared ourselves for the ROI.

We want the `workend` handler, which indicates the end of the ROI, to do the following:

1) Dump the current statistics from the detailed simulation segment,
2) End the simulation.

This way, we print out the statistics we gathered from the timing phase and stop simulating.

> **Your turn:** Fill in `TODO (3)` in `kvm_time.py` to write a `workbegin` handler that does the following:
>
> 1) Dump the current statistics from the KVM fast-forwarding segment,
> 2) Switch from the KVM CPU to the timing CPU,
> 3) Reset the statistics,
> 4) **Schedule an exit event after running from 1,000,000,000 ticks,**
> 5) Fall back to simulation.
>
> Note that we added a new thing for the workbegin handler to do: automatically exit the simulation for us after 1,000,000,000 ticks. This way, we don't have to implement a `workend` handler, and we don't have to simulate the entire ROI (which might take a while).
>
> <details>
> <summary> <b>Answer</b> </summary>
>
> ```python
> def workbegin_handler():
>     print("Done booting Linux")
> 
>     print("Dump the current stats")
>     m5.stats.dump()
> 
>     print("Switching from KVM to TIMING CPU")
>     processor.switch()
> 
>     simulator.set_max_ticks(1000_000_000)
> 
>     print("Resetting stats at the start of ROI!")
>     m5.stats.reset()
> 
>     yield False
> ```
>
> </details>

<br>

We also need to register these exit events with the simulator object.

> **Your turn:** Fill in `TODO (4)` in `kvm_time.py` to register our new `workbegin_handler` function to trigger on the `workbegin` exit event.
>
> <details>
> <summary> <b>Answer</b> </summary>
>
> ```python
> ExitEvent.WORKBEGIN: workbegin_handler(),
> ```
>
> </details>

<br>

Congratulations! You just set up a simulation with KVM fast-forwarding. Let's run this thing and see what it says!

> ⚠️ ***UNDER CONSTRUCTION!*** ⚠️

<!-- TODO (Naama): Run this thing and discuss results -->

## Caveats

KVM fast-forwarding is great, but it's not applicable everywhere. It has a few major downsides which are important to consider:

### The simulation system must have the same ISA as the host

Once again, the fact that KVM CPUs rely on the host CPU comes back to bite us. You can't make an x86 CPU execute ARM instructions! This means that if you want to use KVM fast-forwarding, you can't simulate an ISA different from your host machine.

### KVM might impact parallelism

KVM CPUs require the actual hardware KVM thread, so using KVM fast-forwarding might constrain the amount of simulations we can run in parallel (more on this in the multisim section).

### We're still executing the boring parts

KVM fast-forwarding helps us spend less time on the regions of the simulation that we don't care about, but we still have to execute those sections every time we want to run a simulation. If the fast-forwarded region is large, we could still be waiting a while to get to the good stuff.

### Non-deterministic

Since KVM fast-forwarding still executes everything leading up to the ROI, any non-determinism (for example, thread interleaving) in the fast-forwarded region will affect how the ROI executes between fast-forwarded runs.

We'll address these concerns in the next section about checkpointing.
