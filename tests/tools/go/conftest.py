import random
import string

import pytest

from dda.utils.fs import Path

AVAILABLE_CHARS = string.ascii_letters + string.digits + "-_+.!@#$%^&*()[]{}:;,. "


@pytest.fixture
def get_random_filename():
    def _get_random_filename(k: int = 10, root: Path | None = None) -> Path:
        name = "".join(random.choices(AVAILABLE_CHARS, k=k))
        if root:
            return root / name
        return Path(name)

    return _get_random_filename
