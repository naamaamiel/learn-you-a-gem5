# Installing gem5

To work with gem5, you'll first need to... get gem5. This guide is adapted from the [building gem5 page on the gem5 website](https://www.gem5.org/documentation/general_docs/building). Please refer to this page for more detail and for up-to-date installation information.

> By the end of this section, you will be able to:  
>
> - **Download** and **build** the gem5 source code.
> - **Identify** important directories in the gem5 source code.
>

## Using the right machine

gem5 can be installed on a **Linux-based OS**. If you don't have access to such an environment, refer to the [Docker section of the building gem5 guide](https://www.gem5.org/documentation/general_docs/building#docker).

## Getting all of gem5's dependencies

> **TL;DR** make sure you have:
>
> - git,
> - gcc (version 10 to 13, inclusive) or Clang (version 7 to 16, inclusive),
> - Python (version 3.6 or higher),
> - SCons (version 3.0 or higher)
>
> Alternatively, run the following command to get all of them:
>
> ``` bash
> sudo apt install build-essential scons python3-dev git  pre-commit zlib1g zlib1g-dev \ 
> libprotobuf-dev protobuf-compiler libprotoc-dev libgoogle-perftools-dev \ 
> libboost-all-dev  libhdf5-serial-dev python3-pydot python3-venv python3-tk mypy \ 
> m4 libcapstone-dev libpng-dev libelf-dev pkg-config wget cmake doxygen
> ```
>
> If you do this, you can skip to the "getting the gem5 source code" heading.

gem5 requires a few other pieces of software in order to run. The command in the above TL;DR will take care of these for you, but you can check for them manually or learn a bit more about them below.

### git

gem5 uses git for version control. You can check whether you have git on your machine by running:

```bash
git --version
```

from the command line. You can learn more about git at the [git website](https://git-scm.com/).

### gcc or Clang

gcc and Clang are compilers used to compile gem5. Having either one of these is fine; you don't need both. You can check whether you have gcc or Clang by running:

```bash
gcc --version
clang --version
```

from the command line. Make sure that your gcc version is between 10 and 13 (inclusive), or that your Clang version is between 7 and 16 (inclusive). You can find out more at the [GNU website (gcc)](https://gcc.gnu.org/) and the [LLVM website (Clang)](https://clang.llvm.org/).

### Python

gem5 relies on Python development libraries. You can check whether you have Python by running:

```bash
python --version
```

from the command line. Double-check that your Python version is **3.6 or higher**. More on Python at the [Python website](https://www.python.org/).

### SCons

SCons is a software building tool used to build gem5. More on SCons can be found in the [online SCons user guide](https://scons.org/doc/production/HTML/scons-user.html).

### Optional dependencies

gem5 has two additional optional dependencies (libraries needed for a few gem5 features). **You don't need these for the bootcamp**, but you can install them if you like. These are protobuf (instructions on the [protobuf website](https://protobuf.dev/)) and Boost (instructions on the [Boost getting started manual](https://www.boost.org/doc/libs/latest/more/getting_started/)). The command in the TL;DR will install these, too.

## Getting the gem5 source code

Phew, we're done with all of that installing (or maybe just version checking). Time to get gem5 itself! gem5 is different from other software you might have used before: it is **distributed as source code**. You have to get the source code yourself, then build it yourself.

The gem5 source code is available on [the gem5 GitHub repository](https://github.com/gem5/gem5). You can peruse the repository if you like, but you can acquire the source code by simply running:

```bash
git clone https://github.com/gem5/gem5
```

from the command line.

Congratulations! You now have... a bunch of source code. The next step is to *build* this source code into a binary that you can use to run simulations.

## Building gem5

You can now build gem5 using SCons! Navigate to the `gem5` directory and run:

```bash
scons build/ALL/gem5.opt -j $(nproc)
```

This command builds gem5 with all ISAs (`ALL`) with the `.opt` debug option (a balance of speed optimizations and debugging flags) using all of the available processors.

**This command will take a while!!!** gem5 can take over 45 minutes to build. While that's going on, feel free to take a break or read through the [bootcamp introduction](../01-sim-background/00-welcome.md) if you haven't already. When the building process is finally done, you'll find the binary your computer has been building for so long at `<path-to-your-gem5-folder>/build/ALL/gem5.opt`.

## Navigating the `gem5` directory

<!-- TODO (Naama): Once installed gem5, fill this in with nav information -->