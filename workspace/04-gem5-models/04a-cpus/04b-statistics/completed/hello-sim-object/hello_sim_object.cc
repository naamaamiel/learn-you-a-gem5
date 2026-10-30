#include "bootcamp/hello-sim-object/hello_sim_object.hh"

#include <iostream>

#include "sim/stats.hh"

namespace gem5
{

HelloSimObject::HelloSimObject(const HelloSimObjectParams& params):
    SimObject(params),
    nextHelloEvent([this](){ processHello(); },
                   name() + "HelloEvent"),
    remainingHellos(params.num_hellos),
    stats(this)
{
    for (int i = 0; i < params.num_hellos; i++) {
        std::cout << "i: " << i << ", Hello from HelloSimObject's constructor!" << std::endl;
    }
}

void
HelloSimObject::startup()
{
    panic_if(curTick() != 0, "startup called at a tick other than 0");
    panic_if(nextHelloEvent.scheduled(), "nextHelloEvent is scheduled before HelloSimObject::startup is called!");

    schedule(nextHelloEvent, 500);
}

void
HelloSimObject::processHello()
{
    // Print a hello message that includes the current tick
    std::cout << "tick: " << curTick() << ", Hello from HelloSimObject::processHello!" << std::endl;

    // Decrement hellos remaining, and count this hello
    remainingHellos--;
    stats.hellosSaid++;

    // Schedule the next event if we still have hellos to print
    if (remainingHellos > 0) {
        schedule(nextHelloEvent, curTick() + 500);
    }
}

HelloSimObject::HelloSimObjectStats::HelloSimObjectStats(
    HelloSimObject *parent)
    : statistics::Group(parent),
      ADD_STAT(hellosSaid, statistics::units::Count::get(),
               "Number of hellos said"),
      ADD_STAT(hellosLeft, statistics::units::Count::get(),
               "Number of hellos left to say"),
      ADD_STAT(helloRate, statistics::units::Rate<
                   statistics::units::Count, statistics::units::Second>::get(),
               "Hellos said per simulated second",
               hellosSaid / simSeconds)
{
    hellosLeft.functor([parent]() { return parent->remainingHellos; });
}

} // namespace gem5
