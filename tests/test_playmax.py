"""PLAY Max battery values from the solarEvent (regression found on a live HA running 1.4.0)."""
import json

from .test_tap import HUB_ID, product_info, settle, setup

PLAYMAX_ID = "30EDA08FF570"


def _with_playmax():
    info = product_info()
    info["data"]["devices"].append({
        "id": PLAYMAX_ID, "comType": "Wifi", "comTypeInt": 2, "model": 3,
        "productName": "PLAY_MAX", "manufacturerName": "Sunology", "parentId": HUB_ID})
    return info


def _solar_event(**fields):
    """solarEvent as built by fw-sconnect PlayMaxDto::toJson_solarEvent."""
    return {"event": "solarEvent", "data": {
        "id": PLAYMAX_ID, "productName": "PLAY_MAX", "manufacturerName": "Sunology",
        "parentId": HUB_ID, "rssi": -66, "connectionType": 2, **fields}}


def _playmax(ctx):
    return next(d for d in ctx.sunology_devices if d.device_id == PLAYMAX_ID)


async def test_playmax_battery_power_from_solar_event(hass, caplog):
    """The PLAY Max sends its battery power as `batP`, not `batPow` (STOREY): it was
    always None and every solarEvent logged a warning (200+ per hour on a live HA)."""
    _, ctx = await setup(hass)
    ctx.socket.process(json.dumps(_with_playmax()))
    await settle(hass, ctx)

    ctx.socket.process(json.dumps(_solar_event(
        pvP=243.0, miP=210.2, batTmp=21.41, batP=50.5, batPct=34)))
    await settle(hass, ctx)

    device = _playmax(ctx)
    assert device.batP == 50.5
    assert device.batPct == 34
    assert device.batTmp == 21.41
    assert "without the required" not in caplog.text


async def test_missing_fields_keep_the_last_value(hass, caplog):
    """A partial event must not reset known values to None."""
    _, ctx = await setup(hass)
    ctx.socket.process(json.dumps(_with_playmax()))
    await settle(hass, ctx)
    ctx.socket.process(json.dumps(_solar_event(
        pvP=243.0, miP=210.2, batTmp=21.41, batP=50.5, batPct=34)))
    await settle(hass, ctx)

    ctx.socket.process(json.dumps(_solar_event(pvP=100.0)))
    await settle(hass, ctx)

    device = _playmax(ctx)
    assert device.pvP == 100.0
    assert device.miP == 210.2
    assert device.batP == 50.5
    assert device.batPct == 34
    assert "without the required" not in caplog.text
