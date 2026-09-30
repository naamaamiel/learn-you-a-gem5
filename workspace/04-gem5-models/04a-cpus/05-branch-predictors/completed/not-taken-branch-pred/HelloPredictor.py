from m5.objects.BranchPredictor import BranchPredictor
from m5.params import *

class HelloBP(BranchPredictor):
    type = "HelloBP"
    cxx_class = "gem5::branch_prediction::HelloBP"
    cxx_header = "bootcamp/branch-pred/hello_predictor.hh"

    localPredictorSize = Param.Unsigned(512, "Size of local predictor")
