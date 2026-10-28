# gem5 Workshop Assignment #2

You now have all of the skills you need to write SimObjects in gem5! In this assignment, you'll be expanding on an example from the course to implement new functionality.

> In this assignment, you will:
>
> - **Develop** a SimObject that utilizes ports and gem5 events,
> - **Create** a new debugging flag and add it to a SimObject.


This assignment builds on Unit IV. You may want to refer to it as you work.

| Lesson | Relevant Topics |
|---|---|
| [SimObjects](../../lessons/04-gem5-models/04a-cpus/01-sim-objects.md) | Navigating SimObject files and building gem5.|
| [Event-driven simulation](../../lessons/04-gem5-models/04a-cpus/02-event-driven-sim.md) | Explaining event-driven simulation and using gem5 `Event` and `EventFunctionWrapper`. |
| [Ports](../../lessons/04-gem5-models/04a-cpus/03-ports.md) | Using the gem5 ports and packet interface; using events to schedule port-related actions;  the `PacketInspector` SimObject implementation.|
| [Debugging](../../lessons/04-gem5-models/04a-cpus/04-debugging.md) | Writing and enabling a debugging flag. |

## Instructions

Our goal for this assignment is to implement a simple version of **memory encryption**. In an encrypted memory system, data stored in memory is encrypted using a symmetric encryption scheme like [AES](https://en.wikipedia.org/wiki/Advanced_Encryption_Standard); it is decrypted only as it leaves the memory system (i.e., when the CPU makes a read request) and encrypted when it enters (i.e., when the CPU makes a write request).

> For an example of this in practice, you can check out [AMD SME (Secure Memory Encryption)](https://docs.amd.com/api/khub/documents/ZcsCCmeL80dbtuf_VlGpvw/content). We won't be implementing most of the discussed features here.

![A diagram depicting memory encryption. When a processor makes a write request, its data is encrypted before being stored into the encrypted memory system. When the memory system sends a data read response to the processor, the encrypted data is decrypted before arriving at the processor.](img/memory_encryption.png)

In the [Ports lesson](../../lessons/04-gem5-models/04a-cpus/03-ports.md), we implemented `PacketInspector`, a unit that (at the moment) intercepts all packets heading into and out of memory and "inspects" them; really, it simply queues incoming and outgoing packets into separate buffers with an imposed clock cycle latency. In this assignment, you'll be using `PacketInspector` as the basis for a new SimObject named `PacketEncryptor` that encrypts the data of incoming memory writes and decrypts the data of outgoing memory reads.

![A diagram similar to the one in the ports lesson depicting a simplified view of a processor interacting with memory using packets sent from the processor's RequestPort to memory's ResponsePort. Between the two, the PacketEncryptor unit intercepts all packets in both directions before sending them along.](img/packet_encryptor.png)

Similar to how we used the new `InspectedMemory` component as a wrapper for a memory system with a `PacketInspector`, we'll write a new `EncryptedMemory` component as a wrapper for a memory system with a `PacketEncryptor`.

![A diagram similar to the one in the ports lesson depicting a simplified view of the EncryptedMemory unit. The processor communicates through its RequestPort with an EncryptedMemory unit, which contains within it both memory and a PacketEncryptor unit intercepting and encrypting packets.](img/encrypted_memory.png)

We'll tackle writing this unit in multiple steps: we'll add a debugging flag to `PacketEncryptor`, implement encryption functionality, then improve the throughput of our system.

## Part 0: Exploring the provided code

The provided code for this assignment is a renamed version of `PacketInspector` from the ports lesson. It has all of the same parameters, structure, and functionality, with only the following differences:

- The `PacketInspector` SimObject is renamed to `PacketEncryptor`, which affects the class name and all associated file names,
- `inspectionBuffer` has been renamed to `encryptionBuffer`, which also renames the `inspectionBufferEntries` parameter to `encryptionBufferEntries`.
- `responseBuffer` has been renamed to `decryptionBuffer`, which also renames the `responseBufferEntries` parameter to `decryptionBufferEntries`

> The reasons for this renaming will become clear in Part 2!

You should read through the implementation of `PacketEncryptor` to remind yourself how the class is structured; you can refer to the [ports lesson](../../lessons/04-gem5-models/04a-cpus/03-ports.md) for a thorough walkthrough of the request path.

The provided code also includes `EncryptedMemory`, which closely follows the implementation of `InspectedMemory`, and `packet_encryptor_config.py`, a configuration script that makes use of `EncryptedMemory` with a linear traffic generator and no cache.

> Don't worry too much about the implementation of the traffic generator here; it's just a more straightforward way to introduce memory traffic without making use of a workload.

## Part 1: Adding a debugging flag

Since you'll be messing with a SimObject implementation, you may find it useful to print out useful debugging messages as you go. We'll be doing this by writing a **debug flag** to `PacketEncryptor` and adding debug printing statements to its implementation.

Adding `DebugFlags` was covered in the [debugging lesson](../../lessons/04-gem5-models/04a-cpus/04-debugging.md); you may want to use the process of defining and enabling a flag for `LocalBP` when writing your debug flag for `PacketEncryptor`. Your flag should:

- Be named `Encryptor`,
- Be defined in `PacketEncryptor`'s SConscript,
- Enable debugging print statements in the following locations:
  - When `CPUSidePort` receives a timing request,
  - When `MemSidePort` receives a timing response,
  - When `CPUSidePort` or `MemSidePort` send a packet,
  - When `CPUSidePort` or `MemSidePort` fail to send a packet,
  - When `MemSidePort` receives a retry signal,
  - Any other location you feel is appropriate.

> Some tips for writing effective debugging print statements:
> - The `Packet` class defines a `print()` method (`p.print()` for a `Packet` `p`) that returns a string containing helpful information about the packet it is called on.
> - The `__func__` identifier in C will print out the name of the current function.
> 
> We recommend making use of both of these for your `Encryptor` print statements.

Once you've written your flag, you should enable it *in `packet_encryptor_config.py`*. When running a simulation using this configuration script, you should redirect simulation output into files using the `-re` flag.

For this part, you should submit all files in the `packet-encryptor` directory, `packet_encryptor_config.py`, and the `m5out` directory.

> You may find it useful to continue using the `Encryptor` flag as you continue implementing `PacketEncryptor`. We highly encourage you to do this!

## Part 2: Adding encryption

In this part, you'll be modifying `PacketEncryptor` to actually encrypt packets. You'll do this by simulating the behavior of an *encryption/decryption unit*. Instead of packets being dequeued from the `encryptionBuffer` and `decryptionBuffer` directly to their respective output ports, packets from these ports will be dequeued into encryption/decryption units before being put into an output queue (`requestBuffer` and `responseBuffer`) to be sent out.

![A diagram of PacketEncryptor. Incoming request packets from the ResponsePort are enqueued into the encryptionBuffer. One packet as a time is dequeued into the encryption unit, then enqueued into the requestBuffer. Packets from the requestBuffer are dequeued into the RequestPort to be sent out. Incoming response packets from the RequestPort are enqueued into the decryptionBuffer. One packet as a time is dequeued into the decryption unit, then enqueued into the responseBuffer. Packets from the responseBuffer are dequeued into the ResponsePort to be sent out.](img/single_encryption.png)

We won't be creating a separate class to model encryption or decryption; we'll simply assume a flat one-cycle delay for encryption or decryption and implement the behavior within `PacketEncryptor`. Our packet paths will now become:

- **Request path**: `CPUSidePort.recvTimingReq` &rarr; `PacketEncryptor.recvTimingReq` &rarr; ***Encryption*** &rarr; `PacketEncryptor.processNextReqSendEvent` &rarr; `MemSidePort.sendPacket`
- **Response path**: `MemSidePort.recvTimingResp` &rarr; `PacketEncryptor.recvTimingResp` &rarr; ***Decryption*** &rarr; `PacketEncryptor.processNextRespSendEvent` &rarr; `CPUSidePort.sendPacket`

### Step 2A: Queues and parameters

Your first step should be to add the new queues to handle outgoing packets, `requestBuffer` and `responseBuffer`. Just like `encryptionBuffer` and `decryptionBuffer`, these should be `TimedQueue`s with parameterized sizes (`requestBufferEntries` and `responseBufferEntries`). These new parameters should *not* have default values.

After making these changes and rebuilding gem5, remember to alter any place that `PacketInspector` is instantiated (i.e. `EncryptedMemory`) to provide values for these new parameters (use 8 for both).

> Even while these queues are unused, gem5 should build and the configuration script should run with no errors.

### Step 2B: Events

Next, we'll make use of these new queues by altering the behavior of our events. You should alter the path of an incoming request packet such that it is *encrypted* between `PacketEncryptor.recvTimingReq` and `PacketEncryptor.processNextReqSendEvent`. Similarly, you should alter the path of an incoming response packet such that it is *decrypted* between `PacketEncryptor.recvTimingResp` and `PacketEncryptor.processNextRespSendEvent`. Remember that the *retry paths* are similarly affected by this change and should be altered accordingly (which functions are now responsible for scheduling retry events?).

Since encryption and decryption incur latency, you'll want to make new events to capture this new behavior. You should also make sure that you are enqueuing and dequeuing packets from the appropriate queues: incoming packets are enqueued into `encryption`/`decryptionBuffer`, and outgoing packets (that have been through encryption/decryption) are enqueued into `request`/`responseBuffer`. Also pay close attention to which methods are now responsible for calling which `scheduleNext[...]Event` methods, including on the retry path.

> You may find it easier to implement and debug all of a single path (one of the request or response paths, including retries) before implementing the other.

Currently, you don't need to implement any actual encryption or decryption behavior within the processing of these new events; just handle passing packets around to and from the appropriate buffers with the correct latency.

> We highly recommend making heavy use of debugging prints to to double-check your work here!

If you get stuck, below is a list of all methods you should be implementing in this part. You may also use this list to double-check your work.

> <details>
> <summary markdown="span"> <b>Step 2B new methods</b> </summary>
> 
> ```cpp
> bool PacketEncryptor::processNextEncryptionEvent()
> bool PacketEncryptor::processNextDecryptionEvent()
> void PacketEncryptor::scheduleNextEncryptionEvent(Tick when)
> void PacketEncryptor::scheduleNextDecryptionEvent(Tick when)
> void PacketEncryptor::encryptRequest(PacketPtr pkt); // empty for now
> void PacketEncryptor::decryptResponse(PacketPtr pkt); // empty for now
> ```
> </details>
<br>

Additionally, below are the methods that already exist in `PacketEncryptor` that need to change in order to accommodate the new encryption behavior.

> <details>
> <summary markdown="span"> <b>Step 2B modified methods</b> </summary>
> 
> ```cpp
> bool PacketEncryptor::recvTimingReq(packetPtr pkt)
> bool PacketEncryptor::recvTimingResp(packetPtr pkt)
> void PacketEncryptor::scheduleNextReqSendEvent(Tick when)
> void PacketEncryptor::scheduleNextRespSendEvent(Tick when)
> void PacketEncryptor::processNextReqSendEvent()
> void PacketEncryptor::processNextRespSendEvent()
> ```
> </details>

<br>

> You should once again be able to build and run gem5 here. We recommend that you do (with ample debugging print statements) to double-check that packets take the path you expect through the code.

### Step 2C: Encryption and decryption

At this point, `PacketEncryptor` should be doing everything but actually encrypting and decrypting data. Let's change that here.

Recall that our goal is to encrypt the data of all memory writes and decrypt the data of all memory reads. This means we'll need to double-check all incoming packets on the request path and only encrypt those that are write requests; similarly, we'll need to double-check all incoming packets on the response path and decrypt only those that are read responses.

> *All packets will still pass through the encryption/decryption step of our response/request path and incur the corresponding latency!* The logic for whether the internal data of a packet actually needs modifying will occur within this step.

To do this, we'll use helper methods defined in `Packet` that allow us to examine its properties.

> `Packet`'s `print()` method conveniently prints out some of these properties for us, so you may have seen them before if you've been reading the simulation debugging output!

We can use the following methods to sanity-check ourselves, as we should only be encrypting requests and decrypting responses:

```cpp
bool Packet::isRequest()
bool Packet::isResponse()
```

After verifying this, we can use the following methods to check for reads and writes, and to verify the packets have data for us to encrypt:

```cpp
bool Packet::isRead()
bool Packet::isWrite()
bool Packet::hasData()
```

We'll be encrypting/decrypting the raw data stored in the packets, and we can use the following getter and setter to grab and modify it: 

```cpp
template <typename T>
T Packet::getRaw()

template <typename T>
T Packet::setRaw()
```

> You'll notice these are *[templates](https://en.cppreference.com/cpp/language/function_template)*. This is done so that the data in the packets can be interpreted as different types and sizes. For the sake of this assignment, you can assume all reads and writes are exactly 8 bytes (`uint64_t`s), and our traffic generator is already configured so that this is the case.

Since this assignment is not really about encryption, how to "encrypt" the data is up to you; feel free to use whatever encryption scheme you like. The solution code uses the less-than-safe scheme of simply flipping all of the data bits!

You're now done with Part 2! Be sure to grab your source files and `m5out` directory (after running with the `-re` flag) for submission.

## Part 3: Latency and throughput

In this part, you'll modify the encryption process such that its latency is parameterizable. You'll then improve `PacketEncryptor`'s throughput in the face of this additional latency by introducing an *array* of encryptor and decryptor units such that `PacketEncryptor` can encrypt and decrypt multiple packets simultaneously.

![A diagram of the modified PacketEncryptor. Incoming request packets from the ResponsePort are enqueued into the encryptionBuffer. Packets are dequeued into one of the available encryption units; encrypted packets are then enqueued from their unit into the requestBuffer. Packets from the requestBuffer are dequeued into the RequestPort to be sent out. Incoming response packets from the RequestPort are enqueued into the decryptionBuffer. Packets are dequeued into one of the available decryption units, then enqueued into the responseBuffer. Packets from the responseBuffer are dequeued into the ResponsePort to be sent out.](img/multiple_units.png)

Once again, we'll tackle this modification in steps.

### Step 3A: Multiple inspection units

First, we need to modify the structure and parameters of `PacketEncryptor` to accommodate multiple encryption and decryption units. We need to define a few new parameters:

- `window`: the window for how many packets `PacketEncryptor` should attempt to encrypt/decrypt on each cycle. 
- `num_units`: the number of encryption and decryption units a `PacketEncryptor` has.
- `enc_dec_latency`: the latency (in `Cycles`) for encrypting/decrypting a packet.

>  For example, if we have `window` = 2, `num_units` = 3, and `enc_dec_latency` = 4, we will have 3 encryption units and 3 decryption units in our system. Each cycle, we will attempt to encrypt 2 packets and decrypt 2 packets. The process of encrypting/decrypting a packet will incur a 4-cycle latency.
>
> We could choose define these parameters separately for encryption and decryption (e.g., `enc_window` and `dec_window` instead of just `window`), but we don't do this here for the sake of simplicity. Feel free to try this out if you like after completing this assignment!

You should declare and initialize these parameters appropriately in the header/source files as well as in the declaration file. Again, do not give these parameters default values. Don't forget to also update `EncryptedMemory` to expose and set these parameters (**use a window of 2, 3 units, and a latency of 4 cycles**).

While we are not defining a new class for encryption and decryption functionality, we need to keep track of when each of our encryption and decryption units will next become available. For this, we should keep `encryptionUnitAvailableTimes` and `decryptionUnitAvailableTimes`: `vector`s of `Tick`s, where each index of the `vector` corresponds to an individual unit's next available time.

### Step 3B: Encrypting and decrypting multiple packets

After declaring and initializing our new units appropriately, you should make sure to consider the time in which the next available encryption/decryption unit becomes available when scheduling a packet to be encrypted/decrypted.

Additionally, on each encryption and decryption event, `PacketInspector` should now attempt to encrypt/decrypt `window` packets, not just one. Remember to avoid using busy encryption/decryption units, double-check that you have packets to inspect (there may be fewer than `window` packets in the encryption/decryption buffer!), and ensure that the corresponding output queue (`responseBuffer` or `requestBuffer`) has room for the encrypted/decrypted packets. When a unit encrypts/decrypts a packet, make sure to update its next available tick based on the encryption/decryption latency.

As in the previous part, below is a list of methods that you should modify in this part.

> <details>
> <summary markdown="span"> <b>Step 3B modified methods</b> </summary>
> 
> ```cpp
> void PacketEncryptor::scheduleNextEncryptionEvent(Tick when)
> void PacketEncryptor::scheduleNextDecryptionEvent(Tick when)
> void PacketEncryptor::processNextEncryptionEvent()
> void PacketEncryptor::processNextDecryptionEvent()
> ```
> </details>

<br>

> At this point, your code should build and the configuration script should run with no errors!

You're now done with Part 3! Make sure to grab your source and simulation output files for submission.

> Now that you have a completed component, feel free to play around with modifying these new latency, window, and encryption/decryption unit parameters to see their effect on the system. Some interesting stats to look at:
> ```txt
> board.processor.cores.generator.numPackets
> board.processor.cores.generator.numRetries
> board.processor.cores.generator.totalReads          
> board.processor.cores.generator.totalWrites
> board.processor.cores.generator.totalReadLatency
> board.processor.cores.generator.totalWriteLatency
> ```
>
> Remember that our simulation is bounded to run for 1,000,000 ticks.

## Submission

This assignment is in three parts, and you should submit your code for each part separately.

For Part 1, you should submit:
- All files in the `packet-encryptor` directory, 
- `packet_encryptor_config.py` with the `Inspector` flag enabled,
- The `m5out` directory that is created as a result of running a simulation configured by `packet_encryptor_config.py` using the `-re` flag.

For Part 2, you should submit:
- All files in the `packet-encryptor` directory,
- The `m5out` directory that is created as a result of running a simulation configured by `packet_encryptor_config.py` using the `-re` flag.

For Part 3, you should submit:
- All files in the `packet-encryptor` directory,
- The `m5out` directory that is created as a result of running a simulation configured by `packet_encryptor_config.py` using the `-re` flag.

> For all parts, please **do NOT remove** any additional debugging prints you may have included as part of your implementation process. These help your code's understandability!
