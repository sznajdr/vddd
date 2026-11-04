import pytest

from tripstate.config import load_default


@pytest.fixture(scope="session")
def ts():
    return load_default()
