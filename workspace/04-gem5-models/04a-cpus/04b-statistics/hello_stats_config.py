import m5

from m5.objects.Root import Root
from m5.objects.HelloSimObject import HelloSimObject

root = Root(full_system=False)
root.hello = HelloSimObject(num_hellos=4)

m5.instantiate()

# First 1250 ticks: hellos at ticks 500 and 1000
exit_event = m5.simulate(1250)
print(f"Exited simulation because: {exit_event.getCause()}.")

# TODO: write the stats so far to stats.txt, then start counting from zero

# Next 1250 ticks: hellos at ticks 1500 and 2000
exit_event = m5.simulate(1250)
print(f"Exited simulation because: {exit_event.getCause()}.")
