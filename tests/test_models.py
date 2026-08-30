"""Tests for Bus 57 parsing helpers."""

from __future__ import annotations

from datetime import date

from custom_components.bus_57_bovenstraat.models import (
    parse_passenger_stop_assignments,
    parse_timestamp,
)


def test_passenger_stop_assignment_accepts_datetime_dates() -> None:
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
    <root>
      <quay>
        <stopplacecode>NL:S:66420180</stopplacecode>
        <userstopcodes>
          <userstopcodedata>
            <dataownercode>ARR</dataownercode>
            <userstopcode>66420180</userstopcode>
            <validfrom>2016-12-11 00:00:00</validfrom>
          </userstopcodedata>
        </userstopcodes>
      </quay>
    </root>"""

    assert parse_passenger_stop_assignments(
        payload,
        data_owner="ARR",
        valid_on=date(2026, 8, 30),
    ) == {"66420180": "NL:S:66420180"}


def test_passenger_stop_assignment_respects_valid_thru() -> None:
    payload = b"""<root><quay>
      <stopplacecode>NL:S:123</stopplacecode>
      <userstopcodes><userstopcodedata>
        <dataownercode>ARR</dataownercode>
        <userstopcode>123</userstopcode>
        <validfrom>2020-01-01 00:00:00</validfrom>
        <validthru>2025-12-31 23:59:59</validthru>
      </userstopcodedata></userstopcodes>
    </quay></root>"""

    assert not parse_passenger_stop_assignments(
        payload,
        data_owner="ARR",
        valid_on=date(2026, 8, 30),
    )


def test_timestamp_with_long_fraction_is_supported() -> None:
    parsed = parse_timestamp("2026-08-30T09:30:00.123456789+02:00")
    assert parsed is not None
    assert parsed.microsecond == 123456
