# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import sys

from deva.utils.process import EnvVars


def get_random_name():
    return os.urandom(16).hex().upper()


class TestEnvVars:
    def test_restoration(self):
        num_env_vars = len(os.environ)
        with EnvVars():
            os.environ.clear()

        assert len(os.environ) == num_env_vars

    def test_set(self):
        env_var = get_random_name()

        with EnvVars({env_var: "foo"}):
            assert os.environ.get(env_var) == "foo"

        assert env_var not in os.environ

    def test_include(self):
        env_var = get_random_name()
        pattern = f"{env_var[:-2]}*"

        with EnvVars({env_var: "foo"}):
            num_env_vars = len(os.environ)

            with EnvVars(include=[get_random_name(), pattern]):
                assert len(os.environ) == 1
                assert os.environ.get(env_var) == "foo"

            assert len(os.environ) == num_env_vars

    def test_exclude(self):
        env_var = get_random_name()
        pattern = f"{env_var[:-2]}*"

        with EnvVars({env_var: "foo"}):
            with EnvVars(exclude=[get_random_name(), pattern]):
                assert env_var not in os.environ

            assert os.environ.get(env_var) == "foo"

    def test_precedence(self):
        env_var1 = get_random_name()
        env_var2 = get_random_name()
        pattern = f"{env_var1[:-2]}*"

        with EnvVars({env_var1: "foo"}):
            num_env_vars = len(os.environ)

            with EnvVars({env_var2: "bar"}, include=[pattern], exclude=[pattern, env_var2]):
                assert len(os.environ) == 1
                assert os.environ.get(env_var2) == "bar"

            assert len(os.environ) == num_env_vars


class TestSubprocessRunner:
    def test_run(self, app, tmp_path):
        script = f"""\
from pathlib import Path

f = Path({str(tmp_path)!r}, "output.txt")
f.write_text("foo")
"""
        output_file = tmp_path / "output.txt"
        assert not output_file.exists()

        app.subprocess.run([sys.executable, "-c", script])
        assert output_file.is_file()
        assert output_file.read_text() == "foo"

    def test_capture_cross_streams(self, app):
        script = """\
import sys

print("foo", file=sys.stdout, flush=True, end="")
print("bar", file=sys.stderr, flush=True, end="")
print("baz", file=sys.stdout, flush=True, end="")
"""
        output = app.subprocess.capture([sys.executable, "-c", script])
        assert output == "foobarbaz"

    def test_capture_separate_streams(self, app):
        script = """\
import sys

print("foo", file=sys.stdout, flush=True, end="")
print("bar", file=sys.stderr, flush=True, end="")
print("baz", file=sys.stdout, flush=True, end="")
"""
        output = app.subprocess.capture([sys.executable, "-c", script], cross_streams=False)
        assert output == "foobaz"

    def test_capture_no_encoding(self, app):
        script = """\
import sys

print("foo", file=sys.stdout, flush=True, end="")
print("bar", file=sys.stderr, flush=True, end="")
print("baz", file=sys.stdout, flush=True, end="")
"""
        output = app.subprocess.capture([sys.executable, "-c", script], encoding=None)
        assert output == b"foobarbaz"
