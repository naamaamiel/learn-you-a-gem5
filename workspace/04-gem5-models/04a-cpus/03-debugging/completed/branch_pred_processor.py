from gem5.isas import ISA
from gem5.components.processors.base_cpu_core import BaseCPUCore
from gem5.components.processors.base_cpu_processor import BaseCPUProcessor

from m5.objects.RiscvCPU import RiscvMinorCPU
from m5.objects.FuncUnitConfig import *

class BranchPredMinorCPU(RiscvMinorCPU):
    def __init__(self, branch_predictor):
        super().__init__()
        self.branchPred = branch_predictor

class BranchPredCore(BaseCPUCore):
    def __init__(self, branch_predictor):
        core = BranchPredMinorCPU(branch_predictor)
        super().__init__(core, ISA.RISCV)


class BranchPredProcessor(BaseCPUProcessor):
    def __init__(self, branch_predictor):
        core_list = [BranchPredCore(branch_predictor)]
        super().__init__(
            cores = core_list
        )
