from gem5.isas import ISA
from gem5.components.boards.x86_board import X86Board
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import PrivateL1SharedL2CacheHierarchy
from gem5.components.processors.cpu_types import CPUTypes

from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.memory.multi_channel import DualChannelDDR4_2400

# import memory HERE
from gem5.components.memory.simple import SingleChannelSimpleMemory

# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator


processor = SimpleProcessor(
    cpu_type = CPUTypes.TIMING,
    isa = ISA.X86,
    num_cores = 1
)

cache = PrivateL1SharedL2CacheHierarchy(
    l1d_size = "16KiB",
    l1i_size = "16KiB",
    l2_size = "256KiB",
    l1d_assoc = 8,
    l1i_assoc = 8,
    l2_assoc = 16
)

memory = DualChannelDDR4_2400 (
  size = "3GiB"
)

# memory = SingleChannelSimpleMemory(
#     latency = "50ns",
#     latency_var = "10ns",
#     bandwidth = "32 GiB/s",
#     size = "3GiB"
# )

# A full-system x86 board
board = X86Board(
    clk_freq="3GHz",
    processor = processor,
    cache_hierarchy = cache,
    memory = memory
)

board.set_workload(
    obtain_resource("x86-matrix-multiply-run")
)

sim = Simulator(board)
sim.run()
