"""
Assignment #2: Build-a-Shadow-Unit

Name: Solution
"""

import argparse

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (
    PrivateL1PrivateL2CacheHierarchy,
)
from gem5.components.memory.single_channel import SingleChannelDDR3_1600
from gem5.resources.resource import BinaryResource
from gem5.simulate.simulator import Simulator

from a2_components import ShadowProcessor

parser = argparse.ArgumentParser(
    description="Run a program on an O3 core with a shadow unit."
)
parser.add_argument("--binary", required=True,
                    help="static RISC-V binary to run")
parser.add_argument("--lanes", type=int, default=0,
                    help="shadow lanes (0: no shadow unit)")
parser.add_argument("--compare-latency", type=int, default=0,
                    help="comparator latency in cycles")
parser.add_argument("--shadow-fault-period", type=int, default=0,
                    help="corrupt about 1 in this many S results (0: never)")
parser.add_argument("--cpu-fault-period", type=int, default=0,
                    help="corrupt about 1 in this many P results (0: never)")
parser.add_argument("--seed", type=int, default=1,
                    help="seed for both fault injectors")
parser.add_argument("--speculative", action="store_true",
                    help="Part 5: write results back before the check "
                         "(shadowSpeculative)")
args = parser.parse_args()

shadow_unit = None
if args.lanes > 0:
    # Imported here so that baseline runs work before you've built your unit.
    from m5.objects.ShadowUnit import ShadowUnit

    shadow_unit = ShadowUnit(
        num_lanes=args.lanes,
        compare_latency=args.compare_latency,
        fault_period=args.shadow_fault_period,
        fault_seed=args.seed,
    )

processor = ShadowProcessor(shadow_unit)

# The CPU's own fault injector, part of the provided CPU side
cpu = processor.get_cores()[0].get_simobject()
cpu.faultInjectPeriod = args.cpu_fault_period
cpu.faultInjectSeed = args.seed
# Part 5: write results back before their checks (off: the CPU holds each
# result until its check passes)
cpu.shadowSpeculative = args.speculative

cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(
    l1d_size="32KiB", l1i_size="32KiB", l2_size="2MiB"
)
memory = SingleChannelDDR3_1600(size="2GiB")

board = SimpleBoard(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)
board.set_se_binary_workload(BinaryResource(local_path=args.binary))

simulator = Simulator(board=board)
simulator.run()
