#include "bootcamp/packet-encryptor/packet_encryptor.hh"

#include <algorithm>
#include <cmath>

namespace gem5
{

PacketEncryptor::PacketEncryptor(const PacketEncryptorParams& params):
    ClockedObject(params),
    cpuSidePort(this, name() + ".cpu_side_port"),
    memSidePort(this, name() + ".mem_side_port"),
    encryptionBufferEntries(params.encryption_buffer_entries),
    encryptionBuffer(clockPeriod()),
    decryptionBufferEntries(params.decryption_buffer_entries),
    decryptionBuffer(clockPeriod()),
    nextReqSendEvent([this](){ processNextReqSendEvent(); }, name() + ".nextReqSendEvent"),
    nextReqRetryEvent([this](){ processNextReqRetryEvent(); }, name() + ".nextReqRetryEvent"),
    nextRespSendEvent([this](){ processNextRespSendEvent(); }, name() + ".nextRespSendEvent"),
    nextRespRetryEvent([this](){ processNextRespRetryEvent(); }, name() + ".nextRespRetryEvent")
{}

void
PacketEncryptor::init()
{
    cpuSidePort.sendRangeChange();
}

Port&
PacketEncryptor::getPort(const std::string &if_name, PortID idx)
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
PacketEncryptor::align(Tick when)
{
    return clockEdge((Cycles) std::ceil((when - curTick()) / clockPeriod()));
}

AddrRangeList
PacketEncryptor::CPUSidePort::getAddrRanges() const
{
    return owner->getAddrRanges();
}

AddrRangeList
PacketEncryptor::getAddrRanges() const
{
    return memSidePort.getAddrRanges();
}

bool
PacketEncryptor::CPUSidePort::recvTimingReq(PacketPtr pkt)
{
    if (owner->recvTimingReq(pkt)) {
        needToSendRetry = false;
        return true;
    }
    needToSendRetry = true;
    return false;
}

bool
PacketEncryptor::recvTimingReq(PacketPtr pkt)
{
    if (encryptionBuffer.size() >= encryptionBufferEntries) {
        return false;
    }
    encryptionBuffer.push(pkt, curTick());
    scheduleNextReqSendEvent(nextCycle());
    return true;
}

Tick
PacketEncryptor::CPUSidePort::recvAtomic(PacketPtr pkt)
{
    return owner->recvAtomic(pkt);
}

Tick
PacketEncryptor::recvAtomic(PacketPtr pkt)
{
    return clockPeriod() + memSidePort.sendAtomic(pkt);
}

void
PacketEncryptor::CPUSidePort::recvFunctional(PacketPtr pkt)
{
    owner->recvFunctional(pkt);
}

void
PacketEncryptor::recvFunctional(PacketPtr pkt)
{
    memSidePort.sendFunctional(pkt);
}

void
PacketEncryptor::CPUSidePort::sendPacket(PacketPtr pkt)
{
    panic_if(blocked(), "Should never try to send if blocked!");

    if (!sendTimingResp(pkt)) {
        blockedPacket = pkt;
    }
}

void
PacketEncryptor::CPUSidePort::recvRespRetry()
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
PacketEncryptor::recvRespRetry()
{
    scheduleNextRespSendEvent(nextCycle());
}

void
PacketEncryptor::MemSidePort::sendPacket(PacketPtr pkt)
{
    panic_if(blocked(), "Should never try to send if blocked!");

    if (!sendTimingReq(pkt)) {
        blockedPacket = pkt;
    }
}

bool
PacketEncryptor::MemSidePort::recvTimingResp(PacketPtr pkt)
{
    if (owner->recvTimingResp(pkt)) {
        needToSendRetry = false;
        return true;
    }
    needToSendRetry = true;
    return false;
}

bool
PacketEncryptor::recvTimingResp(PacketPtr pkt)
{
    if (decryptionBuffer.size() >= decryptionBufferEntries) {
        return false;
    }
    decryptionBuffer.push(pkt, curTick());
    scheduleNextRespSendEvent(nextCycle());
    return true;
}

void
PacketEncryptor::MemSidePort::recvReqRetry()
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
PacketEncryptor::recvReqRetry()
{
    scheduleNextReqSendEvent(nextCycle());
}

void
PacketEncryptor::processNextReqSendEvent()
{
    panic_if(memSidePort.blocked(), "Should never try to send if blocked!");
    panic_if(!encryptionBuffer.hasReady(curTick()), "Should never try to send if no ready packets!");

    PacketPtr pkt = encryptionBuffer.front();
    memSidePort.sendPacket(pkt);
    encryptionBuffer.pop();

    scheduleNextReqRetryEvent(nextCycle());
    scheduleNextReqSendEvent(nextCycle());
}

void
PacketEncryptor::scheduleNextReqSendEvent(Tick when)
{
    bool port_avail = !memSidePort.blocked();
    bool have_items = !encryptionBuffer.empty();

    if (port_avail && have_items && !nextReqSendEvent.scheduled()) {
        Tick schedule_time = align(std::max(when, encryptionBuffer.firstReadyTime()));
        schedule(nextReqSendEvent, schedule_time);
    }
}

void
PacketEncryptor::processNextReqRetryEvent()
{
    panic_if(!cpuSidePort.needRetry(), "Should never try to send retry if not needed!");
    cpuSidePort.sendRetryReq();
}

void
PacketEncryptor::scheduleNextReqRetryEvent(Tick when)
{
    if (cpuSidePort.needRetry() && !nextReqRetryEvent.scheduled()) {
        schedule(nextReqRetryEvent, align(when));
    }
}

void
PacketEncryptor::processNextRespSendEvent()
{
    panic_if(cpuSidePort.blocked(), "Should never try to send if blocked!");
    panic_if(!decryptionBuffer.hasReady(curTick()), "Should never try to send if no ready packets!");

    PacketPtr pkt = decryptionBuffer.front();
    cpuSidePort.sendPacket(pkt);
    decryptionBuffer.pop();

    scheduleNextRespRetryEvent(nextCycle());
    scheduleNextRespSendEvent(nextCycle());
}

void
PacketEncryptor::scheduleNextRespSendEvent(Tick when)
{
    bool port_avail = !cpuSidePort.blocked();
    bool have_items = !decryptionBuffer.empty();

    if (port_avail && have_items && !nextRespSendEvent.scheduled()) {
        Tick schedule_time = align(std::max(when, decryptionBuffer.firstReadyTime()));
        schedule(nextRespSendEvent, schedule_time);
    }
}

void
PacketEncryptor::processNextRespRetryEvent()
{
    panic_if(!memSidePort.needRetry(), "Should never try to send retry if not needed!");
    memSidePort.sendRetryResp();
}

void
PacketEncryptor::scheduleNextRespRetryEvent(Tick when)
{
    if (memSidePort.needRetry() && !nextRespRetryEvent.scheduled()) {
        schedule(nextRespRetryEvent, align(when));
    }
}

} // namespace gem5
