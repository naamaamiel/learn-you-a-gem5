"""
This script is the starting point for the multisim exercise.

Usage
-----
# This will run all the simulations in parallel.
gem5 -m gem5.multisim multisim-experiment.py path/to/multisim-experiment.py

"""

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.cachehierarchies.classic.private_l1_cache_hierarchy import PrivateL1CacheHierarchy
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.resources.resource import obtain_resource
from gem5.simulate.simulator import Simulator

cache_hierarchy = PrivateL1CacheHierarchy(
    l1d_size="8kiB",
    l1i_size="8kiB",
)

memory = SingleChannelDDR3_1600(size="32MiB")

processor = SimpleProcessor(cpu_type=CPUTypes.TIMING, isa=ISA.X86, num_cores=1)

board = SimpleBoard(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

board.set_se_binary_workload(
    obtain_resource("x86-matrix-multiply")
)

simulator = Simulator(
    board=board,
)

simulator.run()
