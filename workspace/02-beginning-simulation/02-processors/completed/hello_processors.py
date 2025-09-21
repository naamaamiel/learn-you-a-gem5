from gem5.components.isas import ISA
from gem5.components.boards.x86_board import X86Board
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import PrivateL1SharedL2CacheHierarchy
from gem5.components.memory.single_channel import SingleChannelDDR4_2400

from my_processors import BigProcessor, LittleProcessor

# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
One of the most basic gem5 scripts you can write.

This boots linux (just the kernel) and exits. However, we will only run it for
20 ms to save time.
"""

processor = BigProcessor()

cache = PrivateL1SharedL2CacheHierarchy(
    l1d_size = "16kiB",
    l1i_size = "16kiB",
    l2_size = "256kiB",
    l1d_assoc = 8,
    l1i_assoc = 8,
    l2_assoc = 16
)

memory = SingleChannelDDR4_2400()

# A full-system x86 board
board = X86Board(
    clk_freq="3GHz",
    processor = processor,
    cache_hierarchy = cache,
    memory = memory
)

# Set the workload to boot linux (Ubuntu 24.04)
# We will do "no systemd" to save some time
board.set_workload(
    obtain_resource("x86-ubuntu-24.04-boot-no-systemd")
)

# Run the simulation for 20 ms (of simulated time)
sim = Simulator(board)
sim.run(20_000_000_000) # 20 billion ticks or 20 ms
