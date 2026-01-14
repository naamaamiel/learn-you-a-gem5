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

> **Aside: Setting up bootcamp work**
>
> Throughout this bootcamp, we'll be providing resources (executables, Python and C++ files, etc.) for you to build on. They are available in the `workspace` directory. We highly recommend that you place the `workspace` directory and the `gem5` directory under the same parent; that is, run the above clone command from the parent directory of where you placed the `workspace` directory.
>

Congratulations! You now have... a bunch of source code. The next step is to *build* this source code into a binary that you can use to run simulations.

## Building gem5

You can now build gem5 using SCons! Navigate to the `gem5` directory and run:

```bash
scons build/ALL/gem5.opt -j $(nproc)
```

This command builds gem5 with all ISAs (`ALL`) with the `.opt` debug option (a balance of speed optimizations and debugging flags) using all of the available processors.

**This command will take a while!!!** gem5 can take over 45 minutes to build. While that's going on, feel free to take a break or read through the [bootcamp introduction](../01-sim-background/00-welcome.md) if you haven't already. When the building process is finally done, you'll find the binary your computer has been building for so long at `<path-to-your-gem5-folder>/build/ALL/gem5.opt`.

## Navigating the `gem5` directory

While you wait for everything to build, gem5 contains a *lot* of source code. Here are a few basic directories you should have in mind:

- `build`: this directory will only be visible after you've successfully built gem5. This directory stores build files, including the gem5 executable you will be running.

> If you used the command above, the gem5 executable you created can be found at `gem5/build/ALL/gem5.opt`. We'll be running this executable throughout the bootcamp.

- `src`: contains all source files for gem5. These files are separated into groups based on their purpose.
  - `src/python/gem5`: contains all pre-made Python components from the gem5 standard library. You may remember from the [Enter gem5 section](lessons/01-introduction/03-installing-gem5.md) that Python files specify parameter values for C++ backend models. We'll talk more about the standard library in the next section.
  - `src/mem`: contains all C++ models relating to memory, like caches, DRAM, crossbars, and memory probes.
  - `src/arch`: contains all ISA-specific C++ models, including the ISAs themselves.
  - `src/sim`: contains files relating to simulation, including the C++ parent class for all models, `SimObject`.

> It might be a bit overwhelming to dig through the entire `src` directory at the moment, and that's okay! We'll start exploring these files are we progress through the bootcamp, and you certainly aren't expected to explain what all these files do quite yet.

## Let's go!

Once that long build process is done, you should have access to a gem5 executable. For us, that's

```bash
./gem5/build/ALL/gem5.opt
```

If you enter the above in your terminal, you should get the following usage message:

```txt
gem5 Simulator System.  https://www.gem5.org
gem5 is copyrighted software; use the --copyright option for details.

gem5 version 25.0.0.1
gem5 compiled <COMPILATION TIME>
gem5 started <START TIME>
gem5 executing on <ENVIRONMENT>, pid <PROCESS ID>
command line: ./gem5/build/ALL/gem5.opt

Usage
=====
  gem5.opt [gem5 options] script.py [script options]

gem5 is copyrighted software; use the --copyright option for details.

Options
=======
--help, -h              show this help message and exit
--build-info, -B        Show build information
--copyright, -C         Show full copyright information
--readme, -R            Show the readme
--outdir=DIR, -d DIR    Set the output directory to DIR [Default: m5out]
--redirect-stdout, -r   Redirect stdout (& stderr, without -e) to file
--redirect-stderr, -e   Redirect stderr to file
--silent-redirect       Suppress printing a message when redirecting stdout or
                        stderr
--stdout-file=FILE      Filename for -r redirection [Default: simout.txt]
--stderr-file=FILE      Filename for -e redirection [Default: simerr.txt]
--listener-mode={on,off,auto}
                        Port (e.g., gdb) listener mode (auto: Enable if
                        running interactively) [Default: auto]
--allow-remote-connections
                        Port listeners will accept connections from anywhere
                        (0.0.0.0). Default is only localhost.
--interactive, -i       Invoke the interactive interpreter after running the
                        script
--pdb                   Invoke the python debugger before running the script
--path=PATH[:PATH], -p PATH[:PATH]
                        Prepend PATH to the system path when invoking the
                        script
--quiet, -q             Reduce verbosity
--verbose, -v           Increase verbosity
-m mod                  run library module as a script (terminates option
                        list)
-c cmd                  program passed in as string (terminates option list)
-P                      Don't prepend the script directory to the system path.
                        Mimics Python 3's `-P` option.
-s                      IGNORED, only for compatibility with python. don'tadd
                        user site directory to sys.path; also PYTHONNOUSERSITE

Statistics Options
------------------
--stats-file=FILE       Sets the output file for statistics [Default:
                        stats.txt]
--stats-help            Display documentation for available stat visitors

Configuration Options
---------------------
--dump-config=FILE      Dump configuration output file [Default: config.ini]
--json-config=FILE      Create JSON output of the configuration [Default:
                        config.json]
--dot-config=FILE       Create DOT & pdf outputs of the configuration
                        [Default: config.dot]
--dot-dvfs-config=FILE  Create DOT & pdf outputs of the DVFS configuration
                        [Default: none]

Debugging Options
-----------------
--debug-break=TICK[,TICK]
                        Create breakpoint(s) at TICK(s) (kills process if no
                        debugger attached)
--debug-help            Print help on debug flags
--debug-flags=FLAG[,FLAG]
                        Sets the flags for debug output (-FLAG disables a
                        flag)
--debug-start=TICK      Start debug output at TICK
--debug-end=TICK        End debug output at TICK
--debug-file=FILE       Sets the output file for debug. Append '.gz' to the
                        name for it to be compressed automatically [Default:
                        cout]
--debug-activate=EXPR[,EXPR]
                        Activate EXPR sim objects
--debug-ignore=EXPR     Ignore EXPR sim objects
--remote-gdb-port=REMOTE_GDB_PORT
                        Remote gdb base port (set to 0 to disable listening)
--show-exit-event-messages
                        Print information about exit events and when they
                        occur

Help Options
------------
--list-sim-objects      List all built-in SimObjects, their params and default
                        values
```

If you successfully see this message, this means gem5 was built! If you run into any issues building, please refer to the building gem5 page linked at the beginning of this section or visit the [gem5 common errors document](https://www.gem5.org/documentation/general_docs/common-errors/).

### Quick quality-of-life change: alias

You may notice that if you try to run this executable from the `gem5` directory's parent directory (which should also be the parent directory of your `workspace` directory), the path to the executable is quite long. For convenience, you can create an **alias** for this executable so that you can more easily run files from your workspace. Add the following line to your `bashrc` file (found at `~/.bashrc`):

```bash
alias gem5_opt=<absolute_path_to_parent_directory>/gem5/build/ALL/gem5.opt
```

where `<absolute_path_to_parent_directory>` is replaced with the absolute path to the directory containing the `gem5` directory. You can get to this absolute path by navigating to the gem5 directory then using the `pwd` ("print working directory") command.

After creating this alias, you should be able to type

```bash
gem5
```

in your terminal to get the same usage message from before. 

> Note that we chose to alias the executable as `gem5`, but you can choose whatever name you want!

We'll be referencing `gem5/build/ALL/gem5.opt` as `gem5` for the rest of the bootcamp.
