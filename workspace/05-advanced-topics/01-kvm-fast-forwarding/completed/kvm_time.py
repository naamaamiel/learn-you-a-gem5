from gem5.components.cachehierarchies.classic.private_l1_cache_hierarchy import (
    PrivateL1CacheHierarchy
)
from gem5.components.boards.x86_board import X86Board
from gem5.components.memory import DualChannelDDR4_2400
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_switchable_processor import (
    SimpleSwitchableProcessor,
)
from gem5.isas import ISA
from gem5.resources.resource import obtain_resource
from gem5.simulate.simulator import (
    ExitEvent,
    Simulator,
)
from gem5.utils.requires import requires
import m5

from gem5.simulate.exit_handler import (
    register_exit_handler,
)

requires(
    isa_required=ISA.X86,
    kvm_required=True,
)


cache_hierarchy = PrivateL1CacheHierarchy(
    l1d_size="32KiB",
    l1i_size="32KiB"
)

memory = DualChannelDDR4_2400(size="3GiB")

# Set up the processor. The SimpleSwitchableProcessor allows for
# switching between different CPU types during simulation, such as KVM to Timing
processor = SimpleSwitchableProcessor(
  starting_core_type = CPUTypes.KVM,
  switch_core_type = CPUTypes.TIMING,
  isa = ISA.X86, 
  num_cores = 2
)

# If needed, don't use perf
# uncomment the below lines if simulation errors occur
# for proc in processor.start:
#     proc.core.usePerf = False

board = X86Board(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

board.set_workload(obtain_resource("x86-ubuntu-24.04-npb-ep-a"))

# Set up an ROI begin handler to reset stats and switch to TIMING CPU

def ROI_begin_handler(simulator, payload):
  print("Reached the ROI!")

  print("Dump the current stats")
  m5.stats.dump()

  print("Switching from KVM to TIMING CPU")
  processor.switch()

  simulator.set_max_ticks(1000_000_000)

  print("Resetting stats at the start of ROI!")
  m5.stats.reset()

  return False

register_exit_handler(4, ROI_begin_handler, "ROI begin handler")

simulator = Simulator(board=board)
simulator.run()
