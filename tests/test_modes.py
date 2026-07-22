import pytest

from app.modes import Comment, Mode, determine_mode, user_feedback_since_activity


@pytest.mark.parametrize("pr", [None, {"state": "closed"}, {"state": "merged"}])
def test_no_active_pr_is_fresh(pr):
    assert determine_mode(pr, []) == Mode.FRESH


def test_open_pr_with_feedback_after_bot_is_revision():
    comments = [
        Comment("[githubro:agent][outcome:success] done", "2026-01-01T10:00:00Z"),
        Comment("Please handle nulls", "2026-01-01T11:00:00Z", "alice"),
    ]
    assert determine_mode({"state": "open"}, comments) == Mode.REVISION
    assert user_feedback_since_activity(comments) == [comments[1]]


def test_open_pr_without_new_feedback_is_self_audit():
    comments = [
        Comment("old human comment", "2026-01-01T09:00:00Z"),
        Comment("[githubro:runner][event:start]", "2026-01-01T10:00:00Z"),
    ]
    assert determine_mode({"state": "open"}, comments) == Mode.SELF_AUDIT


def test_open_pr_with_no_activity_treats_unprefixed_comment_as_feedback():
    assert determine_mode({"state": "open"}, [Comment("feedback", "2026-01-01T09:00:00Z")]) == Mode.REVISION
