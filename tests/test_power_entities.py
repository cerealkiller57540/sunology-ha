"""Power entities: normal enabled, reversed disabled (regression from 1.2.1 to 1.4.0)."""
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunology.const import CONF_GATEWAY_HOST, CONF_GATEWAY_PORT, DOMAIN

from .test_tap import TAP_ID, setup


async def test_power_enabled_reversed_disabled(hass):
    """The normal power entity is enabled by default, the reversed one disabled
    (1.2.1 to 1.4.0 did the opposite)."""
    await setup(hass)
    registry = er.async_get(hass)
    tid = TAP_ID.lower()
    normal = registry.async_get_entity_id("sensor", DOMAIN, f"power_all_{tid}")
    reversed_ = registry.async_get_entity_id("sensor", DOMAIN, f"power_all_reversed_{tid}")
    assert registry.async_get(normal).disabled_by is None
    assert registry.async_get(reversed_).disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_power_entities_wrongly_disabled_are_enabled_again(hass):
    """Existing installs: the power entity disabled by the integration is enabled
    again at startup; one disabled by the user stays disabled."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_GATEWAY_HOST: "192.168.1.20",
                                                 CONF_GATEWAY_PORT: 20199})
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    by_integration = registry.async_get_or_create(
        "sensor", DOMAIN, "power_all_b0c7defffe5eccb1", config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION)
    by_user = registry.async_get_or_create(
        "sensor", DOMAIN, "power_p1_a4c138fffe12ab34", config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER)
    reversed_ = registry.async_get_or_create(
        "sensor", DOMAIN, "power_all_reversed_b0c7defffe5eccb1", config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert registry.async_get(by_integration.entity_id).disabled_by is None
    assert registry.async_get(by_user.entity_id).disabled_by is er.RegistryEntryDisabler.USER
    assert registry.async_get(reversed_.entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
