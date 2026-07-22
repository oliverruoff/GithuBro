from app.runner.llm import reasoning_args


def test_reasoning_args_are_provider_specific():
    assert reasoning_args(["--model", "openai/gpt-5"], "high") == ["--reasoning-effort", "high"]
    assert reasoning_args(["--model", "anthropic/claude-opus"], "high") == ["--thinking", "max"]


def test_explicit_reasoning_flag_is_not_duplicated():
    assert reasoning_args(["--model", "openai/gpt-5", "--reasoning-effort", "low"], "high") == []
