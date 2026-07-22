from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Mode(str, Enum):
    FRESH = "fresh"
    REVISION = "revision"
    SELF_AUDIT = "self-audit"


@dataclass(frozen=True)
class Comment:
    body: str
    created_at: str
    author: str = ""
    source: str = "issue"


BOT_PREFIXES = ("[githubro:runner]", "[githubro:agent]")


def is_githubro_comment(comment: Comment) -> bool:
    return comment.body.startswith(BOT_PREFIXES)


def determine_mode(pr: dict | None, comments: Iterable[Comment]) -> Mode:
    if not pr or str(pr.get("state", "")).lower() in {"closed", "merged"}:
        return Mode.FRESH
    if str(pr.get("state", "")).lower() != "open":
        return Mode.FRESH
    ordered = sorted(comments, key=lambda item: item.created_at)
    bot_times = [c.created_at for c in ordered if is_githubro_comment(c)]
    last_bot = max(bot_times, default="")
    if any(not is_githubro_comment(c) and c.created_at > last_bot for c in ordered):
        return Mode.REVISION
    return Mode.SELF_AUDIT


def user_feedback_since_activity(comments: Iterable[Comment]) -> list[Comment]:
    items = list(comments)
    last_bot = max((c.created_at for c in items if is_githubro_comment(c)), default="")
    return sorted(
        (c for c in items if not is_githubro_comment(c) and c.created_at > last_bot),
        key=lambda c: c.created_at,
    )
