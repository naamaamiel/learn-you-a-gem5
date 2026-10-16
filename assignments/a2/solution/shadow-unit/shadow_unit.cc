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

ShadowUnit::ShadowUnit(const ShadowUnitParams &params)
    : BaseShadowUnit(params),
      numLanes(params.num_lanes),
      compareLatency(params.compare_latency),
      faultPeriod(params.fault_period),
      rng(Random::genRandom(params.fault_seed)),
      shadowDoneEvent([this] { processShadowDone(); },
                      name() + ".shadowDoneEvent"),
      compareDoneEvent([this] { processCompareDone(); },
                       name() + ".compareDoneEvent"),
      stats(this)
{
    fatal_if(numLanes == 0, "%s: num_lanes must be at least 1.", name());
}

void
ShadowUnit::scheduleNext(Event &event, Tick when)
{
    if (!event.scheduled()) {
        schedule(event, when);
    } else if (when < event.when()) {
        reschedule(event, when);
    }
}

bool
ShadowUnit::requestCheck(ShadowCheck *check)
{
    if (lanes.size() >= numLanes) {
        DPRINTF(ShadowUnit, "[sn:%llu] rejected: all %u lanes busy\n",
                check->seqNum, numLanes);
        ++stats.rejections;
        return false;
    }

    Tick done = clockEdge(check->latency);
    lanes.emplace(done, check);
    scheduleNext(shadowDoneEvent, done);
    ++stats.checks;
    stats.laneCycles += check->latency;

    DPRINTF(ShadowUnit, "[sn:%llu] S starts, done in %llu cycles "
            "(%u of %u lanes busy)\n", check->seqNum,
            uint64_t(check->latency), lanes.size(), numLanes);
    return true;
}

void
ShadowUnit::processShadowDone()
{
    // Every S that finishes now leaves its lane and enters the comparator.
    while (!lanes.empty() && lanes.begin()->first <= curTick()) {
        ShadowCheck *check = lanes.begin()->second;
        lanes.erase(lanes.begin());

        check->shadow = check->golden;
        if (faultPeriod > 0 && rng->random<unsigned>(1, faultPeriod) == 1) {
            check->shadow ^= RegVal(1) << 63;
            ++stats.faultsInjected;
        }

        DPRINTF(ShadowUnit, "[sn:%llu] S done, comparing\n", check->seqNum);
        comparator.emplace_back(clockEdge(compareLatency), check);
    }

    if (!comparator.empty()) {
        scheduleNext(compareDoneEvent, comparator.front().first);
    }
    if (!lanes.empty()) {
        scheduleNext(shadowDoneEvent, lanes.begin()->first);
    }
}

void
ShadowUnit::processCompareDone()
{
    while (!comparator.empty() && comparator.front().first <= curTick()) {
        ShadowCheck *check = comparator.front().second;
        comparator.pop_front();

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

    if (!comparator.empty()) {
        scheduleNext(compareDoneEvent, comparator.front().first);
    }
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
