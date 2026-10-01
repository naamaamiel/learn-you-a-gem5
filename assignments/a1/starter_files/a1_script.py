from gem5.components.boards.riscv_board import RiscvBoard

# TODO

# for downloading the workload
from gem5.resources.resource import obtain_resource

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
Assignment #1: Assemble-Your-Own-System

Name: 
"""

processor = # TODO

cache = # TODO

memory = # TODO

board = RiscvBoard(
    # TODO
)

# Set the workload to GAPBS BFS benchmark 
board.set_workload(
    obtain_resource("riscv-gapbs-bfs-run")
)

# Run the simulation until its end
sim = Simulator(board)
sim.run()
