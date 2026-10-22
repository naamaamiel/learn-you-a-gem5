from gem5.components.boards.riscv_board import RiscvBoard

from a1_processor import CustomProcessor
from a1_cache_hierarchy import CustomCacheHierarchy
from a1_memory import CustomMemory


# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
Assignment #1: Assemble-Your-Own-System

Name: Solution
"""

processor = CustomProcessor()

cache = CustomCacheHierarchy (
    l1i_size = "32KiB",
    l1d_size = "16KiB",
    l2_size = "2MiB",
    l3_size = "4MiB"
)

memory = CustomMemory (
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
