# Bus 57 Bovenstraat

Home Assistant custom integration for **Arriva bus 57 towards Maastricht**, tracked up to **Bovenstraat in Noorbeek**.

## Sensors

- **Actuele vertraging** — realtime punctuality in minutes
- **Laatst gepasseerde halte** — most recently departed/passed stop
- **Geplande passage Bovenstraat** — scheduled passage time at Bovenstraat

Values are available only while a trusted vehicle-origin KV6 event confirms that the selected bus is underway. Trips reported more than ten minutes early are ignored.

## Installation with HACS

1. In HACS, open **Integrations**.
2. Open the menu and choose **Custom repositories**.
3. Add `https://github.com/digital-IMEI/home-assistant-bus-57-bovenstraat` as category **Integration**.
4. Install **Bus 57 Bovenstraat**.
5. Restart Home Assistant.
6. Open **Settings → Devices & services → Add integration** and add **Bus 57 Bovenstraat**.

The integration requires Home Assistant **2026.8.2 or newer**.

## Data sources

- Arriva KV6 realtime messages from the public NDOV ZeroMQ stream
- NDOV PassengerStopAssignment for translating Arriva stop codes
- DRGL for the selected journey and human-readable stop names

The integration is fixed to line 57 towards Maastricht and Bovenstraat, Noorbeek; there are no route settings or credentials.

## Version 0.4.1

- Adds explicit logo assets in addition to the integration icons for HACS and Home Assistant.

## Version 0.4.0

- Fixes PassengerStopAssignment dates containing a time component. Previously this rejected all current Arriva stop mappings and left **Laatst gepasseerde halte** empty.
- Uses complete national stop identifiers such as `NL:S:66420180` without adding a duplicate prefix.
- Recovers the last known stop from trusted `ONROUTE` messages after a restart or reconnect.
- Prevents older out-of-order KV6 messages from rolling the stop back.
- Adds HACS metadata and the official Arriva logo.

This project is an independent Home Assistant integration and is not affiliated with Arriva, NDOV or DRGL. Arriva is a trademark of its respective owner.
