from gem5.components.boards.riscv_board import RiscvBoard

from a1_components import CustomProcessor
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import PrivateL1PrivateL2CacheHierarchy
from gem5.components.memory.multi_channel import DualChannelDDR3_2133


# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
Assignment #1: Assemble-Your-Own-System

Name: Solution
"""

processor = CustomProcessor()

cache = PrivateL1PrivateL2CacheHierarchy (
    l1i_size = "32KiB",
    l1d_size = "16KiB",
    l2_size = "2MiB",
)

memory = DualChannelDDR3_2133 (
  size = "16GiB"
)

board = RiscvBoard(
    clk_freq="4GHz",
    processor = processor,
    cache_hierarchy = cache,
    memory = memory
)

board.set_workload(
    obtain_resource("riscv-gapbs-bfs-run")
)

# Run the simulation until its end
sim = Simulator(board)
sim.run()
