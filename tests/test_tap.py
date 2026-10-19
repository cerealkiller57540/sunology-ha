"""Sunology TAP (LEGRAND_CONTACTOR) support, exercised inside a real Home Assistant.

Frames follow what fw-sconnect HB2026W39.1RC emits (Device::attributesToCJson,
Device::getFeatures, FlowNode::to_json) and the STREAM HUBMock samples.
"""
import asyncio
import json

from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunology.const import (
    CONF_GATEWAY_HOST,
    CONF_GATEWAY_PORT,
    DOMAIN,
)

HUB_ID = "28372FE823C8"
TAP_ID = "B0C7DEFFFE5ECCB1"
PULSE_ID = "A4C138FFFE12AB34"

FLOW_NODE = {
    "enabled": True, "mode": "FLOW", "priority": "HIGH", "type": "CONSTANT_CONSUMER",
    "autoCalib": False, "efficiency": 100, "dailyRuntimeEn": True,
    "runtimeMin": 120, "runtimeMax": 1440, "dailyEnergyEn": False,
    "energyMin": 0, "energyMax": 0, "minOnTime": 1800,
    "minCons": 0, "maxCons": 2100, "minProd": 0, "maxProd": 0,
}


def product_info():
    return {"event": "productInfo", "data": {
        "id": HUB_ID, "comType": "Cloud", "comTypeInt": 3, "model": 14,
        "productName": "STREAM_CONNECT", "manufacturerName": "Sunology",
        "rssiWifi": -53, "zbPairingActivated": False,
        "fwVersion": "HB2026W39.1", "hwVersion": "0.0.0",
        "devices": [
            {"id": TAP_ID, "comType": "Zigbee", "comTypeInt": 1, "model": 15,
             "productName": "LEGRAND_CONTACTOR", "manufacturerName": "Sunology",
             "parentId": HUB_ID, "rssi": -70, "hwVersion": "0.0.1", "fwVersion": "0.0.2",
             "features": {"flowNode": FLOW_NODE, "electricalData": "PRODUCTION"}},
            {"id": PULSE_ID, "comType": "Zigbee", "comTypeInt": 1, "model": 2,
             "productName": "STREAM_OUTLET", "manufacturerName": "Sunology",
             "parentId": HUB_ID, "rssi": -60,
             "features": {"flowNode": dict(FLOW_NODE, maxCons=0)}},
        ],
    }}


def on_off(dev_id, product, on, mode=None, **electrical):
    data = {"id": dev_id, "productName": product, "manufacturerName": "Sunology",
            "parentId": HUB_ID, "rssi": -70, "comType": 1, "onOff": on,
            "runtimeOn": 42, "targetPower": 2100 if on else 0,
            "electricalData": electrical}
    if mode is not None:
        data["contactorMode"] = mode
    return {"event": "onOffEvent", "data": data}


async def setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_GATEWAY_HOST: "192.168.1.20",
                                                 CONF_GATEWAY_PORT: 20199})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ctx = entry.runtime_data
    ctx.socket.process(json.dumps(product_info()))
    await settle(hass, ctx)
    return entry, ctx


async def settle(hass, ctx):
    """Wait for the platform reloads the integration schedules with
    run_coroutine_threadsafe: HA's async_block_till_done does not track them."""
    for _ in range(5):
        await hass.async_block_till_done()
        pending = [asyncio.wrap_future(f) for f in ctx._coroutines_future if not f.done()]
        if not pending:
            return
        await asyncio.wait(pending, timeout=5)
    await hass.async_block_till_done()


def get_dev(hass, dev_id):
    """Sunology device of the (single) test entry, on any HA version."""
    devreg = dr.async_get(hass)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    if hasattr(devreg, "async_get_device_by_identifier"):
        return devreg.async_get_device_by_identifier((DOMAIN, dev_id), entry.entry_id)
    return devreg.async_get_device(identifiers={(DOMAIN, dev_id)})


def entities_of(hass, dev_id):
    devreg, entreg = dr.async_get(hass), er.async_get(hass)
    device = get_dev(hass, dev_id)
    assert device is not None, f"device {dev_id} not registered"
    return device, {e.unique_id: e for e in er.async_entries_for_device(entreg, device.id)}


def state(hass, entities, unique_id):
    return hass.states.get(entities[unique_id].entity_id)


async def test_tap_device_and_entities(hass):
    _, _ = await setup(hass)
    device, ents = entities_of(hass, TAP_ID)
    tid = TAP_ID.lower()

    assert device.model == "TAP"
    assert device.manufacturer == "Legrand"

    expected = {
        f"relaystate_{tid}", f"contactor_mode_{tid}",
        f"flownodemode_{tid}", f"runtime_on_{tid}", f"target_power_{tid}",
        f"min_on_time_{tid}", f"runtime_min_{tid}", f"max_cons_{tid}",
        f"contactor_status_{tid}",
    }
    assert expected <= set(ents), sorted(ents)
    # No METERING cluster on the TAP: an energy counter would stay unknown forever.
    assert not any(u.startswith("total") or "import" in u for u in ents), sorted(ents)

    select = state(hass, ents, f"flownodemode_{tid}")
    assert select.attributes["options"] == ["FLOW", "FORCED_ON"]
    assert select.state == "FLOW"

    assert state(hass, ents, f"min_on_time_{tid}").state == "1800"
    assert state(hass, ents, f"runtime_min_{tid}").state == "120"
    assert state(hass, ents, f"max_cons_{tid}").state == "2100"

    # User-facing status is a primary entity, the raw firmware mode a diagnostic one.
    assert ents[f"contactor_status_{tid}"].entity_category is None
    assert ents[f"contactor_mode_{tid}"].entity_category == "diagnostic"


async def test_tap_on_off_event(hass):
    _, ctx = await setup(hass)
    _, ents = entities_of(hass, TAP_ID)
    tid = TAP_ID.lower()

    ctx.socket.process(json.dumps(on_off(TAP_ID, "LEGRAND_CONTACTOR", True, 3,
                                         power=1450, apparentPower=1490)))
    await settle(hass, ctx)

    assert state(hass, ents, f"relaystate_{tid}").state == "on"
    assert state(hass, ents, f"contactor_mode_{tid}").state == "ON"
    status = state(hass, ents, f"contactor_status_{tid}")
    assert status.state == "forced_on"
    assert status.attributes["contactor_mode_code"] == 3
    assert status.attributes["relay_on"] is True
    assert state(hass, ents, f"runtime_on_{tid}").state == "42"
    assert state(hass, ents, f"target_power_{tid}").state == "2100"

    # MANUAL (1) is a firmware value the AsyncAPI spec forgot: must decode, not crash.
    ctx.socket.process(json.dumps(on_off(TAP_ID, "LEGRAND_CONTACTOR", False, 1, power=0)))
    await settle(hass, ctx)
    assert state(hass, ents, f"relaystate_{tid}").state == "off"
    assert state(hass, ents, f"contactor_mode_{tid}").state == "MANUAL"
    # Same as the STREAM app: codes other than AUTO / ON have no status.
    assert state(hass, ents, f"contactor_status_{tid}").state == "unknown"

    # AUTO: the relay state tells ACTIVE from IDLE, as mapContactorModeCodeToContactorMode does.
    ctx.socket.process(json.dumps(on_off(TAP_ID, "LEGRAND_CONTACTOR", True, 2, power=2000)))
    await settle(hass, ctx)
    assert state(hass, ents, f"contactor_status_{tid}").state == "active"
    ctx.socket.process(json.dumps(on_off(TAP_ID, "LEGRAND_CONTACTOR", False, 2, power=0)))
    await settle(hass, ctx)
    assert state(hass, ents, f"contactor_status_{tid}").state == "idle"


async def test_tap_select_sends_flow_node_mode(hass, no_hub_connection):
    _, _ = await setup(hass)
    _, ents = entities_of(hass, TAP_ID)
    entity_id = ents[f"flownodemode_{TAP_ID.lower()}"].entity_id

    await hass.services.async_call("select", "select_option",
                                   {"entity_id": entity_id, "option": "FORCED_ON"}, blocking=True)
    no_hub_connection.assert_awaited_with({"deviceConfig": {
        "id": TAP_ID, "features": {"flowNode": {"mode": "FORCED_ON"}}}})


async def test_pulse_keeps_its_behaviour(hass):
    _, ctx = await setup(hass)
    device, ents = entities_of(hass, PULSE_ID)
    pid = PULSE_ID.lower()

    assert device.model == "Pulse"
    assert state(hass, ents, f"flownodemode_{pid}").attributes["options"] == ["FLOW", "FORCED_ON", "FORCED_OFF"]
    assert f"contactor_mode_{pid}" not in ents

    ctx.socket.process(json.dumps(on_off(PULSE_ID, "STREAM_OUTLET", True,
                                         power=900, consoTot=18420)))
    await settle(hass, ctx)
    assert state(hass, ents, f"relaystate_{pid}").state == "on"
