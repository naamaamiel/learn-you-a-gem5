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

ShadowUnit::ShadowCompletion::ShadowCompletion(ShadowCheck *_check,
    int _lane, ShadowUnit *_unit)
    : Event(Default_Pri, AutoDelete),
      check(_check), lane(_lane), unit(_unit)
{
}

void
ShadowUnit::ShadowCompletion::process()
{
    // TODO (Part 1): tell the unit that S finished on its lane, the way
    // FUCompletion::process() does in src/cpu/o3/inst_queue.cc.
}

const char *
ShadowUnit::ShadowCompletion::description() const
{
    return "Shadow execution completion";
}

ShadowUnit::ShadowUnit(const ShadowUnitParams &params)
    : BaseShadowUnit(params),
      // TODO (Part 1): initialize numLanes, compareLatency, faultPeriod,
      // rng (Random::genRandom(seed)), and laneBusy (one entry per lane,
      // all free), in the order the header declares them.
      stats(this)
{
}

int
ShadowUnit::getLane()
{
    // TODO (Part 1): like FUPool::getUnit() in src/cpu/o3/fu_pool.cc, find
    // a lane that isn't busy, mark it busy, and return its index.
    return NoFreeLane;
}

bool
ShadowUnit::requestCheck(ShadowCheck *check)
{
    // TODO (Part 1): take a lane with getLane(). Then schedule a new
    // ShadowCompletion for the cycle S finishes, check->latency cycles from
    // now, the way the O3 instruction queue schedules an FUCompletion in
    // InstructionQueue::scheduleReadyInsts(). Update stats.checks and
    // stats.laneCycles.
    //   Part 1: run with plenty of lanes, and panic if none is free.
    //   Part 2: if no lane is free, reject the check instead.

    DPRINTF(ShadowUnit, "[sn:%llu] S starts\n", check->seqNum);
    return true;
}

void
ShadowUnit::processShadowDone(ShadowCheck *check, int lane)
{
    // TODO (Part 1): S finished, so free its lane, the way an unpipelined
    // FU is freed when its FUCompletion runs.
    //   Part 1: S always agrees with P: set match and send the verdict.
    //   Part 2: instead, set S's result and start the comparison: schedule
    //           a new event for C cycles from now.
    //   Part 3: inject faults into S's result.
}

void
ShadowUnit::processCompareDone(ShadowCheck *check)
{
    // TODO (Part 2): compare S's result with P's, update the stats, and
    // send the verdict.
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
