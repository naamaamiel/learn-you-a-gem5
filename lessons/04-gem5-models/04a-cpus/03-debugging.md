# Debugging gem5 SimObjects

Let's start writing our own branch predictor!

> - **Extend** an existing gem5 SimObject to enable new simulation functionality.
> - **Create** a new debugging flag and enable/disable it using a configuration script and a command line option.
> - **Build** gem5 using Kconfig.
> - **Use** `DPRINTF()` statements to print debugging information in the presence of a flag.
> **Use** C++ `assert` statements and gem5 `fatal` and `panic` statements to verify assumptions and catch user and developer mistakes.
> - **Determine** which build-time configuration and compiler configuration are appropriate for a research goal.
