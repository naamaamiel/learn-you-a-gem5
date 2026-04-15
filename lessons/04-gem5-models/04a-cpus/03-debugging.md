# Debugging gem5 SimObjects

Let's prepare to write our own branch predictor by debugging an existing one.

> By the end of this section, you will be able to:
>
> - **Create** a new debugging flag and enable/disable it using a configuration script and a command line option.
> - **Build** gem5 using Kconfig.
> - **Use** `DPRINTF()` statements to print debugging information in the presence of a flag.
> **Use** C++ `assert` statements and gem5 `fatal` and `panic` statements to verify assumptions and catch user and developer mistakes.
> - **Determine** which build-time configuration and compiler configuration are appropriate for a research goal.

## gem5's build system

So far, we've built gem5 by running this command:

```bash
scons build/ALL/gem5.opt -j$(nproc)
```

As it turns out, gem5's build system offers *many* more options than this, and understanding these options helps when debugging SimObjects.

There are many different ways to configure gem5, which all result in different binaries. Broadly, there are two different categories of options: **compiler configurations**, which define the set of optimizations and *debug flags* to be used, and **build-time options**, which determine what models will be included in the binary.

> You can see all available options by running `scons` with no arguments within the `gem5/` directory. Be warned: there is quite a bit of output to scroll through!

### Compiler configurations

You can tell which compiler configuration is being used for a gem5 build using the *suffix* attached to `gem5` in the `scons` command. For example, since we've been building `gem5.opt`, we've been building with the `opt` compiler configuration. gem5 provides three compiler configurations:

1. `fast`: This option enables all build optimizations and removes debugging symbols. The resulting binary is small (around 50 MiB), which makes it much faster. Since all debugging symbols are removed, you should **only use this configuration after debugging your models**.

2. `opt`: This option is optimized, but it includes debugging symbols and enables all assertions/panics. The resulting binary is *much* larger than `fast`'s (around 500 MiB). Despite this, `opt` is the most common compiler configuration. Debugging with GDB is mostly usable with `opt`, but some variables may be optimized away.

3. `debug`: This option is *not* optimized (it uses the `-O1` flag), includes all debugging symbols, and enables all assertions/panics. This configuration is ***much*** slower than `opt` (5-10 times slower), so you should only reach for it if you need to debug your models and `opt` is not enough.

> Overall, choosing a compiler configuration comes down to the phase of development you are in. `debug` and `opt` are useful when actively making changes to the backend, while `fast` is great when the dust has settled.

### Build-time configurations

gem5 includes *many* default build options:

```txt
ALL                       GCN3_X86                  NULL_MOESI_hammer  X86_MESI_Two_Level
ARM                       MIPS                      POWER              X86_MI_example
ARM_MESI_Three_Level      NULL                      RISCV              X86_MOESI_AMD_Base
ARM_MESI_Three_Level_HTM  NULL_MESI_Two_Level       SPARC
ARM_MOESI_hammer          NULL_MOESI_CMP_directory  VEGA_X86
Garnet_standalone         NULL_MOESI_CMP_token      X86
```

As the names suggest, these options determine the ISA(s) and cache coherence protocol that the binary will contain. We've been using the default build configuration `ALL`, which includes every supported ISA and Ruby coherence protocol.

If the default build configurations don't cut it, you can create your own! One way to do this is interactively with **Kconfig**.

> [Kconfig](https://docs.kernel.org/kbuild/kconfig-language.html) is a configuration tool/language also used for the Linux kernel and many other pieces of software with complex build systems. 

To use Kconfig, first make a new build directory using one of the default build options. Let's make a build directory named `my_gem5` and base it off of the `ALL` default configuration:

```bash
scons defconfig build/my_gem5/ build_opts/ALL
```

> While we are running this command from the `gem5` directory to place this directory alongside all the other build directory, this directory can go *anywhere on your system*.

If you navigate to `gem5/build/`, you should now see a directory called `my_gem5` alongside the one called `ALL` that we've been using this whole time. We can now use Kconfig to interactively change our configuration:

```bash
scons menuconfig build/my_gem5/
```

You can use the UP and DOWN arrows to hover over different build configuration options and menus and SPACE/ENTER to select/deselect them. You can exit from a menu by pressing ESC. 

> **Your turn:** Take some time to explore the interactive build tool. Can you figure out how to disable the CHI cache coherence model in this configuration?
>
> <details>
> <summary> <b>Answer</b> </summary>
> 
> Navigate to the `Ruby Protocols` menu:
>
> ```bash
> (Top) -> Ruby -> Enable -> Ruby Protocols
> ```
>
> Use the DOWN key to scroll down to the `CHI` protocol, and click SPACE/ENTER to disable it.
> 
> ```bash
> [ ] CHI
> ```
> 
> Then, press Q to quit and Y to save when prompted.
> </details>

<br>

Once you have a build configured to your liking, you can build gem5 with it using SCons. You are **NOT REQUIRED** to run the following command, and we will continue to use `ALL` and `gem5.opt` for this bootcamp:

```bash
scons build/my_gem5/gem5.opt -j$(nproc)
```

> As a reminder, `-j$(nproc)` uses all processor cores to build gem5. If you find yourself running into out-of-memory errors on your device, using fewer cores may help.

## `DebugFlags`

Other than selecting the appropriate compiler configuration for debugging with tools like GDB and asserts/panics, you can also enable (and write!) your own `DebugFlags` to use in gem5.