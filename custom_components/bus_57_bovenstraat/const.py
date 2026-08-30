"""Constants for the Bus 57 Bovenstraat integration."""

from datetime import timedelta

DOMAIN = "bus_57_bovenstraat"
NAME = "Bus 57 Bovenstraat"

DATA_OWNER = "ARR"
LINE_PUBLIC_NUMBER = "57"
LINE_PLANNING_NUMBER = "26057"
DESTINATION = "Maastricht"
TARGET_STOP_NAME = "Bovenstraat"
TARGET_STOP_TOWN = "Noorbeek"

# DRGL is used only for selecting the concrete public journey and for resolving
# a *public* CHB StopPlaceCode to a readable stop name.
DRGL_BASE_URL = "https://drgl.nl"
TARGET_STOP_PLACE_CODE = "NL:S:66420180"
DRGL_TARGET_STOP_AREA = TARGET_STOP_PLACE_CODE

# Official Passenger Stop Assignment (PSA): maps the operator-domain
# UserStopCode found in KV6 to the national CHB StopPlaceCode.
NDOV_HALTES_BASE_URL = "https://data.ndovloket.nl/haltes"
PSA_INDEX_URL = f"{NDOV_HALTES_BASE_URL}/"
PSA_FILENAME_PREFIX = "PassengerStopAssignmentExportCHB_"

KV6_ENDPOINT = "tcp://pubsub.besteffort.ndovloket.nl:7658"
KV6_ENVELOPE = "/ARR/KV6posinfo"

# Source=VEHICLE is the BISON indication that the underlying source is the
# physical vehicle rather than a server-generated record.
TRUSTED_KV6_SOURCE = "VEHICLE"

UPDATE_INTERVAL = timedelta(seconds=30)
REQUEST_TIMEOUT_SECONDS = 15
ACTIVE_JOURNEY_MAX_AGE = timedelta(hours=2)
PASSED_JOURNEY_REMEMBER = timedelta(minutes=30)
INVALID_JOURNEY_REMEMBER = timedelta(minutes=30)
REALTIME_STALE_AFTER = timedelta(minutes=2)
PSA_RETRY_INTERVAL = timedelta(minutes=5)
RECENT_KV6_EVENTS = 300

# The user explicitly wants an apparent lead of >10 minutes rejected. This is
# also a useful final sanity guard after filtering server-generated KV6 data.
MAX_EARLY_SECONDS = 10 * 60

USER_AGENT = "HomeAssistant-Bus57Bovenstraat/0.4.1"
