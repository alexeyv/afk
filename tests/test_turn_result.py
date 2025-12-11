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
            result.outcome = "failure"

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
