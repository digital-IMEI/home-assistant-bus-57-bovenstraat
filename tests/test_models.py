"""Tests for Bus 57 parsing helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime

from custom_components.bus_57_bovenstraat.models import (
    AMSTERDAM,
    parse_drgl_departures,
    parse_kv6_xml,
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


def test_kv6_parser_filters_before_creating_events() -> None:
    received_at = datetime(2026, 8, 30, 6, 5, tzinfo=UTC)
    payload = b"""<VV_TM_PUSH>
      <ONROUTE>
        <dataownercode>ARR</dataownercode>
        <lineplanningnumber>26057</lineplanningnumber>
        <operatingday>2026-08-30</operatingday>
        <journeynumber>1234</journeynumber>
        <reinforcementnumber>0</reinforcementnumber>
        <userstopcode>66420180</userstopcode>
        <timestamp>2026-08-30T08:04:58+02:00</timestamp>
        <source>VEHICLE</source>
        <punctuality>-72</punctuality>
        <vehiclenumber>42</vehiclenumber>
      </ONROUTE>
      <ONROUTE>
        <dataownercode>ARR</dataownercode>
        <lineplanningnumber>26056</lineplanningnumber>
        <journeynumber>9999</journeynumber>
      </ONROUTE>
      <ONROUTE>
        <dataownercode>OTHER</dataownercode>
        <lineplanningnumber>26057</lineplanningnumber>
        <journeynumber>9998</journeynumber>
      </ONROUTE>
    </VV_TM_PUSH>"""

    events = parse_kv6_xml(
        payload,
        data_owner="ARR",
        line_planning_number="26057",
        received_at=received_at,
    )

    assert len(events) == 1
    assert events[0].journey_number == 1234
    assert events[0].punctuality == -72
    assert events[0].received_at == received_at


def test_drgl_departures_are_sorted_and_accept_attribute_order() -> None:
    html = """
    <a class='journey' data-extra='yes'
       href='/journey/ARR:26057:200/20260830/'>
      <div class='ott-destination'>Maastricht</div>
      <div class='other ott-linecode'>57</div>
      <div class='ott-departure-time expected'>08:30</div>
    </a>
    <a data-extra='yes' href='/journey/ARR:26057:100/20260830/'>
      <div class='ott-destination'>Maastricht via Gulpen</div>
      <div class='ott-linecode'>57</div>
      <div class='ott-departure-time'>07:30</div>
    </a>
    <a href='/journey/ARR:26057:50/20260830/'>
      <div class='ott-destination'>Maastricht</div>
      <div class='ott-linecode'>57</div>
      <div class='ott-departure-time'>07:00</div>
      <span>Vervallen</span>
    </a>
    """

    journeys = parse_drgl_departures(html)

    assert [journey.journey_number for journey in journeys] == [50, 100, 200]
    assert journeys[0].cancelled
    assert not journeys[1].cancelled
    assert journeys[1].scheduled_bovenstraat == datetime(2026, 8, 30, 7, 30, tzinfo=AMSTERDAM)


def test_drgl_cancellation_marker_in_css_is_retained() -> None:
    html = """
    <a class='journey cancelled' href='/journey/ARR:26057:75/20260830/'>
      <div class='ott-destination'>Maastricht</div>
      <div class='ott-linecode'>57</div>
      <div class='ott-departure-time'>07:15</div>
    </a>
    """

    journeys = parse_drgl_departures(html)

    assert len(journeys) == 1
    assert journeys[0].journey_number == 75
    assert journeys[0].cancelled
