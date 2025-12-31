# Knowledge checklist

This is a comprehensive list of knowledge assumed by the learning gem5 bootcamp, arranged according to topic. You are encouraged to use this document as a checklist for topics you need to cover before completing the bootcamp.

## Computer Organization

### Measurement Terminology

gem5 allows for collection of statistics which require understanding of common measurement terms. Students are expected to be able to:

- [ ] Use IEC and SI prefixes (for example, KiB for kibi-bytes and KB for kilobytes, GHz for gigahertz).
- [ ] Describe what latency and bandwidth are.

### Cache Organization

Caches are one of the key components that can be simulated in gem5. Cache parameters are configured during some demonstrations. Students are expected to be able to:

- [ ] Define cache size, block size, and cache associativity,
- [ ] Describe common cache statistics such as miss rate,
- [ ] Describe the management bits stored in a cache,
- [ ] Describe cache write policies (write back, write through, write allocate).

### Virtual Memory Basics

gem5 can simulate the operating system, including virtual memory translations. Students are expected to be able to:

- [ ] Define the terms page table and TLB (Translation Lookaside Buffer),
- [ ] Explain what a page table walk is.

### Multiprocessing and Multithreading Basics

gem5 can simulate multiprocessing/multithreading, and a discussion of multithreading and multiprocessing in order to speed up gem5 simulations is included in the bootcamp. Students are expected to be able to:

- [ ] Explain the difference between multithreading and multiprocessing,
- [ ] Define a context switch.

## Computer Architecture I

### Cache Hierarchy

gem5 can simulate a variety of cache hierarchies, and different hierarchies are used in code examples throughout the bootcamp. Students are expected to be able to:

- [ ] Define L1, L2, and L3 caches,
- [ ] Explain what an I-cache, D-cache, and a unified cache are,
- [ ] Explain the difference between a private cache and a shared cache.

### Processors/CPUs

CPUs (Central Processing Units AKA processors) and cores are a key simulation component in gem5. Processors are configured and simulated in many code demonstrations. Students are expected to be able to:

- [ ] Explain the difference between a core and a CPU,
- [ ] Describe a CPU in terms of its clock speed,
- [ ] Explain the difference between a single-cycle and a pipelined CPU,
- [ ] Explain how a pipelined CPU works,
- [ ] Define out-of-order execution and related terminology like ROBs (re-order buffers) and LSQs (load-store queues),
- [ ] Explain common CPU metrics such as IPC (Instructions Per Cycle).

### ISAs

gem5 supports multiple ISAs (Instruction Set Architectures) and different ISAs are used across code demonstrations. Students are expected to be able to:

- [ ] List common ISAs (x86, ARM, RISC-V, MIPS, SPARC),
- [ ] Describe at a high level how an instruction is decoded by reading different bit fields of the instruction (ex: the opcode).

## Computer Architecture II

### Memory

Memory is a key simulation component in gem5. Memory is described and configured in many code demonstrations. Students are expected to be able to:

- [ ] Explain what SRAM and DRAM are,
- [ ] Describe how memory is configured (channel/rank/bank/row/column bits),
- [ ] List common memory devices ((LP)DDR3/4/5),
- [ ] Name media-specific operations for memory (activation, pre-charge, refresh, low-power modes, etc.),
- [ ] Name scheduling algorithms for memory read and write requests.

### Cache Coherence

gem5 includes support for configuring cache coherence protocols. Students are expected to be able to:

- [ ] Explain the Single-Writer Multiple-Reader (SWMR) invariant,
- [ ] Explain how cache coherence protocols such as MSI, MESI, and MOESI address the issue of cache coherence,
- [ ] Explain what directories are in the context of cache coherence,
- [ ] Define false sharing,
- [ ] Explain how the CHI (Coherent Hub Interface) protocol works.

### Advanced Cache Terminology

Some caching parameters in gem5 are not covered in early computer architecture classes. Students are expected to be able to:

- [ ] Explain what banked caches are,
- [ ] Explain what cache clusivity is,
- [ ] Describe what a miss status handler register (MSHR) does,
- [ ] Explain what prefetching is.

### Interconnects and Networks

gem5 allows for creation of custom on-chip network topologies. Students are expected to be able to:

- [ ] Define and contrast different types of topologies (buses, crossbars, rings, mesh, torus, etc.),
- [ ] Explain what internal and external links are,
- [ ] Explain what routers are and name common routing algorithms,
- [ ] Explain what virtual channels and networks are,
- [ ] Explain what flits and flow control are.

## Programming Experience

### Python Programming

The interface to gem5 is Python scripts. Students will be writing Python configuration scripts in order to run gem5 simulations. Students are expected to be able to:

- [ ] Explain what a Python interpreter is,
- [ ] Use import statements,
- [ ] Code with variables,
- [ ] Instantiate objects and call object member functions,
- [ ] Call functions.

If students choose not to attend the Python background session during the first day of the bootcamp, students are additionally expected to be familiar with:

- [ ] Print statements,
- [ ] Primitives (integers, floats, strings, booleans),
- [ ] Collections (lists, sets, and dictionaries),
- [ ] List comprehension (including nested list comprehension),
- [ ] Control flow (if-statements, for-loops, while-loops),
- [ ] Functions (defining and calling, parameters, return values, typing hints),
- [ ] Generators,
- [ ] Object-Oriented Design (OOD)
      - [ ] Classes and objects,
      - [ ] Member variables and functions,
      - [ ] Constructors and construction/instantiation,
      - [ ] Inheritance (base class, derived class) and overriding,
      - [ ] Abstract classes and methods,
      - [ ] Encapsulation.

### The Command Line

gem5 and related utilities are run from the command line. Students are expected to be able to:

- [ ] Run command-line utilities,
- [ ] Use common bash commands such as grep, cd, touch, cp, etc.,
- [ ] Set environment variables.

### Makefiles

Pre-made makefiles are used for demonstrations throughout the bootcamp. Students are expected to be able to:

- [ ] Read makefiles and describe how they are used for compilation,
- [ ] Modify makefiles to change compilation options.

### C++ Programming

The backend of gem5 is written in C++. To develop new gem5 models, C++ programming proficiency is required. Students are expected to be able to:

- [ ] Write header (.hh) files,
- [ ] Use include guards,
- [ ] Use include statements,
- [ ] Explain and use namespaces,
- [ ] Use macros and static inline functions,
- [ ] Use intermediate programming constructs (primitives, functions, control flow),
- [ ] Describe what structs are,
- [ ] Use the const keyword,
- [ ] Use standard library data structures (ex: vectors and queues),
- [ ] Use OOD in C++
      - [ ] Write classes and constructors,
      - [ ] Use initialization lists,
      - [ ] Code with inheritance,
      - [ ] Inherit from abstract classes and override virtual functions.
- [ ] Print to the console (cout and cerr),
- [ ] Program with pointers and references,
- [ ] Use assert and static\_assert statements.

### GDB (GNU Debugger)

GDB is used to examine a program while it runs. It is used during a bootcamp session to trace the execution of gem5. Students are expected to be able to:

- [ ] Run GDB on an executable,
- [ ] Use GDB commands,
- [ ] Explain what a breakpoint is.

## Software

### Git/GitHub

gem5 is distributed as source code and acquired by cloning a git repository, and the bootcamp uses GitHub codespaces. Students are expected to be able to:

- [ ] Set up git on their computers,
- [ ] Clone a repository (repo) using git,
- [ ] Define the concept of a branch within git,
- [ ] Define the concept of a tag within git,
- [ ] Create a GitHub account.

### SCons

SCons is a tool used to build gem5. Students are expected to be able to:

- [ ] Use SCons using the command line.

### Packer

Packer is used to automate disk image creation during one demonstration. Students are expected to be able to:

- [ ] State what Packer is used for.

### QEMU

QEMU is referenced across multiple sessions and used to automate disk image creation during one demonstration. Students are expected to be able to:

- [ ] Explain what QEMU is used for.
- [ ] Use QEMU commands.

### Ubuntu

Ubuntu is a Linux distribution used as the operating system across several demonstrations. Students are expected to be able to:

- [ ] Explain what Ubuntu is.
- [ ] Recognize what Ubuntu autoinstall is.

### Visual Studio Code (VSCode)

Resources refer to Visual Studio Code as the default IDE (Integrated Development Environment) for use in the bootcamp, and all demonstrations are done in Visual Studio Code. Students are encouraged to use Visual Studio Code, though this is not required.

## Miscellaneous/Other

### Operating Systems Basics

gem5 can simulate operating systems (OS). Students are expected to be able to:

- [ ] Describe the role of the operating system,
- [ ] Explain what an interrupt is,
- [ ] Explain what a system call (syscall) is,
- [ ] List common Linux system calls,
- [ ] Explain the concept of deadlock.

### Virtual Machines

Required to understand how the gem5 simulator emulates hardware. Students are expected to be able to:

- [ ] Explain what a virtual machine is,
- [ ] Define the concept of a virtualizer/hypervisor/VMM,
- [ ] Define what a guest OS and a host OS are.

### Power Modeling

The bootcamp covers gem5’s power modeling capabilities with a short demonstration. Students are expected to be able to:

- [ ] Explain what “activation count” power modeling is.
- [ ] Identify what McPAT, Wattch, and CACTI are.
