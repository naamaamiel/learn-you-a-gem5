# get the prebuilt board
from gem5.prebuilt.demo.x86_demo_board import X86DemoBoard

# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
One of the most basic gem5 scripts you can write without using a demo board.

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
