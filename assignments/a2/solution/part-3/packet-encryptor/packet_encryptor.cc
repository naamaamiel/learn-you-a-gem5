#include "bootcamp/packet-encryptor/packet_encryptor.hh"

#include <algorithm>
#include <cmath>

#include "debug/Encryptor.hh"

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
    requestBufferEntries(params.request_buffer_entries),
    requestBuffer(clockPeriod()),
    responseBufferEntries(params.response_buffer_entries),
    responseBuffer(clockPeriod()),
    window(params.window),
    encDecLatency(params.enc_dec_latency),
    numUnits(params.num_units),
    encryptionUnitAvailableTimes((size_t) params.num_units, 0),
    decryptionUnitAvailableTimes((size_t) params.num_units, 0),
    nextReqSendEvent([this](){ processNextReqSendEvent(); }, name() + ".nextReqSendEvent"),
    nextReqRetryEvent([this](){ processNextReqRetryEvent(); }, name() + ".nextReqRetryEvent"),
    nextRespSendEvent([this](){ processNextRespSendEvent(); }, name() + ".nextRespSendEvent"),
    nextRespRetryEvent([this](){ processNextRespRetryEvent(); }, name() + ".nextRespRetryEvent"),
    nextEncryptionEvent([this](){ processNextEncryptionEvent(); }, name() + ".nextEncryptionEvent"),
    nextDecryptionEvent([this](){ processNextDecryptionEvent(); }, name() + ".nextDecryptionEvent")
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
    DPRINTF(Encryptor, "%s: Received timing request packet %s\n", __func__, pkt->print());

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
    scheduleNextEncryptionEvent(nextCycle());
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

    DPRINTF(Encryptor, "%s: CPUSidePort sending packet %s in timing mode\n", __func__, pkt->print());

    if (!sendTimingResp(pkt)) {
        DPRINTF(Encryptor, "%s: CPUSidePort failed to send packet %s in timing mode\n", __func__, pkt->print());
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
    
    DPRINTF(Encryptor, "%s: MemSidePort sending packet %s in timing mode\n", __func__, pkt->print());

    if (!sendTimingReq(pkt)) {
        DPRINTF(Encryptor, "%s: MemSidePort failed to send packet %s in timing mode\n", __func__, pkt->print());
        blockedPacket = pkt;
    }
}

bool
PacketEncryptor::MemSidePort::recvTimingResp(PacketPtr pkt)
{
    DPRINTF(Encryptor, "%s: Received timing response packet %s\n", __func__, pkt->print());

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
    scheduleNextDecryptionEvent(nextCycle());
    return true;
}

void
PacketEncryptor::MemSidePort::recvReqRetry()
{
    panic_if(!blocked(), "Should never receive retry if not blocked!");

    DPRINTF(Encryptor, "%s: MemSidePort received retry signal\n", __func__);

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
    panic_if(!requestBuffer.hasReady(curTick()), "Should never try to send if no ready packets!");

    PacketPtr pkt = requestBuffer.front();
    memSidePort.sendPacket(pkt);
    requestBuffer.pop();

    scheduleNextEncryptionEvent(nextCycle());
    scheduleNextReqSendEvent(nextCycle());
}

void
PacketEncryptor::scheduleNextReqSendEvent(Tick when)
{
    bool port_avail = !memSidePort.blocked();
    bool have_items = !requestBuffer.empty();

    if (port_avail && have_items && !nextReqSendEvent.scheduled()) {
        Tick schedule_time = align(std::max(when, requestBuffer.firstReadyTime()));
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
    panic_if(!responseBuffer.hasReady(curTick()), "Should never try to send if no ready packets!");

    PacketPtr pkt = responseBuffer.front();
    cpuSidePort.sendPacket(pkt);
    responseBuffer.pop();

    scheduleNextDecryptionEvent(nextCycle());
    scheduleNextRespSendEvent(nextCycle());
}

void
PacketEncryptor::scheduleNextRespSendEvent(Tick when)
{
    bool port_avail = !cpuSidePort.blocked();
    bool have_items = !responseBuffer.empty();

    if (port_avail && have_items && !nextRespSendEvent.scheduled()) {
        Tick schedule_time = align(std::max(when, responseBuffer.firstReadyTime()));
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

void
PacketEncryptor::processNextEncryptionEvent()
{
    panic_if(!encryptionBuffer.hasReady(curTick()), "Should not encrypt a packet if none are ready!\n");

    int packets_left_in_window = window;

    for (int i = 0; i < encryptionUnitAvailableTimes.size(); i++) {
        if (!encryptionBuffer.hasReady(curTick())) {
            DPRINTF(Encryptor, "%s: No more packets in encryption buffer\n", __func__);
            break;
        }

        if (requestBuffer.size() >= requestBufferEntries) {
            DPRINTF(Encryptor, "%s: No more room in the request buffer for encrypted packets\n", __func__);
            break;
        }

        if (encryptionUnitAvailableTimes[i] <= curTick()) {
            DPRINTF(Encryptor, "%s: Encryption unit %d available\n", __func__, i);
            PacketPtr pkt = encryptionBuffer.front();
            encryptRequest(pkt);
            encryptionBuffer.pop();
            requestBuffer.push(pkt, curTick());
            encryptionUnitAvailableTimes[i] = clockEdge(encDecLatency);
            packets_left_in_window--;
            if (packets_left_in_window == 0) {
                break;
            }
        }
    }
    scheduleNextReqSendEvent(nextCycle());
    scheduleNextReqRetryEvent(nextCycle());
    scheduleNextEncryptionEvent(nextCycle());
}

void PacketEncryptor::scheduleNextEncryptionEvent(Tick when)
{
    bool have_packet = !encryptionBuffer.empty();
    bool room_in_request_buffer = requestBuffer.size() < requestBufferEntries;

    if (have_packet && room_in_request_buffer && !nextEncryptionEvent.scheduled()) {
        Tick first_avail_time = *std::min_element(encryptionUnitAvailableTimes.begin(),
                                                  encryptionUnitAvailableTimes.end());
        Tick schedule_time = align(std::max({when, 
                                            encryptionBuffer.firstReadyTime(),
                                            first_avail_time}));
        schedule(nextEncryptionEvent, schedule_time);
    }
}

void
PacketEncryptor::processNextDecryptionEvent()
{
    panic_if(!decryptionBuffer.hasReady(curTick()), "Should not decrypt a packet if none are ready!\n");

    int packets_left_in_window = window;

    for (int i = 0; i < decryptionUnitAvailableTimes.size(); i++) {
        if (!decryptionBuffer.hasReady(curTick())) {
            DPRINTF(Encryptor, "%s: No more packets in decryption buffer\n", __func__);
            break;
        }

        if (responseBuffer.size() >= responseBufferEntries) {
            DPRINTF(Encryptor, "%s: No more room in the response buffer for decrypted packets\n", __func__);
            break;
        }

        if (decryptionUnitAvailableTimes[i] <= curTick()) {
            DPRINTF(Encryptor, "%s: Decryption unit %d available\n", __func__, i);
            PacketPtr pkt = decryptionBuffer.front();
            decryptResponse(pkt);
            decryptionBuffer.pop();
            responseBuffer.push(pkt, curTick());
            decryptionUnitAvailableTimes[i] = clockEdge(encDecLatency);
            packets_left_in_window--;
            if (packets_left_in_window == 0) {
                break;
            }
        }
    }

    scheduleNextRespSendEvent(nextCycle());
    scheduleNextRespRetryEvent(nextCycle());
    scheduleNextDecryptionEvent(nextCycle());
}

void PacketEncryptor::scheduleNextDecryptionEvent(Tick when)
{
    bool have_packet = !decryptionBuffer.empty();
    bool room_in_response_buffer = responseBuffer.size() < responseBufferEntries;

    if (have_packet && room_in_response_buffer && !nextDecryptionEvent.scheduled()) {
        Tick first_avail_time = *std::min_element(decryptionUnitAvailableTimes.begin(),
                                                  decryptionUnitAvailableTimes.end());
        Tick schedule_time = align(std::max({when,
                                            decryptionBuffer.firstReadyTime(),
                                            first_avail_time}));
        schedule(nextDecryptionEvent, schedule_time);
    }
}

void
PacketEncryptor::encryptRequest(PacketPtr pkt)
{
    panic_if(!pkt->isRequest(), "%s: Cannot encrypt non-request packet %s\n", __func__, pkt->print());

    if (pkt->isWrite() && pkt->hasData()) {
        uint64_t data = pkt->getRaw<uint64_t>();
        DPRINTF(Encryptor, "%s: Encrypting packet %s, data was %lx\n", __func__, pkt->print(), data);
        data = ~data;
        pkt->setRaw<uint64_t>(data);
    } else {
        DPRINTF(Encryptor, "%s: No need to encrypt packet %s\n", __func__, pkt->print());
    }
}

void
PacketEncryptor::decryptResponse(PacketPtr pkt)
{
    panic_if(!pkt->isResponse(), "%s: Cannot decrypt non-response packet %s\n", __func__, pkt->print());

    if (pkt->isRead() && pkt->hasData()) {
        uint64_t data = pkt->getRaw<uint64_t>();
        data = ~data;
        pkt->setRaw<uint64_t>(data);
        DPRINTF(Encryptor, "%s: Decrypting packet %s, data is now %lx\n", __func__, pkt->print(), data);
    } else {
        DPRINTF(Encryptor, "%s: No need to decrypt packet %s\n", __func__, pkt->print());
    }
}

} // namespace gem5
