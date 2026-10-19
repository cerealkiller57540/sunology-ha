"""Regressions reported on the public repo (sunology-tech/sunology-ha)."""
import json

from homeassistant.helpers import device_registry as dr, entity_registry as er

from .test_tap import get_dev, HUB_ID, PULSE_ID, TAP_ID, on_off, product_info, settle, setup


def _soc_entity(hass):
    return next(e for e in er.async_get(hass).entities.values()
                if e.unique_id.startswith("battery_soc") or "soc" in e.unique_id)


async def test_no_deprecated_via_device(hass, caplog):
    """#28 / PR #29: via_device stops working in HA 2027.8."""
    await setup(hass)
    assert "via_device` parameter" not in caplog.text
    devreg = dr.async_get(hass)
    hub = get_dev(hass, HUB_ID)
    tap = get_dev(hass, TAP_ID)
    assert tap.via_device_id == hub.id


async def test_entities_keep_their_platform_after_reload(hass, caplog):
    """#24 / #25: a new device reloads the platforms; updates must only reach live entities."""
    _, ctx = await setup(hass)
    # A second productInfo with one more accessory triggers _reload_platforms.
    info = product_info()
    info["data"]["devices"].append({
        "id": "A4C138FFFE000001", "comType": "Zigbee", "comTypeInt": 1, "model": 2,
        "productName": "STREAM_OUTLET", "manufacturerName": "Sunology", "parentId": HUB_ID})
    ctx.socket.process(json.dumps(info))
    await settle(hass, ctx)
    ctx.socket.process(json.dumps(on_off(TAP_ID, "LEGRAND_CONTACTOR", True, 3, power=10)))
    await settle(hass, ctx)
    assert "does not have a platform" not in caplog.text


async def test_just_paired_creates_the_device(hass):
    """justPaired carries the productInfo of the new accessory: no wait for the next productInfo."""
    _, ctx = await setup(hass)
    new_id = "B0C7DEFFFE000002"
    ctx.socket.process(json.dumps({"event": "justPaired", "data": {
        "id": new_id, "comType": "Zigbee", "comTypeInt": 1, "model": 15,
        "productName": "LEGRAND_CONTACTOR", "manufacturerName": "Sunology", "parentId": HUB_ID}}))
    await settle(hass, ctx)
    device = get_dev(hass, new_id)
    assert device is not None and device.model == "TAP"


async def test_remove_device_10(hass):
    """#10: a paired accessory can be deleted and does not come back with the next
    productInfo; pairing it again brings it back. The STREAM Connect itself cannot."""
    from custom_components.sunology import async_remove_config_entry_device
    entry, ctx = await setup(hass)
    devreg = dr.async_get(hass)

    pulse = get_dev(hass, PULSE_ID)
    assert await async_remove_config_entry_device(hass, entry, pulse) is True
    devreg.async_remove_device(pulse.id)
    await hass.async_block_till_done()
    assert PULSE_ID in entry.options["ignored_devices"]

    ctx.socket.process(json.dumps(product_info()))
    await settle(hass, ctx)
    assert get_dev(hass, PULSE_ID) is None
    assert all(d.device_id != PULSE_ID for d in ctx.sunology_devices)

    pulse_info = next(d for d in product_info()["data"]["devices"] if d["id"] == PULSE_ID)
    ctx.socket.process(json.dumps({"event": "justPaired", "data": pulse_info}))
    await settle(hass, ctx)
    assert get_dev(hass, PULSE_ID) is not None
    assert PULSE_ID not in entry.options["ignored_devices"]

    hub = get_dev(hass, HUB_ID)
    assert await async_remove_config_entry_device(hass, entry, hub) is False


async def test_battery_soc_has_state_class(hass):
    """#27: SOC needs state_class measurement for statistics and the Energy dashboard."""
    from unittest.mock import MagicMock
    from custom_components.sunology.sensor import SunologyBatterySocSensorEntity
    from homeassistant.components.sensor import SensorStateClass
    entity = SunologyBatterySocSensorEntity(MagicMock(device_id="1051DBAC068C"), hass)
    assert entity.state_class == SensorStateClass.MEASUREMENT
