#ifndef __CPU_BASE_SHADOW_UNIT_HH__
#define __CPU_BASE_SHADOW_UNIT_HH__

#include "base/types.hh"
#include "cpu/inst_seq.hh"
#include "params/BaseShadowUnit.hh"
#include "sim/clocked_object.hh"

namespace gem5
{

class ShadowClient;

/** One check. The CPU fills in everything except shadow and match. */
struct ShadowCheck
{
    /** The CPU that asked for the check. sendVerdict() answers it. */
    ShadowClient *client;
    /** Sequence number of the instruction (for debug output). */
    InstSeqNum seqNum;
    /** PC of the instruction (for debug output). */
    Addr pc;
    /** Latency of the functional unit P ran on. S takes as long. */
    Cycles latency;
    /** P's result: the value the core wrote to the register file. */
    RegVal primary;
    /** The value a fault-free execution produces. */
    RegVal golden;

    /** S's result. Written by the shadow unit. */
    RegVal shadow;
    /** True if S's result equals P's. Written by the shadow unit. */
    bool match;
};

/** Implemented by the CPU: where verdicts go. */
class ShadowClient
{
  public:
    virtual ~ShadowClient() = default;

    /** Record check's verdict. Never calls back into the shadow unit. */
    virtual void recvVerdict(ShadowCheck *check) = 0;
};

/**
 * The base class of every shadow unit. The CPU calls requestCheck() in
 * the cycle an instruction executes, and the unit answers later, from
 * one of its events, with sendVerdict().
 */
class BaseShadowUnit : public ClockedObject
{
  public:
    BaseShadowUnit(const BaseShadowUnitParams &params)
        : ClockedObject(params)
    {}

    /**
     * Offer the unit a check. Return true to accept it, or false if the
     * unit can't take it this cycle; the CPU offers it again next cycle.
     */
    virtual bool requestCheck(ShadowCheck *check) = 0;

  protected:
    /** Send check's verdict to the CPU that asked for it. */
    void
    sendVerdict(ShadowCheck *check)
    {
        check->client->recvVerdict(check);
    }
};

} // namespace gem5

#endif // __CPU_BASE_SHADOW_UNIT_HH__
