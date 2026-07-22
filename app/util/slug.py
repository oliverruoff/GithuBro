import re
import unicodedata


def issue_slug(title: str, max_length: int = 40) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")[:max_length].rstrip("-")
    return slug or "issue"


def branch_name(number: int, title: str) -> str:
    return f"agent/{number}-{issue_slug(title)}"
