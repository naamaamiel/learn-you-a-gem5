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

requires(
    isa_required=ISA.X86,
    kvm_required=True,
)


cache_hierarchy = PrivateL1CacheHierarchy(
    l1d_size="32kB",
    l1i_size="32kB"
)

memory = DualChannelDDR4_2400(size="3GB")

# Here we set up the processor. The SimpleSwitchableProcessor allows for
# switching between different CPU types during simulation, such as KVM to Timing

processor = # TODO (2): Fill in a SimpleSwitchableProcessor here!

# Here we tell the KVM CPU (the starting CPU) not to use perf.

for proc in processor.start:
    proc.core.usePerf = False

board = X86Board(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

# TODO (1): Set the board's workload to the "npb-ep-a" workload.

# Set up workbegin handler to reset stats and switch to TIMING CPU

def workbegin_handler():
  pass # TODO (3): Replace this line with an appropriate workbegin handler

simulator = Simulator(
    board=board,
    on_exit_event = {
      # TODO (4): Set up the exit event handling
    }
)
simulator.run()