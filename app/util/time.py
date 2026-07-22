from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def parse_github_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seconds_old(value: str, now: datetime | None = None) -> float:
    return ((now or utc_now()) - parse_github_time(value)).total_seconds()
