#include "bootcamp/packet-inspector/packet_inspector.hh"

#include <algorithm>
#include <cmath>

namespace gem5
{

PacketInspector::PacketInspector(const PacketInspectorParams& params):
    ClockedObject(params),
    cpuSidePort(this, name() + ".cpu_side_port"),
    memSidePort(this, name() + ".mem_side_port"),
    inspectionBufferEntries(params.inspection_buffer_entries),
    inspectionBuffer(clockPeriod()),
    responseBufferEntries(params.response_buffer_entries),
    responseBuffer(clockPeriod()),
    nextReqSendEvent([this](){ processNextReqSendEvent(); }, name() + ".nextReqSendEvent"),
    nextReqRetryEvent([this](){ processNextReqRetryEvent(); }, name() + ".nextReqRetryEvent"),
    nextRespSendEvent([this](){ processNextRespSendEvent(); }, name() + ".nextRespSendEvent"),
    nextRespRetryEvent([this](){ processNextRespRetryEvent(); }, name() + ".nextRespRetryEvent")
{}

void
PacketInspector::init()
{
    cpuSidePort.sendRangeChange();
}

Port&
PacketInspector::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "cpu_side_port") {
        return cpuSidePort;
    } else if (if_name == "mem_side_port") {
        return memSidePort;
    } else {
        return ClockedObject::getPort(if_name, idx);
    }
}

Tick
PacketInspector::align(Tick when)
{
    return clockEdge((Cycles) std::ceil((when - curTick()) / clockPeriod()));
}

AddrRangeList
PacketInspector::CPUSidePort::getAddrRanges() const
{
    return owner->getAddrRanges();
}

AddrRangeList
PacketInspector::getAddrRanges() const
{
    return memSidePort.getAddrRanges();
}

bool
PacketInspector::CPUSidePort::recvTimingReq(PacketPtr pkt)
{
    if (owner->recvTimingReq(pkt)) {
        return true;
    }
    needToSendRetry = true;
    return false;
}

bool
PacketInspector::recvTimingReq(PacketPtr pkt)
{
    if (inspectionBuffer.size() >= inspectionBufferEntries) {
        return false;
    }
    inspectionBuffer.push(pkt, curTick());
    scheduleNextReqSendEvent(nextCycle());
    return true;
}

Tick
PacketInspector::CPUSidePort::recvAtomic(PacketPtr pkt)
{
    return owner->recvAtomic(pkt);
}

Tick
PacketInspector::recvAtomic(PacketPtr pkt)
{
    return clockPeriod() + memSidePort.sendAtomic(pkt);
}

void
PacketInspector::CPUSidePort::recvFunctional(PacketPtr pkt)
{
    owner->recvFunctional(pkt);
}

void
PacketInspector::recvFunctional(PacketPtr pkt)
{
    memSidePort.sendFunctional(pkt);
}

void
PacketInspector::CPUSidePort::sendPacket(PacketPtr pkt)
{
    panic_if(blocked(), "Should never try to send if blocked!");

    if (!sendTimingResp(pkt)) {
        blockedPacket = pkt;
    }
}

void
PacketInspector::CPUSidePort::recvRespRetry()
{
    panic_if(!blocked(), "Should never receive retry if not blocked!");

    PacketPtr pkt = blockedPacket;
    blockedPacket = nullptr;
    sendPacket(pkt);

    if (!blocked()) {
        owner->recvRespRetry();
    }
}

void
PacketInspector::recvRespRetry()
{
    scheduleNextRespSendEvent(nextCycle());
}

void
PacketInspector::MemSidePort::sendPacket(PacketPtr pkt)
{
    panic_if(blocked(), "Should never try to send if blocked!");

    if (!sendTimingReq(pkt)) {
        blockedPacket = pkt;
    }
}

bool
PacketInspector::MemSidePort::recvTimingResp(PacketPtr pkt)
{
    if (owner->recvTimingResp(pkt)) {
        return true;
    }
    needToSendRetry = true;
    return false;
}

bool
PacketInspector::recvTimingResp(PacketPtr pkt)
{
    if (responseBuffer.size() >= responseBufferEntries) {
        return false;
    }
    responseBuffer.push(pkt, curTick());
    scheduleNextRespSendEvent(nextCycle());
    return true;
}

void
PacketInspector::MemSidePort::recvReqRetry()
{
    panic_if(!blocked(), "Should never receive retry if not blocked!");

    PacketPtr pkt = blockedPacket;
    blockedPacket = nullptr;
    sendPacket(pkt);

    if (!blocked()) {
        owner->recvReqRetry();
    }
}

void
PacketInspector::recvReqRetry()
{
    scheduleNextReqSendEvent(nextCycle());
}

void
PacketInspector::processNextReqSendEvent()
{
    panic_if(memSidePort.blocked(), "Should never try to send if blocked!");
    panic_if(!inspectionBuffer.hasReady(curTick()), "Should never try to send if no ready packets!");

    PacketPtr pkt = inspectionBuffer.front();
    memSidePort.sendPacket(pkt);
    inspectionBuffer.pop();

    scheduleNextReqRetryEvent(nextCycle());
    scheduleNextReqSendEvent(nextCycle());
}

void
PacketInspector::scheduleNextReqSendEvent(Tick when)
{
    bool port_avail = !memSidePort.blocked();
    bool have_items = !inspectionBuffer.empty();

    if (port_avail && have_items && !nextReqSendEvent.scheduled()) {
        Tick schedule_time = align(std::max(when, inspectionBuffer.firstReadyTime()));
        schedule(nextReqSendEvent, schedule_time);
    }
}

void
PacketInspector::processNextReqRetryEvent()
{
    panic_if(!cpuSidePort.needRetry(), "Should never try to send retry if not needed!");
    cpuSidePort.sendRetryReq();
}

void
PacketInspector::scheduleNextReqRetryEvent(Tick when)
{
    if (cpuSidePort.needRetry() && !nextReqRetryEvent.scheduled()) {
        schedule(nextReqRetryEvent, align(when));
    }
}

void
PacketInspector::processNextRespSendEvent()
{
    panic_if(cpuSidePort.blocked(), "Should never try to send if blocked!");
    panic_if(!responseBuffer.hasReady(curTick()), "Should never try to send if no ready packets!");

    PacketPtr pkt = responseBuffer.front();
    cpuSidePort.sendPacket(pkt);
    responseBuffer.pop();

    scheduleNextRespRetryEvent(nextCycle());
    scheduleNextRespSendEvent(nextCycle());
}

void
PacketInspector::scheduleNextRespSendEvent(Tick when)
{
    bool port_avail = !cpuSidePort.blocked();
    bool have_items = !responseBuffer.empty();

    if (port_avail && have_items && !nextRespSendEvent.scheduled()) {
        Tick schedule_time = align(std::max(when, responseBuffer.firstReadyTime()));
        schedule(nextRespSendEvent, schedule_time);
    }
}

void
PacketInspector::processNextRespRetryEvent()
{
    panic_if(!memSidePort.needRetry(), "Should never try to send retry if not needed!");
    memSidePort.sendRetryResp();
}

void
PacketInspector::scheduleNextRespRetryEvent(Tick when)
{
    if (memSidePort.needRetry() && !nextRespRetryEvent.scheduled()) {
        schedule(nextRespRetryEvent, align(when));
    }
}

} // namespace gem5
