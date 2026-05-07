from gem5.isas import ISA
from gem5.components.boards.x86_board import X86Board
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import PrivateL1SharedL2CacheHierarchy
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.components.processors.cpu_types import CPUTypes

from gem5.components.processors.simple_processor import SimpleProcessor

from gem5.simulate.exit_handler import (
    ExitHandler,
    ScheduledExitEventHandler,
)

from gem5.simulate.exit_event import ExitEvent

from m5.simulate import scheduleTickExitFromCurrent

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

# Set the workload to boot linux (Ubuntu 24.04)
# We will do "no systemd" to save some time
board.set_workload(
    obtain_resource("x86-ubuntu-24.04-boot-no-systemd")
)

# Custom exit event handlers

# Classic exit event handler goes HERE:

# Scheduled exit event handler goes HERE:


simulator = Simulator(board=board)

# Schedule a classic exit event at the 1,000,000th instruction HERE

simulator.run()
