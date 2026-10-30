#ifndef __BOOTCAMP_HELLO_SIM_OBJECT_HELLO_SIM_OBJECT_HH__
#define __BOOTCAMP_HELLO_SIM_OBJECT_HELLO_SIM_OBJECT_HH__

#include "base/statistics.hh"
#include "params/HelloSimObject.hh"
#include "sim/eventq.hh"
#include "sim/sim_object.hh"

namespace gem5
{

class HelloSimObject: public SimObject
{
  public:
    HelloSimObject(const HelloSimObjectParams& params);
    void processHello();
    virtual void startup() override;

  private:
    EventFunctionWrapper nextHelloEvent;
    int remainingHellos;

    struct HelloSimObjectStats : public statistics::Group
    {
        HelloSimObjectStats(HelloSimObject *parent);

        statistics::Scalar hellosSaid;
        statistics::Value hellosLeft;
        statistics::Formula helloRate;
    } stats;
};

} // namespace gem5

#endif // __BOOTCAMP_HELLO_SIM_OBJECT_HELLO_SIM_OBJECT_HH__
