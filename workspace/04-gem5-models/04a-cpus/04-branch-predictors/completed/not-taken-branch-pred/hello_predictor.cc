/*
 * Copyright (c) 2022-2023 The University of Edinburgh
 * All rights reserved
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Copyright (c) 2004-2006 The Regents of The University of Michigan
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "bootcamp/branch-pred/hello_predictor.hh"
#include "debug/HelloBranchPred.hh"

#include <algorithm>

namespace gem5
{

namespace branch_prediction
{

HelloBP::HelloBP(const HelloBPParams &params)
    : BPredUnit(params),
    localPredictorSize(params.localPredictorSize),
    localPredictorElts(localPredictorSize / sizeof(Addr)),
    notTakens()
{
    if (!isPowerOf2(localPredictorSize)) {
        fatal("Invalid local predictor size!\n");
    }

    if (!isPowerOf2(localPredictorElts)) {
        fatal("Invalid number of local predictor elements! Check localPredictorSize.\n");
    }
}

void
HelloBP::updateHistories(ThreadID tid, Addr pc, bool uncond, bool taken,
                         Addr target, const StaticInstPtr &inst,
                         void * &bp_history)
{
// Place holder for a function that is called to update predictor history
}


bool
HelloBP::lookup(ThreadID tid, Addr branch_addr, void * &bp_history)
{   
    // check the list of not taken PCs; is this there?
    if (std::find(notTakens.begin(), notTakens.end(), branch_addr) != notTakens.end()) {
        // if there, predict not taken
        DPRINTF(HelloBranchPred, "Address %ld found in set, predicted not taken\n", branch_addr);
        return 0;
    } else {
        // otherwise, predict taken
        DPRINTF(HelloBranchPred, "Address %ld not found in set, predicted taken\n", branch_addr);
        return 1;
    }
}

void
HelloBP::update(ThreadID tid, Addr branch_addr, bool taken, void *&bp_history,
                bool squashed, const StaticInstPtr & inst, Addr target)
{
    assert(bp_history == NULL);
    if(squashed){
        return;
    }
    DPRINTF(HelloBranchPred, "update() called on non-squashed address %ld\n", branch_addr);
    // if the branch is taken, we don't need to do anything
    if (taken) {
        DPRINTF(HelloBranchPred, "    update(): Address %ld was taken\n", branch_addr);
        return;
    }
    // if the branch is already in the list, remove it (so it can be re-added to the front)
    auto iter = std::find(notTakens.begin(), notTakens.end(), branch_addr);
    if (iter != notTakens.end()) {
        DPRINTF(HelloBranchPred, "    update(): Address %ld already in set of not takens\n", branch_addr);
        notTakens.erase(iter);
    }
    // do we have room for this address?
    if (notTakens.size() == localPredictorElts) {
        // evict from the back
        Addr evicted = notTakens.back();
        notTakens.pop_back();
        DPRINTF(HelloBranchPred, "    update(): Removed address %ld to make room for address %ld\n", evicted, branch_addr);
    }
    // push the address to the front
    notTakens.push_front(branch_addr);
    DPRINTF(HelloBranchPred, "    update(): Address %ld added to list of not takens\n", branch_addr);
}

} // namespace branch_prediction
} // namespace gem5
