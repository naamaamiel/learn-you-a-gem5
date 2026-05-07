#include <gem5/m5ops.h>
#include <m5_mmap.h>
#include <stdio.h>

int main(int argc, char** argv) {
  // set up address-mode m5ops
  m5op_addr = 0XFFFF0000;
  map_m5_mem();

  m5_hypercall_addr(4);
  fprintf(stderr, "Hello, stderr!\n");
  m5_hypercall_addr(5);

  // unmap m5ops range
  unmap_m5_mem();
  return 0;
}
