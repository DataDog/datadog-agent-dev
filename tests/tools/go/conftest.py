from base64 import urlsafe_b64encode
from os import urandom

import pytest

from dda.utils.fs import Path


@pytest.fixture
def get_random_filename():
    def _get_random_filename(k: int = 10, root: Path | None = None) -> Path:
        return (root or Path()).joinpath(urlsafe_b64encode(urandom(k)).decode("utf-8"))

    return _get_random_filename
