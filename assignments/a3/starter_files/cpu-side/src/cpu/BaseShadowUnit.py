from m5.objects.ClockedObject import ClockedObject


class BaseShadowUnit(ClockedObject):
    type = "BaseShadowUnit"
    abstract = True
    cxx_header = "cpu/base_shadow_unit.hh"
    cxx_class = "gem5::BaseShadowUnit"
