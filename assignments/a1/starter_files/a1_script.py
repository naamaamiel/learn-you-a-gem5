from gem5.components.boards.riscv_board import RiscvBoard

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

board.set_workload(
    # TODO
)

# Run the simulation until its end
sim = Simulator(board)
sim.run()
