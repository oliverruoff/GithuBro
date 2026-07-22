from app.util.slug import branch_name, issue_slug


def test_slug_normalizes_ascii_and_separators():
    assert issue_slug("  Héllo, Big WORLD!!! ") == "hello-big-world"


def test_slug_is_trimmed_to_40_without_trailing_dash():
    value = issue_slug("word " * 20)
    assert len(value) <= 40
    assert not value.endswith("-")


def test_empty_slug_has_stable_fallback():
    assert branch_name(7, "🎉") == "agent/7-issue"
