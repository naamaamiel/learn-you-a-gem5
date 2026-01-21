from gem5.components.boards.x86_board import X86Board
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import PrivateL1SharedL2CacheHierarchy
from gem5.components.memory.single_channel import SingleChannelDDR4_2400

from my_processors import BigProcessor, LittleProcessor

# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
A simple gem5 configuration script that uses custom out-of-order CPUs, 
BigProcessor and LittleProcessor, defined in my_processors.py.

This script runs an x86 matrix multiply workload to its completion.
"""

processor = LittleProcessor()

cache = PrivateL1SharedL2CacheHierarchy(
    l1d_size = "16KiB",
    l1i_size = "16KiB",
    l2_size = "256KiB",
    l1d_assoc = 8,
    l1i_assoc = 8,
    l2_assoc = 16
)

memory = SingleChannelDDR4_2400(
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
    obtain_resource("x86-matrix-multiply-run")
)

# Run the simulation until its end
sim = Simulator(board)
sim.run()
