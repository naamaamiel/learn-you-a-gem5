"""
Assignment #1: Assemble-Your-Own-System

Name: Solution
"""

from gem5.isas import ISA
from gem5.components.processors.base_cpu_core import BaseCPUCore
from gem5.components.processors.base_cpu_processor import BaseCPUProcessor

from m5.objects.RiscvCPU import RiscvMinorCPU

class CustomCPU(RiscvMinorCPU):
    def __init__(self):
        super().__init__()
        self.decodeInputWidth = 4
        self.executeInputWidth = 4
        self.executeBranchDelay = 1

class CustomCore(BaseCPUCore):
    def __init__(self):
        core = CustomCPU()
        super().__init__(core, ISA.RISCV)

class CustomProcessor(BaseCPUProcessor):
    def __init__(self):
        core_list = [CustomCore(), CustomCore()]
        super().__init__(
            cores = core_list
        )
