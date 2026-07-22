from datetime import datetime, timezone

from app.github.recovery import is_stale, latest_runner_activity
from app.modes import Comment


NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_absent_runner_activity_is_stale():
    assert is_stale([], 2700, NOW)


def test_latest_runner_comment_controls_freshness():
    comments = [
        Comment("[githubro:runner][event:start]", "2026-01-01T10:00:00Z"),
        Comment("user", "2026-01-01T11:59:00Z"),
        Comment("[githubro:runner][event:heartbeat]", "2026-01-01T11:30:00Z"),
    ]
    assert latest_runner_activity(comments) == comments[2]
    assert not is_stale(comments, 2700, NOW)
    assert is_stale(comments, 1200, NOW)
