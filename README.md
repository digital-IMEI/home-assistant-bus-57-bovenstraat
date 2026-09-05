# Bus 57 Bovenstraat

Home Assistant custom integration for **Arriva bus 57 towards Maastricht**, tracked up to **Bovenstraat in Noorbeek**.

## Sensors

- **Actuele vertraging** — signed realtime punctuality as a Home Assistant duration sensor in seconds
- **Buspositie** — the stop where the bus is standing, otherwise the last passed stop
- **Ritstatus** — waiting, underway, no bus, cancelled journey or unavailable realtime data
- **Volgende passage Bovenstraat** — next scheduled passage time at Bovenstraat

The next Bovenstraat time is visible as soon as a journey is found, including
before departure. Realtime delay is exposed only after a trusted vehicle-origin
`DEPARTURE` or `ONROUTE` event proves that the trip has started. Waiting at the
origin therefore cannot create a false early-running value. Trips reported more
than ten minutes early after departure are ignored.

| Situation | Buspositie | Ritstatus | Delay |
| --- | --- | --- | --- |
| Bus is standing at a stop | Current stop | Underway (or waiting at the origin) | Available only after departure |
| Bus is between stops | Last passed stop | Underway | Available |
| Realtime data becomes stale | Last known position | Realtime temporarily unavailable | Unavailable |
| Selected journey is cancelled or never appears | Last known position, otherwise no bus underway | Journey cancelled | Unavailable |
| A following journey is already selected | Not yet departed | Previous journey cancelled | Unavailable |
| No journey is available | No bus underway | No bus underway | Unavailable |

## Lightweight morning runtime

The integration runs only when all four conditions are true:

| Condition | Required value |
| --- | --- |
| Local weekday | Monday through Friday |
| Local time | From 06:00 up to, but not including, 10:00 |
| Selected presence entity | `home` |
| Selected day-off binary sensor | `off` |

Outside those conditions all sensors are unavailable and the integration closes
its ZeroMQ connection, cancels HTTP work, stops XML parsing and disables its
maintenance timer. Leaving home stops it immediately. Returning before 10:00
starts it again.

Both entities are selected privately in the Home Assistant setup screen and can
be changed later with **Settings → Devices & services → Bus 57 Bovenstraat →
Configure**. Their entity ids are not part of this public repository.

While active, there is one push connection. A cheap local maintenance check runs
once per minute. Journey discovery/revalidation uses one small HTTP request at
most every five minutes while waiting for a trip; it stops during an active trip.
The official stop mapping is downloaded at most once per active calendar day,
and stop names are resolved only when needed.

## Installation with HACS

1. In HACS, open **Integrations**.
2. Open the menu and choose **Custom repositories**.
3. Add `https://github.com/digital-IMEI/home-assistant-bus-57-bovenstraat` as category **Integration**.
4. Install **Bus 57 Bovenstraat**.
5. Restart Home Assistant.
6. Open **Settings → Devices & services → Add integration** and add **Bus 57 Bovenstraat**.
7. Select your presence entity and your day-off binary sensor.

Existing installations upgrading from an earlier version must use **Configure**
once to select those two entities. Until then the integration remains fully
asleep and performs no network work.

The integration requires Home Assistant **2026.8.2 or newer**.

## Data sources

- Arriva KV6 realtime messages from the public NDOV ZeroMQ stream
- NDOV PassengerStopAssignment for translating Arriva stop codes
- DRGL for the selected journey and human-readable stop names

The integration is fixed to line 57 towards Maastricht and Bovenstraat, Noorbeek; there are no route settings or credentials.

## Version 0.5.2

- Restricts the lightweight runtime to Monday through Friday. On Saturday and
  Sunday all sensors remain unavailable and no transport network processing is
  started.

## Version 0.5.1

- Exposes the scheduled Bovenstraat passage of the most recently cancelled journey as `cancelled_scheduled_time` on **Ritstatus**.
- Keeps the cancelled journey time separate from the scheduled time of the following journey, so dashboards never have to infer it.

## Version 0.5.0

- Adds the strict 06:00–10:00, home and workday runtime gate described above.
- Makes both gate entities configurable in the Home Assistant UI.
- Keeps **Volgende passage Bovenstraat** visible before the journey starts.
- Starts delay reporting only on real trip progress and reports it as seconds.
- Shows the current stop while the bus is standing there and otherwise keeps the last passed stop.
- Adds **Ritstatus** and distinguishes a cancelled/no-show journey from a temporary realtime outage.
- Retains the last known bus position during a realtime outage and reconnects automatically.
- Filters unrelated KV6 events during streaming XML parsing to reduce memory and CPU use.
- Reconnects a silent realtime stream and bases freshness on local receipt time.
- Handles cancelled, disappeared, prematurely ended and no-show journeys without blocking the next candidate.
- Retains working stop mappings during an outage and retries failed stop-name lookups.
- Adds richer diagnostics and automated validation before publishing a release.

## Version 0.4.3

- Exposes **Actuele vertraging** as a proper Home Assistant duration/measurement sensor in seconds, with zero decimal places.

## Version 0.4.2

- Starts showing realtime delay only after a `DEPARTURE` or `ONROUTE` event, so waiting at the origin does not create an artificial early-running value.
- Shows **Geen bus onderweg** for **Laatst gepasseerde halte** instead of `unknown` or `unavailable` outside an active trip.

## Version 0.4.1

- Adds explicit logo assets in addition to the integration icons for HACS and Home Assistant.

## Version 0.4.0

- Fixes PassengerStopAssignment dates containing a time component. Previously this rejected all current Arriva stop mappings and left **Laatst gepasseerde halte** empty.
- Uses complete national stop identifiers such as `NL:S:66420180` without adding a duplicate prefix.
- Recovers the last known stop from trusted `ONROUTE` messages after a restart or reconnect.
- Prevents older out-of-order KV6 messages from rolling the stop back.
- Adds HACS metadata and the official Arriva logo.

This project is an independent Home Assistant integration and is not affiliated with Arriva, NDOV or DRGL. Arriva is a trademark of its respective owner.
