/*
 * Assignment #2: Build-a-Shadow-Unit
 *
 * Name: Solution
 */

#include "bootcamp/shadow-unit/shadow_unit.hh"

#include "base/logging.hh"
#include "base/trace.hh"
#include "debug/ShadowUnit.hh"

namespace gem5
{

ShadowUnit::ShadowCompletion::ShadowCompletion(ShadowCheck *_check,
    int _lane, ShadowUnit *_unit)
    : Event(Default_Pri, AutoDelete),
      check(_check), lane(_lane), unit(_unit)
{
}

void
ShadowUnit::ShadowCompletion::process()
{
    unit->processShadowDone(check, lane);
}

const char *
ShadowUnit::ShadowCompletion::description() const
{
    return "Shadow execution completion";
}

ShadowUnit::ShadowUnit(const ShadowUnitParams &params)
    : BaseShadowUnit(params),
      numLanes(params.num_lanes),
      compareLatency(params.compare_latency),
      faultPeriod(params.fault_period),
      rng(Random::genRandom(params.fault_seed)),
      laneBusy(params.num_lanes, false),
      stats(this)
{
    fatal_if(numLanes == 0, "%s: num_lanes must be at least 1.", name());
}

int
ShadowUnit::getLane()
{
    for (unsigned lane = 0; lane < numLanes; ++lane) {
        if (!laneBusy[lane]) {
            laneBusy[lane] = true;
            return lane;
        }
    }
    return NoFreeLane;
}

bool
ShadowUnit::requestCheck(ShadowCheck *check)
{
    int lane = getLane();
    if (lane == NoFreeLane) {
        DPRINTF(ShadowUnit, "[sn:%llu] rejected: all %u lanes busy\n",
                check->seqNum, numLanes);
        ++stats.rejections;
        return false;
    }

    // S holds its lane for L cycles, like an unpipelined FU.
    schedule(new ShadowCompletion(check, lane, this),
             clockEdge(check->latency));
    ++stats.checks;
    stats.laneCycles += check->latency;

    DPRINTF(ShadowUnit, "[sn:%llu] S starts on lane %d, done in %llu "
            "cycles\n", check->seqNum, lane, uint64_t(check->latency));
    return true;
}

void
ShadowUnit::processShadowDone(ShadowCheck *check, int lane)
{
    // S is done, so its lane is free.
    laneBusy[lane] = false;

    check->shadow = check->golden;
    if (faultPeriod > 0 && rng->random<unsigned>(1, faultPeriod) == 1) {
        check->shadow ^= RegVal(1) << 63;
        ++stats.faultsInjected;
    }

    DPRINTF(ShadowUnit, "[sn:%llu] S done on lane %d, comparing\n",
            check->seqNum, lane);

    // The comparator is pipelined: each check gets its own event.
    schedule(new EventFunctionWrapper([this, check] {
                 processCompareDone(check);
             }, name() + ".compareDone", true),
             clockEdge(compareLatency));
}

void
ShadowUnit::processCompareDone(ShadowCheck *check)
{
    check->match = (check->shadow == check->primary);
    if (check->match) {
        ++stats.passes;
    } else {
        ++stats.mismatches;
    }

    DPRINTF(ShadowUnit, "[sn:%llu] verdict: %s\n", check->seqNum,
            check->match ? "match" : "MISMATCH");
    sendVerdict(check);
}

ShadowUnit::ShadowUnitStats::ShadowUnitStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(checks, statistics::units::Count::get(),
               "Checks accepted"),
      ADD_STAT(laneCycles, statistics::units::Cycle::get(),
               "Lane cycles used by accepted checks"),
      ADD_STAT(rejections, statistics::units::Count::get(),
               "Times a check was turned away because every lane was busy"),
      ADD_STAT(passes, statistics::units::Count::get(),
               "Checks where S's result matched P's"),
      ADD_STAT(mismatches, statistics::units::Count::get(),
               "Checks where S's result did not match P's"),
      ADD_STAT(faultsInjected, statistics::units::Count::get(),
               "Faults injected into S's results")
{
}

} // namespace gem5
