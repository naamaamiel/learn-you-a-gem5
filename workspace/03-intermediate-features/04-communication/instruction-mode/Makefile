GEM5_PATH = /gem5
ISA = x86
GXX = g++


all: annotated_workload

annotated_workload: annotated_workload.cpp
	$(GXX) -o annotated_workload annotated_workload.cpp -I$(GEM5_PATH)/include -L$(GEM5_PATH)/util/m5/build/$(ISA)/out -lm5

clean:
	rm -f annotated_workload