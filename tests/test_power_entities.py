"""Power entities: the reversed one is the default (Home Assistant sign convention)."""
from homeassistant.helpers import entity_registry as er

from custom_components.sunology.const import DOMAIN

from .test_tap import TAP_ID, setup


async def test_reversed_power_enabled_normal_disabled(hass):
    """Since 1.2.1 the reversed entity (production positive, as Home Assistant expects)
    is enabled and the normal one (Sunology sign convention) disabled. Intended:
    do not "fix" it, existing Energy dashboards use the reversed entities."""
    await setup(hass)
    registry = er.async_get(hass)
    tid = TAP_ID.lower()
    normal = registry.async_get_entity_id("sensor", DOMAIN, f"power_all_{tid}")
    reversed_ = registry.async_get_entity_id("sensor", DOMAIN, f"power_all_reversed_{tid}")
    assert registry.async_get(reversed_).disabled_by is None
    assert registry.async_get(normal).disabled_by is er.RegistryEntryDisabler.INTEGRATION
