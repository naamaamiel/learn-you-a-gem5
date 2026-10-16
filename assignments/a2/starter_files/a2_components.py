"""
Assignment #2: Build-a-Shadow-Unit

Name:
"""

from gem5.components.processors.base_cpu_core import BaseCPUCore
from gem5.components.processors.base_cpu_processor import BaseCPUProcessor
from gem5.isas import ISA

from m5.objects.RiscvCPU import RiscvO3CPU


class ShadowO3CPU(RiscvO3CPU):
    def __init__(self, shadow_unit=None):
        super().__init__()
        if shadow_unit is not None:
            # TODO (Part 1): give this CPU its shadow unit, through the
            # CPU's shadowUnit parameter.
            pass


class ShadowCore(BaseCPUCore):
    def __init__(self, shadow_unit=None):
        super().__init__(ShadowO3CPU(shadow_unit), ISA.RISCV)


class ShadowProcessor(BaseCPUProcessor):
    def __init__(self, shadow_unit=None):
        super().__init__(cores=[ShadowCore(shadow_unit)])
