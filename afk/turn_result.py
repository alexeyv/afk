from dataclasses import dataclass


@dataclass(frozen=True)
class TurnResult:
    outcome: str | None
    message: str
    commit_hash: str
