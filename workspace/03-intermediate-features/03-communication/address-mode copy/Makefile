GEM5_PATH = /gem5
ISA = x86
GXX = g++


all: address_annotated_workload

address_annotated_workload: address_annotated_workload.cpp
	$(GXX) -o address_annotated_workload address_annotated_workload.cpp -I$(GEM5_PATH)/include -L$(GEM5_PATH)/util/m5/build/$(ISA)/out -lm5

clean:
	rm -f address_annotated_workload