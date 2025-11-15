import random
import string

import pytest

from dda.utils.fs import Path

AVAILABLE_CHARS = string.ascii_letters + string.digits + "-_+.!@#$%^&*()[]{}:;,. "


@pytest.fixture
def get_random_filename():
    def _get_random_filename(k: int = 10, root: Path | None = None) -> Path:
        name = "".join(random.choices(AVAILABLE_CHARS, k=k))
        # Remove the leading `-` to avoid considering it as a command flag
        path = Path(name.removeprefix("-"))
        if root:
            return root / path
        return path

    return _get_random_filename
