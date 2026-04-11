#ifndef __BOOTCAMP_HELLO_SIM_OBJECT_HELLO_SIM_OBJECT_HH__
#define __BOOTCAMP_HELLO_SIM_OBJECT_HELLO_SIM_OBJECT_HH__

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
    class HelloEvent : public Event
    {
        private:
            HelloSimObject* owner;
        public:
            HelloEvent(HelloSimObject* owner): 
            Event(),
            owner(owner)
            {}

            virtual void process() override
            {
                owner->processHello();
            }
    };
    HelloEvent nextHelloEvent;
    int remainingHellos;
};

} // namespace gem5

#endif // __BOOTCAMP_HELLO_SIM_OBJECT_HELLO_SIM_OBJECT_HH__