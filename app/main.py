from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

from app.config import Config
from app.github.client import GitHubClient
from app.github.labels import ensure_workflow_labels
from app.log import configure_logging
from app.runner.cleanup import cleanup
from app.runner.llm import run_llm
from app.runner.poll import poll
from app.runner.setup import setup

log = logging.getLogger(__name__)


def run_tick(client: GitHubClient, config: Config) -> None:
    candidate = poll(client, config)
    if candidate is None:
        return
    try:
        prepared = setup(client, config, candidate)
    except Exception:
        log.exception("setup failed", extra={"repo": candidate.repo, "issue": candidate.issue["number"]})
        return
    try:
        result = run_llm(client, config, prepared)
    except Exception:
        log.exception("pi invocation failed", extra={"repo": candidate.repo, "issue": candidate.issue["number"]})
        from app.runner.llm import LLMResult
        result = LLMResult(-1, False, "", "pi invocation failed", 0.0)
    cleanup(client, config, prepared, result)


def seconds_until_next_tick(config: Config, now: datetime | None = None) -> float:
    current = now or datetime.now().astimezone()
    if config.poll_interval < 900:
        return float(config.poll_interval)
    minute = ((current.minute // 15) + 1) * 15
    boundary = current.replace(second=0, microsecond=0)
    if minute >= 60:
        boundary = boundary.replace(minute=0) + timedelta(hours=1)
    else:
        boundary = boundary.replace(minute=minute)
    return max(0.0, (boundary - current).total_seconds())


def main() -> None:
    try:
        config = Config.from_env()
    except ValueError as exc:
        configure_logging("INFO")
        log.error("configuration error: %s", exc)
        raise SystemExit(2) from exc
    configure_logging(config.log_level)
    client = GitHubClient(config.github_pat)
    try:
        created = ensure_workflow_labels(
            client,
            config.repos,
            trigger=config.trigger_label,
            in_progress=config.in_progress_label,
            done=config.done_label,
        )
    except Exception as exc:
        log.error("workflow label provisioning failed: %s", exc, exc_info=True)
        raise SystemExit(3) from exc
    for repo, labels in created.items():
        if labels:
            log.info("created missing workflow labels: %s", ", ".join(labels), extra={"repo": repo})
        else:
            log.info("workflow labels ready", extra={"repo": repo})
    while True:
        delay = seconds_until_next_tick(config)
        log.info("next tick in %.1f seconds", delay)
        time.sleep(delay)
        try:
            run_tick(client, config)
        except Exception:
            log.exception("tick failed")
