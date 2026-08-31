"""Constants for the Bus 57 Bovenstraat integration."""

from datetime import time, timedelta

DOMAIN = "bus_57_bovenstraat"
NAME = "Bus 57 Bovenstraat"

DATA_OWNER = "ARR"
LINE_PUBLIC_NUMBER = "57"
LINE_PLANNING_NUMBER = "26057"
DESTINATION = "Maastricht"
TARGET_STOP_NAME = "Bovenstraat"
TARGET_STOP_TOWN = "Noorbeek"

# The two gate entities are selected in the config/options flow and remain in
# the user's Home Assistant config entry; personal entity ids are never baked
# into the public integration repository.
CONF_PRESENCE_ENTITY = "presence_entity"
CONF_DAY_OFF_ENTITY = "day_off_entity"
ACTIVE_START_TIME = time(6, 0)
ACTIVE_END_TIME = time(10, 0)

JOURNEY_STATUS_NO_BUS = "no_bus"
JOURNEY_STATUS_WAITING = "waiting"
JOURNEY_STATUS_UNDERWAY = "underway"
JOURNEY_STATUS_REALTIME_UNAVAILABLE = "realtime_unavailable"
JOURNEY_STATUS_CANCELLED = "cancelled"
JOURNEY_STATUS_PREVIOUS_CANCELLED = "previous_cancelled"
JOURNEY_STATUS_OPTIONS = (
    JOURNEY_STATUS_NO_BUS,
    JOURNEY_STATUS_WAITING,
    JOURNEY_STATUS_UNDERWAY,
    JOURNEY_STATUS_REALTIME_UNAVAILABLE,
    JOURNEY_STATUS_CANCELLED,
    JOURNEY_STATUS_PREVIOUS_CANCELLED,
)

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

MAINTENANCE_INTERVAL = timedelta(minutes=1)
JOURNEY_DISCOVERY_INTERVAL = timedelta(minutes=5)
JOURNEY_REVALIDATE_INTERVAL = timedelta(minutes=5)
REQUEST_TIMEOUT_SECONDS = 15
NO_SHOW_GRACE_AFTER_TARGET = timedelta(minutes=45)
JOURNEY_WITHOUT_TIME_MAX_AGE = timedelta(hours=1)
PASSED_JOURNEY_REMEMBER = timedelta(minutes=30)
INVALID_JOURNEY_REMEMBER = timedelta(minutes=30)
REALTIME_STALE_AFTER = timedelta(minutes=5)
KV6_FRAME_TIMEOUT_SECONDS = 300
SOURCE_FUTURE_TOLERANCE = timedelta(minutes=5)
PSA_RETRY_INTERVAL = timedelta(minutes=5)
STOP_NAME_RETRY_INTERVAL = timedelta(minutes=5)
RECENT_KV6_EVENTS = 300

# The user explicitly wants an apparent lead of >10 minutes rejected. This is
# also a useful final sanity guard after filtering server-generated KV6 data.
MAX_EARLY_SECONDS = 10 * 60

# Avoid duplicating the manifest version in runtime code.
USER_AGENT = "HomeAssistant-Bus57Bovenstraat"
