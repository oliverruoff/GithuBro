from __future__ import annotations

import logging
import threading

from app.config import Config
from app.github.client import GitHubClient
from app.github.issues import get_comments, post_comment
from app.util.time import iso_now, seconds_old

log = logging.getLogger(__name__)


class Heartbeat:
    def __init__(self, client: GitHubClient, config: Config, repo: str, issue: int):
        self.client, self.config, self.repo, self.issue = client, config, repo, issue
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="githubro-heartbeat", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=5)

    def _run(self) -> None:
        while not self.stop_event.wait(self.config.heartbeat_interval):
            try:
                comments = get_comments(self.client, self.repo, self.issue)
                beats = [c for c in comments if c.body.startswith("[githubro:runner][event:heartbeat]")]
                if beats and seconds_old(max(beats, key=lambda c: c.created_at).created_at) < self.config.heartbeat_interval:
                    continue
                post_comment(self.client, self.repo, self.issue, (
                    "[githubro:runner][event:heartbeat]\n"
                    "⏳ githubro still working on this issue.\n"
                    f"Last update: {iso_now()}\n@{self.config.username}"
                ))
            except Exception:
                log.exception("heartbeat failed", extra={"repo": self.repo, "issue": self.issue})
