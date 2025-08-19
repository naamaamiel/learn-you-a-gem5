# Simulation modes

You might have noticed us using "SE mode" functions like `set_se_binary_workload` in previous sections; what's that about?

> By the end of this section, you will be able to:  
>
> - **Assess** whether SE or FS mode is more appropriate for a particular simulation goal.
> - **Contrast** the benefits and drawbacks of Syscall Emulation (SE) and Full-System (FS) simulation modes.
> - **Change** whether a simulation uses SE or FS mode.

## What's SE mode?

**Syscall emulation (SE)** mode is a simulation mode in gem5 that *emulates* the operating system as opposed to *simulating* it. Only user-level code is simulated, and any system calls made within that code trap into the simulator. SE mode supports most common Linux system calls.

![A diagram of SE mode. A large rectangle represents the host system, and a smaller rectangle within it represents the simulation. Within the simulation, the simulated hardware and the simulated application interact with one another. The simulated application also interacts with the emulated OS, which is outside the simulation in the host system.](img/se_mode.png)

### The good news

SE mode is great if you really only care about the processor and the cache/memory system: it makes it easy for you to set up simulations by not requiring instantiation of every device in the system. Since it simulates less, SE mode also gives faster simulation speeds.

> SE mode is **simpler**, **easier to set up**, and **simulates faster**.

### The bad news

Since SE does not simulate the OS, you shouldn't use it if you care about *any* OS features or interactions (for example, page table walks). Think of the syscall emulation SE mode provides as a bare minimum needed to get user-level code to work. SE mode also has lower simulation fidelity, so if you require a high-fidelity simulation of your system, SE mode is not the right choice. Binaries that require elevated permissions also don't work in SE mode.

> SE mode is **lower-fidelity**, **does not simulate the OS**, and **does not support elevated permissions**.

### Example

Let's take a look at how SE mode handles user-level code with system calls. Open `SE_hello_world.py` to get started! This file sets up a simple system with a `PrivateL1CacheHierarchy`, a `SingleChannelDDR4_2400`, and a `TIMING` `SimpleProcessor`. 

We then use `set_se_binary_workload` (a function you've seen use use before!) to set a **binary workload** in **SE mode** for the board. This is how we tell the simulator to use SE mode.

That workload is a local binary resource, the source code of which is at `SE_hello_world.c`. This is a very simple workload:

```C
#include <stdio.h>

int main() {
    printf("Hello, World!\n");
    return 0;
}
```

> Recall that `printf` requires a system call to print to the console.

Let's run this thing! Use the following command:

```bash
gem5 -re --debug-flags=SyscallAll SE_hello_world.py
```

> You'll notice a few flags in this command. `-re` redirects the simulation output (both `stdout` and `stderr`) to separate directories. `--debug-flags` (which you've seen before in the traffic generation section!) logs system calls in stdout.

When the simulation wraps up, you should see the following in `simout.txt` (the redirected output of `stdout`):

```bash
280945000: board.processor.cores.core: T0 : syscall Calling write(1, 21152, 14)...
Hello, World!
280945000: board.processor.cores.core: T0 : syscall Returned 14.
```

One thing to know about gem5 output is that the *simulation's* `stdout` and the *simulator's* `stdout` are both output to the same `stdout` (and thus redirected to the same `simout.txt` file). This means we can separate the output into the two lines printed to the *simulator's*  `stdout`:

```bash
280945000: board.processor.cores.core: T0 : syscall Calling write(1, 21152, 14)...
280945000: board.processor.cores.core: T0 : syscall Returned 14.
```

...and the one line printed to the *simulation's* `stdout`:

```bash
Hello, World!
```

Recall that the number at the beginning of a line corresponds to the tick that the line was printed at. The two lines in the simulator's `stdout` show the `write` syscall being called at tick 280945000, then that same `write` syscall returning at 280945000: the same tick! As you can see, **SE mode does NOT record timing information for system calls**, but as the line of simulation `stdout` shows, the *behavior* of the system call still functions.

## What's FS mode?

**Full-system (FS) mode** is a simulation mode in gem5 that *simulates the entire system*. It simulates the CPU and the memory system (like SE mode does), but it also simulates I/O devices like disk and network interfaces along with the entire software stack including the OS, drivers, and applications.

![A diagram of FS mode. A large rectangle represents the host system, and a smaller rectangle within it represents the simulation. Within the simulation, the simulated hardware, the simulated OS, and the simulated application interact with one another.](img/fs_mode.png)

### The good news

Full-system mode is the go-to simulation mode if you need to simulate an entire system in high fidelity. It allows for detailed analysis and debugging of hardware and software interactions. If you care about I/O or the operating system, FS mode is the right move.

> FS mode **simulates the entire system** (including the OS) and **allows for detailed system analysis**.

### The bad news

All of that extra simulating comes at the price of simulation speed. If you don't care about the OS boot process, but need the OS to be fully simulated, you'll have to wait through that boot process every time (that is, unless you accelerate the simulation... check out the advanced topics section). You'll also need to provide extra resources other than just a binary (like the kernel and disk image) to run an FS mode simulation.

> FS mode is **slower** and **requires extra gem5 resources**.

### Example

<!--TODO (Naama): I don't like the existing FS mode example. Write and test out a new one before putting it here. Maybe running the same binary?-->

## Which should I choose?

One way to quickly know that you need to use FS mode is if your simulation requires a feature that SE mode does not support. For example, you may need to simulate system calls or any other aspect of the operating system in detail. Your binary may require elevated privileges to work, or you may rely on a more esoteric system call that is not implemented in SE mode, even if you don't care about its timing.

It's important not to treat SE mode as just "FS mode but faster". As we just looked at, SE mode doesn't simulate everything that FS mode does, and if you're not 100% sure that SE mode simulates everything you need, you should use FS mode instead. **FS mode simulates everything that SE mode does**, so it's a safe option.

> ***When in doubt, use FS mode***.

That being said, if you're certain that SE mode meets your needs, it is a quicker option! You'll notice that we've used SE mode quite a bit in this bootcamp to look at simpler simulations and examine processors, caches, and memory components. SE mode is another useful tool in your toolbox!

<link href="../style.css" rel="stylesheet"></link>
