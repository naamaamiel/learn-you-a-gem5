from gem5.components.boards.x86_board import X86Board
from gem5.components.memory.single_channel import SingleChannelDDR4_2400

from my_processors import BigProcessor, LittleProcessor
from my_cache_hierarchy import PrivateL1PrivateL2SharedL3CacheHierarchy
from my_lpddr2 import SingleChannelLPDDR2

# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
A simple gem5 configuration script that uses custom out-of-order CPUs 
and a custom 3-level cache hierarchy.

This script runs an x86 matrix multiply workload to its completion.
"""

processor = BigProcessor()

cache = PrivateL1PrivateL2SharedL3CacheHierarchy(
    l1d_size = "16KiB",
    l1i_size = "16KiB",
    l2_size = "256KiB",
    l3_size = "8MiB",
    l1d_assoc = 8,
    l1i_assoc = 8,
    l2_assoc = 16,
    l3_assoc = 16
)

memory = SingleChannelLPDDR2(
    size = "3GiB"
)

# A full-system x86 board
board = X86Board(
    clk_freq="3GHz",
    processor = processor,
    cache_hierarchy = cache,
    memory = memory
)

# Set the workload to a matrix multiply
board.set_workload(
    obtain_resource("x86-ubuntu-24.04-boot-no-systemd")
)

# Run the simulation until its end
sim = Simulator(board)
sim.run(20_000_000_000)
