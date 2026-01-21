from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.cachehierarchies.classic.private_l1_cache_hierarchy import PrivateL1CacheHierarchy
from gem5.components.memory.single_channel import SingleChannelDDR3_1600
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.resources.resource import obtain_resource
from gem5.simulate.simulator import Simulator


# A simple script to test with different CPU models
# We will run a simple application (matrix-multiply) with AtomicSimpleCPU and TimingSimpleCPU
# using two different cache sizes

# Start with 32KiB and change to 1KiB
cache_hierarchy = PrivateL1CacheHierarchy(
    l1d_size="1KiB",        # l1d_size="32KiB"
    l1i_size="1KiB"         # l1d_size="32KiB"
)

memory = SingleChannelDDR3_1600("1GiB")

# By default, use Atomic CPU
cpu_type = CPUTypes.TIMING      # cpu_type = CPUTypes.ATOMIC

processor = SimpleProcessor(
    cpu_type=cpu_type, 
    isa=ISA.RISCV, 
    num_cores=1
)

board = SimpleBoard(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy
)

# Resources can be found at
    # https://resources.gem5.org/
# riscv-matrix-multiply is obtained from
    # https://resources.gem5.org/resources/riscv-getting-started-benchmark-suite?version=1.0.0

workload = obtain_resource("riscv-matrix-multiply-run")
board.set_workload(workload)
simulator = Simulator(board=board)
simulator.run()
