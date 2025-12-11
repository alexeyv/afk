from dataclasses import dataclass


@dataclass(frozen=True)
class TurnResult:
    outcome: str
    message: str
    commit_hash: str
