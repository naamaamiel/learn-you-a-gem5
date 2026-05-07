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
class ClassicExitHandler(ExitHandler, hypercall_num=0):

  def __init__(self, payload):
    super().__init__(payload)
    self.should_exit = True
  
  def _process(self, simulator) -> None:
    # get the classic exit event type
    exit_enum = ExitEvent.translate_exit_status(
      simulator.get_last_exit_event_cause()
    )
    # check for MAX_INSTS
    if exit_enum == ExitEvent.MAX_INSTS:
      print("Reached the 1,000,000th instruction!")
      print(f"Current tick is {simulator.get_current_tick()}")
      scheduleTickExitFromCurrent(1_000, "1,000 ticks from the 1,000,000th instruction")
      self.should_exit = False
    else:
      print("Encountered a classic exit event!")
      self.should_exit = True
  
  def _exit_simulation(self):
    return self.should_exit

class MyScheduledExitEventHandler(ScheduledExitEventHandler):
  num_hypercalls: int = 0 # Declare the class variable

  def _process(self, simulator):
    super()._process(simulator)
    MyScheduledExitEventHandler.num_hypercalls += 1 # Increment hypercall count

    print("Encountered a scheduled exit event!")
    print(f"Current tick is {simulator.get_current_tick()}")

    if MyScheduledExitEventHandler.num_hypercalls == 1:
      scheduleTickExitFromCurrent(1_000, "2,000 ticks from the 1,000,000th instruction")
      self.should_exit = False
    else:
      self.should_exit = True

  def _exit_simulation(self):
    return self.should_exit

simulator = Simulator(board=board)
simulator.schedule_max_insts(1_000_000)
simulator.run()
