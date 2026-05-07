#include <gem5/m5ops.h>
#include <stdio.h>

int main(int argc, char** argv) {
  m5_hypercall(4);  // work/ROI begin hypercall
  fprintf(stderr, "Hello, stderr!\n");
  m5_hypercall(5);  // work/ROI end hypercall
  return 0;
}
