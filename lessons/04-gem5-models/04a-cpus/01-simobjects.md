# SimObjects

Let's get specific about gem5 models.

> By the end of this section, you will be able to:
>
> - **Create** a simple SimObject (with a constructor and parameters) from scratch by creating the appropriate Python, C++, and SConscript files.
> - **Build** gem5 using SCons and Kconfig.
> - **Apply** gem5 code conventions such as naming conventions, include guards, and best practices when creating new SimObjects.
> - **Determine** which build-time configuration and compiler configuration are appropriate for a research goal.
> - **Trace** m5’s instantiate() function to follow SimObject creation.

## What's a SimObject?

We've talked about gem5 **simulation models**: C++ classes that make up gem5's backend. So far in the bootcamp, we've used models for processor cores (`O3CPU`), caches (`Cache`), and memory (`ChanneledMemory`) when creating our own standard library components. These models are the backbone of simulation, and in gem5, they are all `SimObject`s. 

The `SimObject` class is the parent C++ class for all gem5 SimObjects. It (and its children, such as `ClockedObject`) facilitates:

- Defining a model (ex: a CPU core),
- Parameterizing a model (ex: fetch width, number of reorder buffers),
- Gathering statistics (ex: number of instructions executed)

Many SimObjects work in concert to simulate an entire system. In this section, we'll create a basic SimObject and see it in simulation.

## Writing SimObjects

### SimObjects in code

Each SimObject is made up of 4 basic files:

- Declaration file (`.py`):
  - This file represents the model at the highest level. It allows for the instantiation of the model and for interfacing with the C++ backend. It defines the sets of parameters for the model.
  - This file determines the name of the model that will be used in Python files.
- Header file (`.hh`):
  - Like a traditional header file, this file declares the SimObject and all its functions, to be instantiated in the source file.
- Source file (`.cc`):
  - This file implements the SimObject's functionality!
- `Params` header file (`.hh`):
  - This file declares a C++ struct that stores all parameters for the SimObject.
  - This file is **auto-generated** based on the other three files, meaning you don't have to write it yourself!

> Overall, this means you need to write 3 files to create a new SimObject!

![An graphic of the four files representing a SimObject: SimObject.py, sim_object.hh, sim_object.cc, and SimObjectParams.hh. SimObjectParams.hh is greyed out slightly, indicating it is auto-generated.](img/gem5-sim-object.png)

### Peek at a CPU SimObject

Let's look at an example of an existing CPU SimObject and all its files. `AtomicSimpleCPU` is a model for a simple core with atomic memory accesses, and it has 4 files.

> Don't worry too much about understanding every line of code in this example just yet. This is a sneak peek!

#### Declaration file: `gem5/src/cpu/simple/BaseAtomicSimpleCPU.py`

Looking into this file, we see it looks like this:

```python
class BaseAtomicSimpleCPU(BaseSimpleCPU):
    type = "BaseAtomicSimpleCPU"
    cxx_header = "cpu/simple/atomic.hh"
    cxx_class = "gem5::AtomicSimpleCPU"

    ...
```
This format is followed by other declaration files; they indicate the type of the SimObject (the name of its Python class that can be used in Python simulation files, also often the name of the .py file), the locations of the corresponding header and source file, and any parameters (omitted here).

> You might be wondering why we aren't looking at `AtomicSimpleCPU.py` instead. CPU models in gem5 work a bit differently due to them being ISA-specific.
> 
> The `AtomicSimpleCPU.py` file (`gem5/src/cpu/simple/AtomicSimpleCPU.py`) looks at the ISA being used and imports the appropriate version of `AtomicSimpleCPU`, all of which inherit from `BaseAtomicSimpleCPU`. The same pattern holds for all other CPUs in gem5.

#### Header file: `gem5/src/cpu/simple/atomic.hh`

Looking into this file, we see:

```C++
namespace gem5
{

class AtomicSimpleCPU : public BaseSimpleCPU
{
  public:

    AtomicSimpleCPU(const BaseAtomicSimpleCPUParams &params);
    virtual ~AtomicSimpleCPU();

    void init() override;

    ...
```
Header files declare the class name and include all method signatures for the C++ class, including the constructor (which you see here). The constructor always takes the corresponding `Params` struct (which we'll see in a moment!). We can see this class also has an `init()` function.

#### Source file: `gem5/src/cpu/simple/atomic.cc`

```C++
namespace gem5
{

void
AtomicSimpleCPU::init()
{
    BaseSimpleCPU::init();

    int cid = threadContexts[0]->contextId();
    ifetch_req->setContext(cid);
    data_read_req->setContext(cid);
    data_write_req->setContext(cid);
    data_amo_req->setContext(cid);
}

AtomicSimpleCPU::AtomicSimpleCPU(const BaseAtomicSimpleCPUParams &p)
    : BaseSimpleCPU(p),
      tickEvent([this]{ tick(); }, "AtomicSimpleCPU tick",
                false, Event::CPU_Tick_Pri),
      width(p.width), locked(false),

      ...
```

Source files contain the SimObject's functionality. We can see the implementation of the `init()` function we saw declared in the header file, followed by the beginning of the constructor (remember C++ initialization lists?).

#### `Params` header file: `gem5/build/ALL/params/BaseAtomicSimpleCPU.hh`

If we look in this file, we can see:

```C++
...

namespace gem5
{
struct BaseAtomicSimpleCPUParams
    : public BaseSimpleCPUParams
{
    gem5::AtomicSimpleCPU * create() const;
    bool simulate_data_stalls;
    bool simulate_inst_stalls;
    int width;
};

...
```

This is the auto-genrated `Params` struct! You'll notice its name matches the argument of `BaseAtomicSimpleCPU`'s constructor (declared in the header file and implemented in the source file). Looks like `BaseAtomicSimpleCPU` takes three parameters.

> Since the `Params` file is auto-generated, it lives in the `build` folder, and it will only be auto-generated as part of the build process (more on that in a second). Its name matches the type declared in the .py declaration file  with `Params` appended to the end.


### Let's make a SimObject!

<link href="../../style.css" rel="stylesheet"></link>