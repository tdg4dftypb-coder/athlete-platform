from dataclasses import dataclass

from recovery.models import RecoveryResult


@dataclass
class RecoveryState:

    result: RecoveryResult