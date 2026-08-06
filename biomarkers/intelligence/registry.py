from typing import Tuple
from biomarkers.intelligence.rules import (
    BiomarkerInsightRule,
    GenericIncreasingRule,
    GenericDecreasingRule,
    GenericStableRule,
    GenericUnknownRule,
)
from biomarkers.intelligence.ferritin_rule import FerritinRule
from biomarkers.intelligence.crp_rule import CRPRule
from biomarkers.intelligence.vitamin_d_rule import VitaminDRule


class BiomarkerInsightRuleRegistry:
    """
    Registry serving as a factory configuration for default intelligence rules.
    """

    def rules(self) -> Tuple[BiomarkerInsightRule, ...]:
        return (
            FerritinRule(),
            CRPRule(),
            VitaminDRule(),
            GenericIncreasingRule(),
            GenericDecreasingRule(),
            GenericStableRule(),
            GenericUnknownRule(),
        )



