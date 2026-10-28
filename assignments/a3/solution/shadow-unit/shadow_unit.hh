#ifndef __BOOTCAMP_SHADOW_UNIT_SHADOW_UNIT_HH__
#define __BOOTCAMP_SHADOW_UNIT_SHADOW_UNIT_HH__

#include <vector>

#include "base/random.hh"
#include "base/statistics.hh"
#include "cpu/base_shadow_unit.hh"
#include "params/ShadowUnit.hh"
#include "sim/eventq.hh"

namespace gem5
{

/**
 * A pool of generic lanes, like the O3 CPU's FUPool (src/cpu/o3/fu_pool.hh):
 * any lane can run S for any instruction, and S holds its lane for the
 * latency of the functional unit P ran on. Lanes aren't pipelined.
 */
class ShadowUnit : public BaseShadowUnit
{
  private:
    /**
     * Like the O3 CPU's FUCompletion (src/cpu/o3/inst_queue.hh): one per
     * check, scheduled for the cycle S finishes, and deleted after it runs.
     */
    class ShadowCompletion : public Event
    {
      private:
        /** The check whose S is running. */
        ShadowCheck *check;

        /** Index of the lane S runs on. */
        int lane;

        /** Pointer back to the shadow unit. */
        ShadowUnit *unit;

      public:
        ShadowCompletion(ShadowCheck *check, int lane, ShadowUnit *unit);

        void process() override;
        const char *description() const override;
    };

    const unsigned numLanes;
    const Cycles compareLatency;
    const unsigned faultPeriod;

    /** Random numbers for the shadow fault injector (Part 3). */
    Random::RandomPtr rng;

    /** Which lanes are running S, like FUPool::unitBusy. */
    std::vector<bool> laneBusy;

    /** What getLane() returns when every lane is busy. */
    static constexpr int NoFreeLane = -1;

    /**
     * Take a free lane and mark it busy, like FUPool::getUnit(). Returns
     * its index, or NoFreeLane if every lane is busy.
     */
    int getLane();

    /** S finished on lane: free the lane, and start the comparison. */
    void processShadowDone(ShadowCheck *check, int lane);

    /** check's comparison finished: compare, and send the verdict. */
    void processCompareDone(ShadowCheck *check);

    struct ShadowUnitStats : public statistics::Group
    {
        ShadowUnitStats(statistics::Group *parent);

        statistics::Scalar checks;
        statistics::Scalar laneCycles;
        statistics::Scalar rejections;
        statistics::Scalar passes;
        statistics::Scalar mismatches;
        statistics::Scalar faultsInjected;
    } stats;

  public:
    ShadowUnit(const ShadowUnitParams &params);

    bool requestCheck(ShadowCheck *check) override;
};

} // namespace gem5

#endif // __BOOTCAMP_SHADOW_UNIT_SHADOW_UNIT_HH__
