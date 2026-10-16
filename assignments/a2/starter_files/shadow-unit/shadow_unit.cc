/*
 * Assignment #2: Build-a-Shadow-Unit
 *
 * Name:
 */

#include "bootcamp/shadow-unit/shadow_unit.hh"

#include "base/logging.hh"
#include "base/trace.hh"
#include "debug/ShadowUnit.hh"

namespace gem5
{

ShadowUnit::ShadowUnit(const ShadowUnitParams &params)
    : BaseShadowUnit(params),
      // TODO (Part 1): initialize numLanes, compareLatency, faultPeriod,
      // rng (Random::genRandom(seed)), shadowDoneEvent and
      // compareDoneEvent, in the order the header declares them.
      stats(this)
{
}

void
ShadowUnit::scheduleNext(Event &event, Tick when)
{
    // TODO (Part 1): if event isn't scheduled, schedule it at when. If it
    // is scheduled later than when, move it earlier.
}

bool
ShadowUnit::requestCheck(ShadowCheck *check)
{
    // TODO (Part 2): if every lane is busy, reject the check.

    // TODO (Part 1): S takes a lane and finishes check->latency cycles
    // from now. Add it to lanes, make sure shadowDoneEvent fires in time,
    // and update stats.checks and stats.laneCycles.

    DPRINTF(ShadowUnit, "[sn:%llu] S starts (%u of %u lanes busy)\n",
            check->seqNum, lanes.size(), numLanes);
    return true;
}

void
ShadowUnit::processShadowDone()
{
    // TODO (Part 1): take every S that finishes now out of lanes.
    //   Part 1: S always agrees with P: set match and send the verdict.
    //   Part 2: instead, set S's result and hand the check to the
    //           comparator.
    //   Part 3: inject faults into S's result.

    // TODO (Part 1): if S executions are still in flight, make sure
    // shadowDoneEvent fires when the next one finishes.
}

void
ShadowUnit::processCompareDone()
{
    // TODO (Part 2): send the verdict of every check whose comparison
    // finishes now. Then make sure compareDoneEvent fires when the next
    // one finishes, if there is one.
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
