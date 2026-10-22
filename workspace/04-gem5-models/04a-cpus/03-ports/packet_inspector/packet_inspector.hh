#ifndef __BOOTCAMP_PACKET_INSPECTOR_PACKET_INSPECTOR_HH__
#define __BOOTCAMP_PACKET_INSPECTOR_PACKET_INSPECTOR_HH__

#include "params/PacketInspector.hh"
#include "sim/clocked_object.hh"

namespace gem5
{

class PacketInspector : public ClockedObject
{
  private:
    int inspectionBufferEntries;
    int responseBufferEntries;

    Tick align(Tick when);

  public:
    PacketInspector(const PacketInspectorParams& params);
};


} // namespace gem5

#endif // __BOOTCAMP_PACKET_INSPECTOR_PACKET_INSPECTOR_HH__
