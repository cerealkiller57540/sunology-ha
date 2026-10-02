""" Sunology const file """
from enum import IntEnum, StrEnum

DOMAIN = "sunology"

CONF_GATEWAY_HOST = "lan_gateway_host"
CONF_GATEWAY_PORT = "lan_gateway_port"

GATEWAY_DEFAULT_PORT = 20199

MIN_UNTIL_REFRESH = 2

# Config entry option: Sunology ids the user deleted from Home Assistant. The hub keeps
# listing a paired accessory even once it is gone, so without this the device would come
# back on the next productInfo (#10). A new pairing (justPaired) takes it off the list.
CONF_IGNORED_DEVICES = "ignored_devices"

# Reconnection backoff to the STREAM Connect, in seconds: first retry immediate,
# then RECONNECT_BACKOFF_BASE doubled on each failed attempt, capped.
RECONNECT_BACKOFF_BASE = 5
RECONNECT_BACKOFF_MAX = 300

PACKAGE_NAME = f"custom_components.{DOMAIN}"


class SmartMeterPhase(StrEnum):
    """Phase of a smart meter."""
    ALL = "All"
    PHASE_1 = "P1"
    PHASE_2 = "P2"
    PHASE_3 = "P3"

class SmartMeterTarifIndex(StrEnum):
    """Phase of a smart meter."""
    INDEX_1 = "idx1"
    INDEX_2 = "idx2"
    INDEX_3 = "idx3"
    INDEX_4 = "idx4"
    INDEX_5 = "idx5"
    INDEX_6 = "idx6"
    INDEX_7 = "idx7"
    INDEX_8 = "idx8"
    INDEX_9 = "idx9"
    INDEX_10 = "idx10"

class ElectricalDataFeature(StrEnum):
    """Phase of a smart meter."""
    UNUSED = "UNUSED"
    PRODUCER = "PRODUCER"
    LOAD = "LOAD"
    GRID = "GRID"
    PRODUCER_REV = "PRODUCER_REV"
    LOAD_REV = "LOAD_REV"
    GRID_REV = "GRID_REV"

class FlowWorkingModes(StrEnum):
    """Phase of a smart meter."""
    COST_OPTIM = "COST_OPTIM"
    POWER_OPTIM = "POWER_OPTIM"

class FeatureFlowNodeModes(StrEnum):
    """Phase of a smart meter."""
    FLOW = "FLOW"
    FORCED_ON = "FORCED_ON"
    FORCED_OFF = "FORCED_OFF"

class ContactorStatus(StrEnum):
    """User-facing TAP status, aligned on the STREAM app.

    Mirrors web/apps/mobile mapContactorModeCodeToContactorMode + mapContactorModeToStatus:
    the LAN WebSocket carries the raw contactorMode code only, so the app tells
    FLOW_AUTO_ON from FLOW_AUTO_OFF with the relay state of the same event.
    """
    ACTIVE = "active"        # driven by the hub, relay closed
    IDLE = "idle"            # driven by the hub, relay open
    FORCED_ON = "forced_on"  # relay held closed on the client's request
    UNKNOWN = "unknown"      # any other code (0 OFF, 1 MANUAL): the app shows it unknown

class ContactorMode(IntEnum):
    """Mode reported by a Legrand contactor (TAP)."""
    OFF = 0
    MANUAL = 1
    AUTO = 2
    ON = 3