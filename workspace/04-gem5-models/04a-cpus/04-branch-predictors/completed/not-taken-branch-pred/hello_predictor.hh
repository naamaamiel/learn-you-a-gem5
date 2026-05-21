#ifndef __BOOTCAMP_BRANCH_PRED_HELLO_PREDICTOR_HH__
#define __BOOTCAMP_BRANCH_PRED_HELLO_PREDICTOR_HH__

#include "base/types.hh"
#include "cpu/pred/bpred_unit.hh"
#include "params/HelloBP.hh"

namespace gem5
{

namespace branch_prediction
{

class HelloBP : public BPredUnit
{
  public:
    /**
     * Default branch predictor constructor.
     */
    HelloBP(const HelloBPParams &params);

    // Overriding interface functions
    bool lookup(ThreadID tid, Addr pc, void * &bp_history) override;

    void updateHistories(ThreadID tid, Addr pc, bool uncond, bool taken,
                         Addr target, const StaticInstPtr &inst,
                         void * &bp_history) override;

    void update(ThreadID tid, Addr pc, bool taken,
                void * &bp_history, bool squashed,
                const StaticInstPtr & inst, Addr target) override;

    void squash(ThreadID tid, void * &bp_history) override
    { assert(bp_history == NULL); }

  private:
      const unsigned localPredictorSize;

      const unsigned localPredictorElts;

      std::list<Addr> notTakens;
};

} // namespace branch_prediction
} // namespace gem5

#endif // __BOOTCAMP_BRANCH_PRED_HELLO_PREDICTOR_HH__
