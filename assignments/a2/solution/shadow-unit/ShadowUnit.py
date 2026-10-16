from m5.objects.BaseShadowUnit import BaseShadowUnit
from m5.params import *


class ShadowUnit(BaseShadowUnit):
    type = "ShadowUnit"
    cxx_header = "bootcamp/shadow-unit/shadow_unit.hh"
    cxx_class = "gem5::ShadowUnit"

    num_lanes = Param.Unsigned("Number of shadow executions in flight at once")
    compare_latency = Param.Cycles("Latency of the comparator")
    fault_period = Param.Unsigned(
        0, "Corrupt about one in this many shadow results (0: never)"
    )
    fault_seed = Param.Unsigned(1, "Seed for the shadow fault injector")
