# Imports
from gem5.components.memory.dram_interfaces.lpddr2 import LPDDR2_S4_1066_1x32
from gem5.components.memory.abstract_memory_system import AbstractMemorySystem
from gem5.components.memory.memory import ChanneledMemory
from typing import Optional

# Define SingleChannelLPDDR2
def SingleChannelLPDDR2(
    size: Optional[str] = None,
  ) -> AbstractMemorySystem:
  return ChanneledMemory(
    dram_interface_class = LPDDR2_S4_1066_1x32, 
    num_channels = 1,
    interleaving_size = 64,
    size=size
  )
