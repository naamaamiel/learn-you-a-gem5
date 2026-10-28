#ifndef __BOOTCAMP_PACKET_ENCRYPTOR_PACKET_ENCRYPTOR_HH__
#define __BOOTCAMP_PACKET_ENCRYPTOR_PACKET_ENCRYPTOR_HH__

#include <queue>
#include <vector>

#include "mem/packet.hh"
#include "mem/port.hh"
#include "params/PacketEncryptor.hh"
#include "sim/clocked_object.hh"
#include "sim/eventq.hh"

namespace gem5
{

class PacketEncryptor : public ClockedObject
{
  private:
    class CPUSidePort: public ResponsePort
    {
      private:
        PacketEncryptor* owner;
        bool needToSendRetry;
        PacketPtr blockedPacket;

      public:
        CPUSidePort(PacketEncryptor* owner, const std::string& name):
            ResponsePort(name), owner(owner), needToSendRetry(false), blockedPacket(nullptr)
        {}
        bool needRetry() const { return needToSendRetry; }
        bool blocked() const { return blockedPacket != nullptr; }
        void sendPacket(PacketPtr pkt);

        virtual AddrRangeList getAddrRanges() const override;
        virtual bool recvTimingReq(PacketPtr pkt) override;
        virtual Tick recvAtomic(PacketPtr pkt) override;
        virtual void recvFunctional(PacketPtr pkt) override;
        virtual void recvRespRetry() override;
    };

    class MemSidePort: public RequestPort
    {
      private:
        PacketEncryptor* owner;
        bool needToSendRetry;
        PacketPtr blockedPacket;

      public:
        MemSidePort(PacketEncryptor* owner, const std::string& name):
            RequestPort(name), owner(owner), needToSendRetry(false), blockedPacket(nullptr)
        {}
        bool needRetry() const { return needToSendRetry; }
        bool blocked() const { return blockedPacket != nullptr; }
        void sendPacket(PacketPtr pkt);

        virtual bool recvTimingResp(PacketPtr pkt) override;
        virtual void recvReqRetry() override;
    };

    template<typename T>
    class TimedQueue
    {
      private:
        Tick latency;

        std::queue<T> items;
        std::queue<Tick> insertionTimes;

      public:
        TimedQueue(Tick latency): latency(latency) {}

        void push(T item, Tick insertion_time) {
            items.push(item);
            insertionTimes.push(insertion_time);
        }
        void pop() {
            items.pop();
            insertionTimes.pop();
        }

        T& front() { return items.front(); }
        Tick frontTime() { return insertionTimes.front(); }
        bool empty() const { return items.empty(); }
        size_t size() const { return items.size(); }
        bool hasReady(Tick current_time) const {
            if (empty()) {
                return false;
            }
            return (current_time - insertionTimes.front()) >= latency;
        }
        Tick firstReadyTime() { return insertionTimes.front() + latency; }
    };

    CPUSidePort cpuSidePort;
    MemSidePort memSidePort;

    int encryptionBufferEntries;
    TimedQueue<PacketPtr> encryptionBuffer;

    int decryptionBufferEntries;
    TimedQueue<PacketPtr> decryptionBuffer;

    int requestBufferEntries;
    TimedQueue<PacketPtr> requestBuffer;

    int responseBufferEntries;
    TimedQueue<PacketPtr> responseBuffer;

    int window;
    Cycles encDecLatency;
    int numUnits;

    std::vector<Tick> encryptionUnitAvailableTimes;
    std::vector<Tick> decryptionUnitAvailableTimes;

    EventFunctionWrapper nextReqSendEvent;
    void processNextReqSendEvent();
    void scheduleNextReqSendEvent(Tick when);

    EventFunctionWrapper nextReqRetryEvent;
    void processNextReqRetryEvent();
    void scheduleNextReqRetryEvent(Tick when);

    EventFunctionWrapper nextRespSendEvent;
    void processNextRespSendEvent();
    void scheduleNextRespSendEvent(Tick when);

    EventFunctionWrapper nextRespRetryEvent;
    void processNextRespRetryEvent();
    void scheduleNextRespRetryEvent(Tick when);

    EventFunctionWrapper nextEncryptionEvent;
    void processNextEncryptionEvent();
    void scheduleNextEncryptionEvent(Tick when);

    EventFunctionWrapper nextDecryptionEvent;
    void processNextDecryptionEvent();
    void scheduleNextDecryptionEvent(Tick when);

    Tick align(Tick when);

    void encryptRequest(PacketPtr pkt);
    void decryptResponse(PacketPtr pkt);

  public:
    PacketEncryptor(const PacketEncryptorParams& params);

    virtual void init() override;
    virtual Port& getPort(const std::string& if_name, PortID idx=InvalidPortID) override;

    AddrRangeList getAddrRanges() const;
    bool recvTimingReq(PacketPtr pkt);
    Tick recvAtomic(PacketPtr pkt);
    void recvFunctional(PacketPtr pkt);
    void recvReqRetry();

    bool recvTimingResp(PacketPtr pkt);
    void recvRespRetry();
};


} // namespace gem5

#endif // __BOOTCAMP_PACKET_ENCRYPTOR_PACKET_ENCRYPTOR_HH__
