#!/usr/bin/env bash
# Run every checkpoint configuration of Assignment 2 into out/<run>/.
# Usage: GEM5=/path/to/gem5/build/ALL/gem5.opt JOBS=8 ./run_a2.sh
set -u
GEM5=${GEM5:?set GEM5 to your gem5.opt}
JOBS=${JOBS:-8}

run() {  # run <name> [options...]; the program is <name> up to its first "-"
    local name=$1; shift
    while (( $(jobs -rp | wc -l) >= JOBS )); do sleep 1; done
    "$GEM5" -re -d "out/$name" a2_script.py --binary "tests/${name%%-*}" "$@" &
}

for p in chain_add chain_mul chain_div indep_add kernel; do
    run "$p-base"                    # Part 0: no shadow unit
    run "$p-p1" --lanes 64           # Part 1 behavior: lanes never run out, C = 0
done
for n in 1 2 3 4 6 8; do run "indep_add-n$n" --lanes "$n"; done
for p in chain_add chain_mul chain_div; do run "$p-n1" --lanes 1; done
run chain_add-c2 --lanes 1 --compare-latency 2
run kernel-pfaults --lanes 4 --cpu-fault-period 1000
run kernel-pfaults-nounit --cpu-fault-period 1000
run kernel-sfaults --lanes 4 --shadow-fault-period 1000
for p in chain_add chain_mul chain_div indep_add; do
    run "$p-spec" --lanes 64 --speculative   # Part 5: speculation, C = 0
done
run kernel-spec-pfaults --lanes 4 --cpu-fault-period 1000 --speculative
wait
echo "Done. Now run: ./check_a2.py"
