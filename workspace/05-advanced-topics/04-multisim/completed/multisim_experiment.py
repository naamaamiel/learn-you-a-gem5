from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.cachehierarchies.classic.private_l1_cache_hierarchy import PrivateL1CacheHierarchy
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.resources.resource import obtain_resource
from gem5.simulate.simulator import Simulator

import gem5.utils.multisim as multisim

multisim.set_num_processes(2)

for data_cache_size in ["8kB", "16kB"]:
  for instruction_cache_size in ["8kB", "16kB"]:
    cache_hierarchy = PrivateL1CacheHierarchy (
      l1d_size=data_cache_size,
      l1i_size=instruction_cache_size,
    )

    memory = SingleChannelDDR3_1600(size="32MB")

    processor = SimpleProcessor (
        cpu_type=CPUTypes.TIMING,
        isa=ISA.X86,
        num_cores=1,
    )

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
        id=f"process_{data_cache_size}_{instruction_cache_size}"
    )

    multisim.add_simulator(simulator)
