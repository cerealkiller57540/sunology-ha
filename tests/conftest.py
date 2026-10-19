"""Fixtures for the Sunology integration tests."""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load custom_components/sunology."""
    yield


@pytest.fixture(autouse=True)
def no_hub_connection():
    """Never open a real WebSocket: the tests push the hub frames themselves."""
    with patch(
        "custom_components.sunology.SunologySocket.connect", new=AsyncMock()
    ), patch(
        "custom_components.sunology.SunologySocket.send_hub_command", new=AsyncMock()
    ) as send:
        yield send


@pytest.fixture(autouse=True)
def no_zeroconf_dependency():
    """The manifest depends on zeroconf, which needs a network stack in tests."""
    with patch(
        "homeassistant.loader.Integration.dependencies",
        new_callable=lambda: property(lambda self: [] if self.domain == "sunology" else self.manifest.get("dependencies", [])),
    ):
        yield
