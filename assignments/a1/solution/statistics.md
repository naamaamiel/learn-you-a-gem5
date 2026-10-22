# Simulation statistics

For each of the requested statistics, provide the full statistic name and its associated value. If a statistic description references for a value for each component in a set (for example, "for each core", "for each memory controller"), you will need to provide multiple statistic names and values.

## Example

**Description:** The total number of instructions bytes read from each memory controller.

**Statistic name(s):**

```txt
board.memory.mem_ctrl0.dram.bytesInstRead::total
board.memory.mem_ctrl1.dram.bytesInstRead::total
```

**Value(s):**

```txt
73344
74368
```

> The values of these statistics will not match your observed values!

## Assignment #1 statistics

### Statistic #1

**Description:** The number of seconds elapsed in-simulation.

**Statistic name(s):**

```txt
simSeconds
```

**Value(s):**

```txt
0.003502
```

### Statistic #2

**Description:** The core-level IPC (instructions per cycle) of each core of the CPU.

**Statistic name(s):**

```txt
board.processor.cores0.core.ipc 
board.processor.cores1.core.ipc 
```

**Value(s):**

```txt
0.861853
0.702861
```

### Statistic #3

**Description:** The overall miss rate of the L2 cache.

**Statistic name(s):**

```txt
board.cache_hierarchy.l2_cache.overallMissRate::total
```

**Value(s):**

```txt
0.094374
```

### Statistic #4

**Description:** The total number of read requests accepted by each memory controller.

**Statistic name(s):**

```txt
board.memory.mem_ctrl0.readReqs
board.memory.mem_ctrl1.readReqs
```

**Value(s):**

```txt
3738
3739
```