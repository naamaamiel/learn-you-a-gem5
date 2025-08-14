# Your first configuration script

Hope you had a good stretch break waiting for gem5 to build. Now that it's finally done, let's run a simulation!

> By the end of this section, you will be able to:  
>
> - **Run** a pre-existing gem5 Python script.
> - **Explain** how a Python configuration script is used in conjunction with the gem5 binary.
> - **Locate** the output of gem5 simulator runs.
>  

## What's a configuration script?

Like we mentioned in the [Enter gem5 section](../01-sim-background/02-enter-gem5.md), gem5 is a Python interpreter. A configuration script is a Python (`.py`) file containing the parameters for a gem5 simulation. It specifies the components to be simulated and provides other options like the simulation mode (more on this later), how long the simulation will run for, what code the simulated components will execute, and much more.

## `Hello, world!`

Ok, enough waiting. Let's simulate! Outside of the `gem5` directory, create a directory for your bootcamp work (we'll call it `bootcamp`) containing a subdirectory for this part (we'll call it `hello-world`). Inside `bootcamp/hello-world`, create a file called `hello_world.py` with the following contents:

```python
# get the prebuilt board 
from gem5.prebuilt.demo.x86_demo_board import X86DemoBoard

# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
One of the most basic gem5 scripts you can write.

This boots linux (just the kernel) and exits. However, we will only run it for
20 ms to save time.
"""

# A full-system x86 board
board = X86DemoBoard()

# Set the workload to boot linux (Ubuntu 24.04)
# We will do "no systemd" to save some time
board.set_workload(
    obtain_resource("x86-ubuntu-24.04-boot-no-systemd")
)

# Run the simulation for 20 ms (of simulated time)
sim = Simulator(board)
sim.run(20_000_000_000) # 20 billion ticks or 20 ms
```

Without further ado, let's run this thing. Navigate to the parent directory of the gem5 directory and run:

```bash
./gem5/build/ALL/gem5.opt bootcamp/hello-world/hello_world.py
```

If all goes well, you'll see this output in your terminal:

```bash
TODO (Naama): Fill in terminal output. 
```

## What did I just run?

Great question! Let's break this down.

### The imports

```python
from gem5.prebuilt.demo.x86_demo_board import X86DemoBoard
from gem5.resources.resource import obtain_resource
from gem5.simulate.simulator import Simulator
```

These 3 import statements pull in critical components for our simulation: the board, the method by which we grab a workload for our board, and the simulator that actually runs the workload on the simulated board. More on these components up next!

### The board

```python
board = X86DemoBoard()
```

This line instantiates a board. Think of a board as a motherboard that other components (such as a CPU, a cache hierarchy, and a memory system) plug into. `X86DemoBoard` is a pre-built board that already comes with plugged-in components so that you don't have to worry about it!

If you're curious, you can look into the source file for `X86DemoBoard` at `gem5/src/python/gem5/prebuilt/demo/x86_demo_board.py`. The code in there may not make perfect sense quite yet, but you may be able to spot the memory, processor, and cache hierarchy being instantiated and "plugged into" the board.

### The workload

```python
board.set_workload(
    obtain_resource("x86-ubuntu-24.04-boot-no-systemd")
)
```

You can think of a board's workload as the code it is tasked with running along with any parameters or extra data it needs to do so. We first acquire the workload using the `obtain_resource` function, which grabs a resource by name from the collection of pre-existing gem5 resources. We'll talk more about these resources later on in the bootcamp.

This particular resources boots up Ubuntu without systemd then promptly exits the simulation. This workload includes all of the necessary information to boot Ubuntu (like the disk image and the kernel code) and sets all the simulation parameters to their default values.

After we get the workload, we tell the board to run it using the `set_workload` function.

### The simulator

```python
sim = Simulator(board)
sim.run(20_000_000_000)
```

Having a board is great and all, but we need to tell gem5 how to start the simulation. For that, we use the `Simulator` object. Think of the `Simulator` as the simulation controller. It takes a board (along with other optional parameters, which we didn't bother with here), and we can tell it to instantiate all of the board's components and start a simulation with `run()`.

The parameter we gave to the `run()` function is the number of *simulation ticks* we want the simulation to run for. You can configure the length of a tick, but by defualt, a tick is one picosecond (1 ps, equal to $10^{-12}$ seconds). Here, we tell the simulation to run for 20,000,000,000 in-simulation picoseconds, or 20 in-simulation milliseconds. After that simulated time has elapsed, the simulation will end.

### Putting it all together

All together, our "hello world" file takes a pre-built board, tells it to boot Ubuntu, then simulates that booting process happening on that board for 20 simulated milliseconds before exiting. It looks something like this:

![A diagram of the gem5 hello world example. The simulator is a box with two slots: one for params and one for a board. The board is a separate box with four slots: one for a CPU, one for a cache hierarchy, one for memory, and one for a workload. The board box is connected to the board slot in the simulator box.](img/gem5-hello-world.png)

In this case, we left the "params" box empty, meaning we just used the default values.

At the core, every gem5 simulation boils down to this: a simulation that simulates a board. The complexity comes in when we start doing away with prebuilt components and reconfigure or even build our own components. You'll be doing that in no time!
