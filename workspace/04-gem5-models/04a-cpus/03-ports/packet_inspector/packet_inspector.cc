#include "bootcamp/packet-inspector/packet_inspector.hh"

#include <cmath>

namespace gem5
{

PacketInspector::PacketInspector(const PacketInspectorParams& params):
    ClockedObject(params),
    inspectionBufferEntries(params.inspection_buffer_entries),
    responseBufferEntries(params.response_buffer_entries),
{}

Tick
PacketInspector::align(Tick when)
{
    return clockEdge((Cycles) std::ceil((when - curTick()) / clockPeriod()));
}

} // namespace gem5
