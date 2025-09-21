# get the prebuilt board 
from gem5.components.boards.x86_board import X86DemoiBoard

# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
One of the most basic gem5 scripts you can write.

This boots linux (just the kernel) and exits. However, we will only run it for
20 ms to save time.
"""

# define the processor, cache, and memory here

# A full-system x86 board (replace this with X86iBoard!)
board = X86DemoiBoard()

# Set the workload to boot linux (Ubuntu 24.04)
# We will do "no systemd" to save some time
board.set_workload(
    obtain_resource("x86-ubuntu-24.04-boot-no-systemd")
)

# Run the simulation for 20 ms (of simulated time)
sim = Simulator(board)
sim.run(20_000_000_000) # 20 billion ticks or 20 ms
