from dataclasses import dataclass


@dataclass(frozen=True)
class TurnResult:
    outcome: str | None
    message: str
    commit_hash: str

    def __post_init__(self) -> None:
        if self.outcome is not None and not isinstance(self.outcome, str):
            raise TypeError(f"expected str or None for outcome, got {self.outcome!r}")
        if not isinstance(self.message, str):
            raise TypeError(f"expected str for message, got {self.message!r}")
        if not isinstance(self.commit_hash, str):
            raise TypeError(f"expected str for commit_hash, got {self.commit_hash!r}")
