from dataclasses import dataclass
from datetime import datetime

from afk.turn_result import TurnResult


@dataclass(frozen=True)
class Turn:
    turn_number: int
    transition_type: str
    result: TurnResult | None
    log_file: str
    timestamp: datetime
