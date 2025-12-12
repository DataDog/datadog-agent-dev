from base64 import urlsafe_b64encode
from os import urandom

import pytest


@pytest.fixture
def get_random_filename():
    def _get_random_filename(k: int = 10) -> str:
        return urlsafe_b64encode(urandom(k)).decode("utf-8")

    return _get_random_filename
