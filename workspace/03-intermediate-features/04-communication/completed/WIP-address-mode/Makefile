GEM5_PATH = /learn-you-a-gem5/gem5
ISA = x86
GXX = g++


all: address_annotated_workload

address_annotated_workload: address_annotated_workload.c
	$(GXX) -o address_annotated_workload address_annotated_workload.c -no-pie \
  -I$(GEM5_PATH)/include \
  -L$(GEM5_PATH)/util/m5/build/$(ISA)/out \
  -I$(GEM5_PATH)/util/m5/src -lm5


clean:
	rm -f address_annotated_workload