from m5.objects.BaseShadowUnit import BaseShadowUnit
from m5.params import *


class ShadowUnit(BaseShadowUnit):
    type = "ShadowUnit"
    cxx_header = "bootcamp/shadow-unit/shadow_unit.hh"
    cxx_class = "gem5::ShadowUnit"

    # TODO (Part 1): declare the four parameters listed in Step 1.1 of the
    # assignment.
