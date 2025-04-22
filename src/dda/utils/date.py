# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def parse_imf_date(data: str) -> datetime:
    """
    Parse a date value using the Internet Message Format (IMF) as defined by
    [RFC 5322](https://datatracker.ietf.org/doc/html/rfc5322#section-3.3).

    This is the date format used by the HTTP and email specifications, among others.

    Parameters:
        data: The date value to parse.

    Returns:
        A [`datetime`][datetime.datetime] object representing the parsed date.

    Raises:
        ValueError: If the date value is not valid.
    """
    # This function strives to copy the behavior of the `email.utils.parsedate_to_datetime`
    # function but avoid the costly import of the `email.utils` module.
    #
    # https://docs.python.org/3/library/email.utils.html#email.utils.parsedate_to_datetime
    # https://github.com/python/cpython/blob/3.13/Lib/email/utils.py#L315
    from email._parseaddr import _parsedate_tz  # noqa: PLC2701

    parsed_date_tz = _parsedate_tz(data)
    if parsed_date_tz is None:
        message = f"Invalid date value or format {data!r}"
        raise ValueError(message)

    *dtuple, tz = parsed_date_tz
    if tz is None:
        return datetime(*dtuple[:6])  # noqa: DTZ001

    return datetime(*dtuple[:6], tzinfo=timezone(timedelta(seconds=tz)))  # type: ignore[misc]
