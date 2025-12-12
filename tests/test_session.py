from datetime import datetime, timezone
from pathlib import Path

import pytest

from afk.session import Session
from afk.turn import Turn
from afk.turn_result import TurnResult

FIXED_TIME = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_turn(n: int, transition_type: str = "coding") -> Turn:
    """Helper to create Turn instances for testing."""
    return Turn(
        turn_number=n,
        transition_type=transition_type,
        result=TurnResult(outcome="success", message="test", commit_hash="abc123"),
        log_file=Path(f"/logs/turn-{n:03d}.log"),
        timestamp=FIXED_TIME,
    )


class TestSession:
    def test_empty_session(self):
        """AC#4: Session can be instantiated and returns empty tuple of turns."""
        session = Session()
        assert session.turns == ()
        assert list(session) == []

    def test_add_single_turn(self):
        """AC#1: add_turn adds turn to session."""
        session = Session()
        turn = make_turn(1, "init")
        session.add_turn(turn)
        assert session.turns == (turn,)

    def test_add_multiple_turns_in_order(self):
        """AC#1: Turns are stored in order of addition."""
        session = Session()
        t1 = make_turn(1, "init")
        t2 = make_turn(2, "coding")
        t3 = make_turn(3, "coding")
        session.add_turn(t1)
        session.add_turn(t2)
        session.add_turn(t3)
        assert session.turns == (t1, t2, t3)

    def test_turn_lookup_by_number(self):
        """AC#2: turn(n) returns correct turn by turn_number."""
        session = Session()
        t1 = make_turn(1)
        t2 = make_turn(2)
        session.add_turn(t1)
        session.add_turn(t2)
        assert session.turn(1) is t1
        assert session.turn(2) is t2

    def test_turn_lookup_raises_keyerror(self):
        """AC#2: turn(n) raises KeyError for non-existent turn."""
        session = Session()
        session.add_turn(make_turn(1))
        with pytest.raises(KeyError):
            session.turn(99)

    def test_iteration_chronological_order(self):
        """AC#3: Iteration yields turns in chronological order."""
        session = Session()
        turns = [make_turn(i) for i in range(1, 4)]
        for t in turns:
            session.add_turn(t)
        assert list(session) == turns

    def test_turns_property_is_immutable(self):
        """AC#4: turns property returns tuple (immutable view)."""
        session = Session()
        session.add_turn(make_turn(1))
        turns = session.turns
        assert isinstance(turns, tuple)

    def test_add_turn_validates_sequence_starts_at_one(self):
        """AC#1: Turn numbers must start at 1."""
        session = Session()
        with pytest.raises(ValueError, match="Expected turn number 1"):
            session.add_turn(make_turn(2))  # Should start at 1

    def test_add_turn_validates_next_number(self):
        """AC#1: Turn numbers must be sequential."""
        session = Session()
        session.add_turn(make_turn(1))
        with pytest.raises(ValueError, match="Expected turn number 2"):
            session.add_turn(make_turn(5))  # Should be 2

    def test_failed_add_doesnt_corrupt_state(self):
        """Failed add_turn must leave session state unchanged."""
        session = Session()
        session.add_turn(make_turn(1))
        with pytest.raises(ValueError):
            session.add_turn(make_turn(5))  # Wrong number - fails
        session.add_turn(make_turn(2))  # Correct next - should work
        assert len(session) == 2
        assert session.turn(1).turn_number == 1
        assert session.turn(2).turn_number == 2
