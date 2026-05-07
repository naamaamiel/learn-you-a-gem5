GEM5_PATH = /learn-you-a-gem5/gem5
ISA = x86
GCC = gcc


all: annotated_workload

annotated_workload: annotated_workload.c
	$(GCC) -o annotated_workload annotated_workload.c -I$(GEM5_PATH)/include -L$(GEM5_PATH)/util/m5/build/$(ISA)/out -lm5

clean:
	rm -f annotated_workload