#include "bootcamp/hello-sim-object/hello_sim_object.hh"

#include <iostream>

namespace gem5
{

HelloSimObject::HelloSimObject(const HelloSimObjectParams& params):
    SimObject(params), nextHelloEvent(this), remainingHellos(params.num_hellos)
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

    // Decrement hellos remaining
    remainingHellos--;

    // Schedule the next event if we still have hellos to print
    if (remainingHellos > 0) {
        schedule(nextHelloEvent, curTick() + 500);
    }
}

} // namespace gem5