# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from dda.utils.date import parse_imf_date


class TestParseImfDate:
    def test_standard(self):
        assert parse_imf_date("Sun, 06 Nov 1994 08:49:37 GMT") == datetime(1994, 11, 6, 8, 49, 37, tzinfo=UTC)

    def test_standard_with_timezone_offset(self):
        assert parse_imf_date("Sun, 06 Nov 1994 08:49:37 +0100") == datetime(
            1994, 11, 6, 8, 49, 37, tzinfo=timezone(timedelta(hours=1))
        )

    def test_standard_with_timezone_offset_and_name(self):
        assert parse_imf_date("Sun, 06 Nov 1994 08:49:37 +0100 (Europe/Paris)") == datetime(
            1994, 11, 6, 8, 49, 37, tzinfo=timezone(timedelta(hours=1))
        )

    def test_obsolete_usenet_format(self):
        assert parse_imf_date("Sunday, 06-Nov-94 08:49:37 GMT") == datetime(1994, 11, 6, 8, 49, 37, tzinfo=UTC)

    def test_obsolete_asctime_format(self):
        assert parse_imf_date("Sun Nov  6 08:49:37 1994") == datetime(1994, 11, 6, 8, 49, 37)  # noqa: DTZ001
