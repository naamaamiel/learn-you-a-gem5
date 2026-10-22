from gem5.components.boards.x86_board import X86Board

# TODO

# to run the simulation
from gem5.simulate.simulator import Simulator

"""
Assignment #1: Assemble-Your-Own-System

Name: 
"""

processor = # TODO

cache = # TODO

memory = # TODO

board = X86Board(
    # TODO
)

board.set_workload(
    # TODO
)

# Run the simulation until its end
sim = Simulator(board)
sim.run()
