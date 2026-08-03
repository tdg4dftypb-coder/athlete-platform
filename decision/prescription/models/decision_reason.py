from enum import Enum


class DecisionReason(str, Enum):
    ADAPTATION_REDUCE_LOAD = "adaptation_reduce_load"
    INSIGHT_NEED_MORE_RECOVERY = "insight_need_more_recovery"
    INSIGHT_FATIGUE_ACCUMULATING = "insight_fatigue_accumulating"
    INSIGHT_HIGH_TRAINING_COMPLIANCE = "insight_high_training_compliance"
