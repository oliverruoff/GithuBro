import pytest

from app.config import Config


@pytest.fixture
def config():
    return Config(github_pat="secret", repos=("owner/repo",), username="alice")
