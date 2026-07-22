from datetime import datetime

from app.main import seconds_until_next_tick


def test_default_scheduler_aligns_to_quarter_hour(config):
    now = datetime.fromisoformat("2026-01-01T10:07:30+01:00")
    assert seconds_until_next_tick(config, now) == 450


def test_short_test_interval_is_used_directly(config):
    config = type(config)(**{**config.__dict__, "poll_interval": 3})
    assert seconds_until_next_tick(config) == 3
