#ifndef __BOOTCAMP_SHADOW_UNIT_SHADOW_UNIT_HH__
#define __BOOTCAMP_SHADOW_UNIT_SHADOW_UNIT_HH__

#include <deque>
#include <map>
#include <utility>

#include "base/random.hh"
#include "base/statistics.hh"
#include "cpu/base_shadow_unit.hh"
#include "params/ShadowUnit.hh"
#include "sim/eventq.hh"

namespace gem5
{

class ShadowUnit : public BaseShadowUnit
{
  private:
    const unsigned numLanes;
    const Cycles compareLatency;
    const unsigned faultPeriod;

    /** Random numbers for the shadow fault injector (Part 3). */
    Random::RandomPtr rng;

    /** Shadow executions in flight, keyed by the tick each one finishes. */
    std::multimap<Tick, ShadowCheck *> lanes;
    EventFunctionWrapper shadowDoneEvent;

    /** Checks in the comparator, oldest first, with the tick each is done. */
    std::deque<std::pair<Tick, ShadowCheck *>> comparator;
    EventFunctionWrapper compareDoneEvent;

    /** Make sure that event happens no later than when. */
    void scheduleNext(Event &event, Tick when);

    /** Callback of shadowDoneEvent: S finished on one or more lanes. */
    void processShadowDone();

    /** Callback of compareDoneEvent: one or more comparisons finished. */
    void processCompareDone();

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
