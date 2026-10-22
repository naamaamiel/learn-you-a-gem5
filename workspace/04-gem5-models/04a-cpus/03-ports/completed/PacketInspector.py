from m5.objects.ClockedObject import ClockedObject
from m5.params import *


class PacketInspector(ClockedObject):
    type = "PacketInspector"
    cxx_header = "bootcamp/packet-inspector/packet_inspector.hh"
    cxx_class = "gem5::PacketInspector"

    cpu_side_port = ResponsePort(
        "ResponsePort to received requests from CPU side."
    )
    mem_side_port = RequestPort(
        "RequestPort to send received requests to memory side."
    )

    inspection_buffer_entries = Param.Int(
        "Number of entries in the inspection buffer."
    )
    response_buffer_entries = Param.Int(
        "Number of entries in the response buffer."
    )
