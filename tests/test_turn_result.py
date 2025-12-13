import pytest

from afk.turn_result import TurnResult


class TestTurnResultDataclass:
    def test_creates_turn_result_with_all_fields(self):
        result = TurnResult(
            outcome="success",
            message="feat: add feature\n\noutcome: success",
            commit_hash="abc123def456",
        )
        assert result.outcome == "success"
        assert result.message == "feat: add feature\n\noutcome: success"
        assert result.commit_hash == "abc123def456"

    def test_turn_result_is_frozen(self):
        result = TurnResult(
            outcome="success",
            message="test message",
            commit_hash="abc123",
        )
        with pytest.raises(AttributeError):
            result.outcome = "failure"  # type: ignore[misc]

    def test_turn_result_equality(self):
        result1 = TurnResult(
            outcome="success",
            message="msg",
            commit_hash="abc123",
        )
        result2 = TurnResult(
            outcome="success",
            message="msg",
            commit_hash="abc123",
        )
        assert result1 == result2

    def test_turn_result_repr(self):
        result = TurnResult(
            outcome="success",
            message="msg",
            commit_hash="abc123",
        )
        repr_str = repr(result)
        assert "TurnResult" in repr_str
        assert "success" in repr_str
        assert "abc123" in repr_str


class TestTurnResultValidation:
    def test_rejects_non_string_outcome(self):
        with pytest.raises(TypeError, match="expected str or None for outcome"):
            TurnResult(outcome=123, message="msg", commit_hash="abc")  # type: ignore[arg-type]

    def test_accepts_none_outcome(self):
        result = TurnResult(outcome=None, message="msg", commit_hash="abc")
        assert result.outcome is None

    def test_rejects_non_string_message(self):
        with pytest.raises(TypeError, match="expected str for message"):
            TurnResult(outcome="success", message=123, commit_hash="abc")  # type: ignore[arg-type]

    def test_rejects_non_string_commit_hash(self):
        with pytest.raises(TypeError, match="expected str for commit_hash"):
            TurnResult(outcome="success", message="msg", commit_hash=123)  # type: ignore[arg-type]
